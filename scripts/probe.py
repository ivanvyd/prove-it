"""The day-one gate.

Three assumptions carry the whole product, and all three are cheap to falsify before any
interface exists. This script falsifies them, or clears them:

  1. Does Genie return an inspectable query attachment for a claim-testing question?
     If not, there is nothing to put on screen and the concept changes shape.
  2. Is `thoughts` actually populated on Free Edition, and with which types?
     If not, beat 2 falls back to SQL plus a one-line description.
  3. Does a loaded question ("are boys better at maths?") get refused?
     If it does, free-text input is replaced by a curated rumour deck.

It also answers a fourth question nobody asks until it hurts: how long does a turn take
on a 2X-Small warehouse, so the courtroom pacing is choreographed against real numbers.

Run it, read the summary, and only then decide whether to write a line of UI.

    export DATABRICKS_HOST=...            # or use a profile in ~/.databrickscfg
    export DATABRICKS_TOKEN=...
    python scripts/probe.py --space-id <genie-space-id> --repeats 3 --record

Output lands in probe-runs/ (gitignored — it can carry workspace identifiers).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from prove_it.domain.claim import opening_question, repair_question  # noqa: E402
from prove_it.genie.client import DatabricksGenieClient  # noqa: E402
from prove_it.genie.fake import fixture_payload  # noqa: E402
from prove_it.genie.models import Turn  # noqa: E402

# Each claim carries what the DATA can do with it, because the two outcomes are graded
# differently. An earlier version pooled them and divided by everything, which scored the
# product's own third verdict — "this data cannot answer that" — as a failure and reported
# FAIL on a run where every single claim behaved correctly.
COMPARISON = "comparison"  # the table can answer this; expect a usable two-group result
UNTESTABLE = "untestable"  # no such column; expect Genie to say so and name what is missing

CLAIMS: list[tuple[str, str]] = [
    ("boys are better at maths", COMPARISON),
    ("girls are better at reading", COMPARISON),
    ("boys are naturally worse at reading than girls", COMPARISON),  # loaded phrasing
    ("do boys and girls score differently in maths", COMPARISON),
    ("kids with phones read worse", UNTESTABLE),  # no device column
    ("our region is the poorest", UNTESTABLE),  # no region column
    ("rich kids always do better", UNTESTABLE),  # no income column
    ("some countries are just smarter", UNTESTABLE),  # no country column, loaded phrasing
]


# If Genie's FIRST answer already reports variation, there is no gap for the child to
# open and the whole lesson collapses. This is the number-one kill risk in
# docs/requirement.md, and it is measurable from the emitted SQL alone.
SPREAD_FUNCTIONS = re.compile(
    r"\b(STDDEV\w*|VAR_\w+|VARIANCE|PERCENTILE\w*|APPROX_PERCENTILE|MEDIAN)\s*\(",
    re.I,
)

# MIN and MAX only disclose spread when they appear together, as a range. Alone, either is
# far more likely to be filtering — `WHERE exam_year = (SELECT MAX(exam_year) ...)` is an
# ordinary way to pick the latest year and says nothing about variation. Counting a lone
# MAX as "not naive" would fail the day-one gate over a query that reveals no spread at
# all, and send whoever reads it off tightening instructions for a problem they do not
# have.
_MIN = re.compile(r"\bMIN\s*\(", re.I)
_MAX = re.compile(r"\bMAX\s*\(", re.I)


def discloses_spread(sql: str) -> bool:
    if SPREAD_FUNCTIONS.search(sql):
        return True
    return bool(_MIN.search(sql) and _MAX.search(sql))


@dataclass
class Observation:
    claim: str
    attempt: int
    seconds: float
    status: str
    got_query: bool
    expectation: str = COMPARISON
    thought_kinds: list[str] = field(default_factory=list)
    rows: int = 0
    cols: int = 0
    first_cell_numeric: bool = False
    sql: str = ""
    refusal: str = ""
    error: str = ""
    first_draft_naive: bool = False
    """True when the opening query reports averages only — which is what the lesson needs."""


def _numeric(cell: object) -> bool:
    try:
        float(str(cell).replace(",", "").strip())
    except (TypeError, ValueError):
        return False
    return True


def probe_once(client: DatabricksGenieClient, claim: str, attempt: int) -> Observation:
    started = time.monotonic()
    try:
        turn = client.ask(opening_question(claim))
    except Exception as exc:  # noqa: BLE001 - the probe reports failures, it does not raise
        return Observation(
            claim, attempt, time.monotonic() - started, "ERROR", False, error=repr(exc)
        )

    elapsed = time.monotonic() - started
    obs = Observation(
        claim=claim,
        attempt=attempt,
        seconds=elapsed,
        status=turn.status,
        got_query=turn.has_query,
        thought_kinds=[t.kind for t in turn.thoughts],
        sql=turn.sql or "",
        refusal=(turn.refusal_text or "")[:400],
        first_draft_naive=bool(turn.sql) and not discloses_spread(turn.sql or ""),
    )
    if not turn.has_query:
        return obs

    try:
        table = client.fetch_result(turn)
    except Exception as exc:  # noqa: BLE001 - same rule: a failed fetch is an observation
        obs.error = repr(exc)
        return obs

    obs.rows = len(table.rows)
    obs.cols = len(table.columns)
    if table.rows and table.rows[0]:
        obs.first_cell_numeric = any(_numeric(c) for c in table.rows[0])
    return obs


def record_demo_fixture(client: DatabricksGenieClient, claim: str, path: Path) -> None:
    """Capture one full two-turn investigation for offline replay.

    This is what turns `prove_it.genie.fake` from a plausible stand-in into a recording
    of the real thing, which is what the demo video should be built on.
    """
    first = client.ask(opening_question(claim))
    turns: list[Turn] = [first]
    results = {}
    if first.has_query:
        results[first.message_id] = client.fetch_result(first)
        second = client.follow_up(first, repair_question())
        turns.append(second)
        if second.has_query:
            results[second.message_id] = client.fetch_result(second)

    # Shape owned by `prove_it.genie.fake`, next to the loader that reads it back. Written
    # out here once and drifting from that loader is exactly how a fixture ends up with a
    # field nothing consumes.
    path.write_text(json.dumps(fixture_payload(claim, turns, results), indent=2), encoding="utf-8")
    print(f"\nRecorded a full investigation to {path}")


def summarise(observations: list[Observation]) -> int:
    """Print the go/no-go. Returns a process exit code."""
    total = len(observations)
    if not total:
        print("No observations.")
        return 1

    # Split by what the data can actually do with the claim. Pooling these scores the
    # product's own third verdict as a failure: a claim with no supporting column SHOULD
    # come back without a query, and Genie saying so is the behaviour, not a miss.
    comparisons = [o for o in observations if o.expectation == COMPARISON]
    untestable = [o for o in observations if o.expectation == UNTESTABLE]

    with_query = [o for o in observations if o.got_query]
    parseable = [o for o in comparisons if o.got_query and o.rows >= 2 and o.first_cell_numeric]
    declined_well = [o for o in untestable if not o.got_query and o.refusal]
    with_thoughts = [o for o in with_query if o.thought_kinds]
    errors = [o for o in observations if o.error]
    times = [o.seconds for o in observations if o.seconds > 0]

    kinds: dict[str, int] = {}
    for o in with_thoughts:
        for k in set(o.thought_kinds):
            kinds[k] = kinds.get(k, 0) + 1

    naive = [o for o in with_query if o.first_draft_naive]
    query_rate = len(with_query) / total
    parse_rate = (len(parseable) / len(comparisons)) if comparisons else 0.0
    decline_rate = (len(declined_well) / len(untestable)) if untestable else 1.0
    thought_rate = (len(with_thoughts) / len(with_query)) if with_query else 0.0
    naive_rate = (len(naive) / len(with_query)) if with_query else 0.0

    print("\n" + "=" * 68)
    print("PROVE IT — day-one gate")
    print("=" * 68)
    print(f"  attempts                 {total}")
    print(f"  returned a query         {len(with_query)}  ({query_rate:.0%} of all)")
    print(
        f"  usable comparison        {len(parseable)}/{len(comparisons)}  "
        f"({parse_rate:.0%})   <- the gate, over answerable claims only"
    )
    print(
        f"  correctly declined       {len(declined_well)}/{len(untestable)}  "
        f"({decline_rate:.0%})   <- the third verdict"
    )
    print(f"  thoughts populated       {len(with_thoughts)}  ({thought_rate:.0%} of queries)")
    print(f"  thought types seen       {', '.join(sorted(kinds)) or 'NONE'}")
    print(f"  naive first draft        {len(naive)}  ({naive_rate:.0%} of queries)   <- the lesson")
    if times:
        print(f"  latency p50 / p95        {statistics.median(times):.1f}s / {max(times):.1f}s")
    print(f"  errors                   {len(errors)}")

    refused = [o for o in observations if not o.got_query]
    if refused:
        print("\n  Questions that produced no query:")
        for o in refused[:8]:
            tag = "expected" if o.expectation == UNTESTABLE else "UNEXPECTED"
            print(
                f"    - [{tag}] {o.claim!r}: {o.refusal[:100] or o.error[:100] or 'no explanation'}"
            )

    print("\n  Verdict:")
    ok = True
    if parse_rate >= 0.9:
        print("    PASS  free-text claims are reliable. Build as specified.")
    elif parse_rate >= 0.6:
        print("    WARN  free text is shaky. Ship the curated rumour deck as the primary")
        print("          input (R11) and keep free text behind a flag.")
        ok = False
    else:
        print("    FAIL  answerable claims do not produce a usable comparison. Reshape")
        print("          the concept before building UI — this is what day one is for.")
        ok = False

    if untestable and decline_rate < 0.8:
        ok = False
        print("    FAIL  claims the data cannot answer are not being declined cleanly.")
        print("          The third verdict is a headline feature, and a child must be")
        print("          told which column is missing rather than shown a guess.")

    if with_query and naive_rate < 0.8:
        ok = False
        print("    FAIL  Genie is volunteering the spread in its FIRST answer, so there is")
        print("          no gap for the child to open and the repair round has nothing to")
        print("          overturn. Tighten the opening paragraph of the space instructions")
        print("          (docs/genie-space-instructions.md) and re-run. This matters more")
        print("          than the hit rate: without it there is no lesson, only a chart.")

    if not with_thoughts:
        print("    NOTE  thoughts is empty in every response. Beat 2 falls back to SQL")
        print("          plus the one-line description. Not fatal, but weaker.")
    print("=" * 68)
    return 0 if ok else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Prove It — Genie day-one probe")
    parser.add_argument("--space-id", required=True, help="Genie space id")
    parser.add_argument("--repeats", type=int, default=3, help="attempts per claim")
    parser.add_argument("--record", action="store_true", help="save a replayable fixture")
    parser.add_argument("--out", default="probe-runs", help="output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    client = DatabricksGenieClient(space_id=args.space_id)

    observations: list[Observation] = []
    for claim, expectation in CLAIMS:
        for attempt in range(1, args.repeats + 1):
            obs = probe_once(client, claim, attempt)
            obs.expectation = expectation
            observations.append(obs)
            flag = "query" if obs.got_query else "NO QUERY"
            thoughts = f"{len(obs.thought_kinds)} thoughts" if obs.thought_kinds else "no thoughts"
            print(
                f"  [{obs.seconds:5.1f}s] {expectation:<10} {flag:<8} {thoughts:<12} "
                f"{obs.rows}x{obs.cols}  {claim!r}"
            )

    csv_path = out_dir / "probe.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "claim",
                "attempt",
                "seconds",
                "status",
                "got_query",
                "thought_kinds",
                "rows",
                "cols",
                "first_cell_numeric",
                "first_draft_naive",
                "sql",
                "refusal",
                "error",
            ]
        )
        for o in observations:
            writer.writerow(
                [
                    o.claim,
                    o.attempt,
                    f"{o.seconds:.2f}",
                    o.status,
                    o.got_query,
                    "|".join(o.thought_kinds),
                    o.rows,
                    o.cols,
                    o.first_cell_numeric,
                    o.first_draft_naive,
                    o.sql.replace("\n", " "),
                    o.refusal,
                    o.error,
                ]
            )
    print(f"\nWrote {csv_path}")

    if args.record:
        record_demo_fixture(client, CLAIMS[0][0], out_dir / "demo-investigation.json")

    return summarise(observations)


if __name__ == "__main__":
    raise SystemExit(main())
