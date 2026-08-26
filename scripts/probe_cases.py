"""The gate: does each case's two-turn arc actually happen against live Genie?

`probe.py` asks whether Genie returns an inspectable query at all. This asks the harder
question the docket depends on: for each case, does the FIRST answer come back naive —
plainly, at the level asked, volunteering nothing — and does the curated follow-up produce
the fairer query that overturns it?

A case that fails here is not a UI problem to be worked around later. It has no lesson,
and it gets rewritten or cut. That decision is cheap now and expensive after the UI is
built around it.

    python scripts/probe_cases.py --space-id <id>
    python scripts/probe_cases.py --space-id <id> --repeats 3 --only paradox
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prove_it.domain.verdict import ResultTable, Verdict, analyse  # noqa: E402
from prove_it.genie.client import DatabricksGenieClient  # noqa: E402
from prove_it.genie.fake import fixture_payload  # noqa: E402
from prove_it.genie.models import Turn as GenieTurn  # noqa: E402

RUNS = Path(__file__).resolve().parents[1] / "probe-runs"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@dataclass(frozen=True)
class CaseProbe:
    """One case's arc, and how to tell whether each turn came back right."""

    key: str
    claim: str
    follow_up: str
    table: str
    # Naive means: the first query must NOT already contain the thing the follow-up asks
    # for. Matched on the SQL, because that is what the app shows and what the child reads.
    naive_forbids: tuple[str, ...]
    repaired_requires: tuple[str, ...]
    # The arc the case exists to produce, judged by the real engine on the real rows.
    # Genie returning the right SHAPE is necessary and not sufficient: the paradox case is
    # only a case if the arithmetic over those twelve rows actually reverses.
    expect_naive: Verdict
    expect_repaired: Verdict


CASES: tuple[CaseProbe, ...] = (
    CaseProbe(
        key="spread",
        claim="boys are better at maths",
        follow_up="show the spread too, and how many are in each group",
        table="student_scores",
        naive_forbids=("stddev", "std(", "variance", "count("),
        repaired_requires=("stddev", "count("),
        expect_naive=Verdict.HOLDS,
        expect_repaired=Verdict.BUSTED,
    ),
    CaseProbe(
        # The case that SURVIVES. Same table and follow-up as spread, opposite outcome:
        # the reading gap is designed at d ~ 0.31, above the 0.2 threshold, so the fairer
        # query confirms it. Without one of these the game's call is not a call.
        key="reading",
        claim="girls are better at reading",
        follow_up="show the spread too, and how many are in each group",
        table="student_scores",
        naive_forbids=("stddev", "std(", "variance", "count("),
        repaired_requires=("stddev", "count("),
        expect_naive=Verdict.HOLDS,
        expect_repaired=Verdict.HOLDS,
    ),
    CaseProbe(
        key="paradox",
        claim="men were more likely than women to be admitted to Berkeley in 1973",
        follow_up="break that down by department",
        table="berkeley_admissions",
        naive_forbids=("department",),
        repaired_requires=("department",),
        expect_naive=Verdict.HOLDS,
        expect_repaired=Verdict.BUSTED,
    ),
    CaseProbe(
        key="window",
        claim="Bulgaria halved its education spending between 1991 and 1996",
        follow_up="now show every year in the data, not just the 1990s",
        table="country_indicators",
        # A naive answer honours the window it was given rather than widening it.
        naive_forbids=(),
        repaired_requires=(),
        expect_naive=Verdict.HOLDS,
        expect_repaired=Verdict.HALF_TRUE,
    ),
    CaseProbe(
        key="denominator",
        claim="China is the world's biggest polluter",
        follow_up="show it per person instead",
        table="emissions",
        naive_forbids=("per_capita", "population"),
        repaired_requires=("per_capita",),
        expect_naive=Verdict.HOLDS,
        expect_repaired=Verdict.HALF_TRUE,
    ),
)


@dataclass
class Turn:
    sql: str = ""
    rows: int = 0
    cols: list[str] = field(default_factory=list)
    seconds: float = 0.0
    refused: str = ""
    error: str = ""


@dataclass
class Arc:
    case: str
    attempt: int
    naive: Turn = field(default_factory=Turn)
    repaired: Turn = field(default_factory=Turn)
    right_table: bool = False
    naive_was_naive: bool = False
    repair_landed: bool = False
    naive_verdict: str = ""
    repaired_verdict: str = ""
    verdicts_as_expected: bool = False
    naive_reason: str = ""
    repaired_reason: str = ""
    recorded: str = ""

    @property
    def worked(self) -> bool:
        return (
            self.right_table
            and self.naive_was_naive
            and self.repair_landed
            and self.verdicts_as_expected
        )


def one_line(sql: str) -> str:
    """Genie returns SQL formatted across many lines; a probe log wants one."""
    return re.sub(r"\s+", " ", sql).strip()


def mentions(sql: str, needles: tuple[str, ...]) -> bool:
    low = sql.lower()
    return any(n in low for n in needles)


def run_turn(client, question, previous=None) -> tuple[Turn, GenieTurn | None, ResultTable | None]:
    """One live turn: what Genie said, the turn handle, and the rows it produced."""
    out = Turn()
    started = time.time()
    try:
        turn = client.follow_up(previous, question) if previous else client.ask(question)
    except Exception as exc:  # noqa: BLE001 - a probe reports failures, it does not raise them
        out.error = f"{type(exc).__name__}: {exc}"[:160]
        out.seconds = time.time() - started
        return out, None, None
    out.seconds = time.time() - started
    out.sql = turn.sql or ""
    if not turn.has_query:
        out.refused = (turn.refusal_text or "")[:160]
        return out, turn, None
    result = None
    try:
        result = client.fetch_result(turn)
        out.rows = len(result.rows)
        out.cols = [c.name for c in result.columns]
    except Exception as exc:  # noqa: BLE001 - the gate's whole job is to survive and report
        out.error = f"fetch: {type(exc).__name__}: {exc}"[:160]
    return out, turn, result


def record_arc(
    case: CaseProbe,
    turns: list,
    results: dict,
) -> Path:
    """Write one case's live conversation to `fixtures/case-<key>.json`.

    Recorded from THIS script rather than `probe.py` on purpose: the questions asked here
    are the exact strings `Investigation.open_case` and `repair` send, so the fixture is a
    recording of the arc the app actually performs. `probe.py` wraps the claim in v1's
    opening question, and a fixture recorded through a different wording is a demo of
    something the product does not do.
    """
    path = FIXTURES / f"case-{case.key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = fixture_payload(case.claim, turns, results)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def probe_case(client, case: CaseProbe, attempt: int, record: bool = False) -> Arc:
    arc = Arc(case=case.key, attempt=attempt)
    arc.naive, turn, naive_rows = run_turn(client, case.claim)
    if turn is None or not arc.naive.sql:
        return arc

    arc.right_table = case.table in arc.naive.sql.lower()
    arc.naive_was_naive = not mentions(arc.naive.sql, case.naive_forbids)

    arc.repaired, repaired_turn, repaired_rows = run_turn(client, case.follow_up, previous=turn)
    if arc.repaired.sql:
        arc.repair_landed = (
            mentions(arc.repaired.sql, case.repaired_requires)
            if case.repaired_requires
            else arc.repaired.sql.strip() != arc.naive.sql.strip()
        )
        # The window case has no keyword to look for: widening the series IS the repair,
        # so it shows up as more rows rather than as different SQL.
        if not case.repaired_requires:
            arc.repair_landed = arc.repair_landed or arc.repaired.rows > arc.naive.rows

    # The part that makes this a gate on the PRODUCT rather than on Genie. The right shape
    # coming back is necessary and not sufficient: the paradox case is only a case if the
    # arithmetic over those twelve rows actually reverses, and the only way to know that
    # is to run the real engine over the real rows.
    if naive_rows is not None:
        first = analyse(naive_rows)
        arc.naive_verdict = first.verdict.name
        arc.naive_reason = first.reason
    if repaired_rows is not None:
        second = analyse(repaired_rows, previous=naive_rows)
        arc.repaired_verdict = second.verdict.name
        arc.repaired_reason = second.reason
    arc.verdicts_as_expected = (
        arc.naive_verdict == case.expect_naive.name
        and arc.repaired_verdict == case.expect_repaired.name
    )

    # Only a arc that did the whole job gets recorded. A fixture is what someone without a
    # Databricks account plays, so shipping a half-arc would hand them a broken lesson and
    # call it the demo.
    if record and arc.worked and repaired_turn is not None:
        results = {}
        if naive_rows is not None:
            results[turn.message_id] = naive_rows
        if repaired_rows is not None:
            results[repaired_turn.message_id] = repaired_rows
        arc.recorded = str(record_arc(case, [turn, repaired_turn], results))

    return arc


def report(arcs: list[Arc]) -> int:
    print("\n" + "=" * 74)
    by_case: dict[str, list[Arc]] = {}
    for a in arcs:
        by_case.setdefault(a.case, []).append(a)

    failed = []
    for key, runs in by_case.items():
        n = len(runs)
        table = sum(1 for a in runs if a.right_table)
        naive = sum(1 for a in runs if a.naive_was_naive)
        repair = sum(1 for a in runs if a.repair_landed)
        worked = sum(1 for a in runs if a.worked)
        latency = [a.naive.seconds for a in runs] + [a.repaired.seconds for a in runs]
        print(f"\n  {key}")
        verdicts = sum(1 for a in runs if a.verdicts_as_expected)
        arcs_seen = {f"{a.naive_verdict or '?'} -> {a.repaired_verdict or '?'}" for a in runs}
        print(f"    right table        {table}/{n}")
        print(f"    naive first draft  {naive}/{n}")
        print(f"    repair landed      {repair}/{n}")
        print(f"    verdict arc        {verdicts}/{n}   {', '.join(sorted(arcs_seen))}")
        print(f"    full arc           {worked}/{n}")
        print(f"    slowest turn       {max(latency):.0f}s")
        for a in runs:
            if a.naive.refused:
                print(f"    ! refused: {a.naive.refused[:90]}")
            if a.naive.error or a.repaired.error:
                print(f"    ! error: {a.naive.error or a.repaired.error}")
        if worked * 3 < n * 2:  # two thirds of runs must complete the arc
            failed.append(key)

    print("\n" + "=" * 74)
    if failed:
        print(f"  GATE FAILED for: {', '.join(failed)}")
        print("  Rewrite the framing, tune the space instructions, or cut the case.")
    else:
        print("  GATE PASSED — every case completed its arc in at least two runs of three.")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove It — probe the case docket")
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--only", default="", help="comma-separated case keys")
    parser.add_argument("--profile", default=None)
    parser.add_argument(
        "--record",
        action="store_true",
        help="write each case's conversation to fixtures/case-<key>.json for offline play",
    )
    args = parser.parse_args()

    wanted = {k.strip() for k in args.only.split(",") if k.strip()}
    cases = [c for c in CASES if not wanted or c.key in wanted]
    if not cases:
        raise SystemExit(f"no such case: {args.only}")

    from databricks.sdk import WorkspaceClient

    workspace = WorkspaceClient(profile=args.profile) if args.profile else WorkspaceClient()
    client = DatabricksGenieClient(space_id=args.space_id, workspace_client=workspace)

    arcs: list[Arc] = []
    for case in cases:
        for attempt in range(1, args.repeats + 1):
            print(f"  {case.key} {attempt}/{args.repeats} …", flush=True)
            # Record from the LAST attempt that works, so a fixture is never overwritten
            # by a later failed run and the recording is the arc most recently verified.
            arc = probe_case(client, case, attempt, record=args.record)
            arcs.append(arc)
            flags = "".join(
                "+" if ok else "-"
                for ok in (arc.right_table, arc.naive_was_naive, arc.repair_landed)
            )
            print(
                f"    [{flags}] naive {arc.naive.seconds:.0f}s "
                f"{arc.naive.rows}r {arc.naive.cols} | "
                f"repaired {arc.repaired.seconds:.0f}s {arc.repaired.rows}r "
                f"{arc.repaired.cols}"
            )
            # Collapsed outside the f-string: a backslash inside an f-string expression is
            # a syntax error before 3.12, and this project supports 3.11.
            for label, sql_text in (("v1", arc.naive.sql), ("v2", arc.repaired.sql)):
                if sql_text:
                    print(f"      {label}: {one_line(sql_text)[:150]}")
            if arc.recorded:
                print(f"      recorded -> {Path(arc.recorded).name}")

    RUNS.mkdir(exist_ok=True)
    out = RUNS / "case-probe.json"
    out.write_text(
        json.dumps(
            [
                {
                    "case": a.case,
                    "attempt": a.attempt,
                    "worked": a.worked,
                    "naive_verdict": a.naive_verdict,
                    "repaired_verdict": a.repaired_verdict,
                    "naive_reason": a.naive_reason,
                    "repaired_reason": a.repaired_reason,
                    "right_table": a.right_table,
                    "naive": a.naive_was_naive,
                    "repair": a.repair_landed,
                    "v1_sql": a.naive.sql,
                    "v2_sql": a.repaired.sql,
                    "v1_cols": a.naive.cols,
                    "v2_cols": a.repaired.cols,
                    "v1_rows": a.naive.rows,
                    "v2_rows": a.repaired.rows,
                    "refused": a.naive.refused,
                    "error": a.naive.error or a.repaired.error,
                }
                for a in arcs
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n  raw run -> {out}")
    return report(arcs)


if __name__ == "__main__":
    sys.exit(main())
