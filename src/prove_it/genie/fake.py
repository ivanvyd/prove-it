"""A Genie client that replays a script instead of calling Databricks.

Two jobs. In tests it is a spy, so the rule that matters most — no rows are fetched
before the child predicts — can be asserted rather than hoped for. In the app it is
`PROVE_IT_OFFLINE=1` mode, which lets the whole five-beat flow be built and demonstrated
before a workspace exists.

The scripted turns below are a stand-in with the shape of a real response. Replace them
with genuinely recorded output once `scripts/probe.py` has run: `--record` writes
fixtures in exactly this form.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from prove_it.demo_data import OBSERVED
from prove_it.domain.verdict import Column, ResultTable
from prove_it.genie.models import ThoughtStep, Turn


@dataclass
class ScriptedGenieClient:
    """Replays prepared turns in order and records what was asked of it."""

    turns: list[Turn]
    results: dict[str, ResultTable] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)
    followed_up_on: list[str] = field(default_factory=list)
    # How offline replays the recorded wait: sleep is a hook so tests run instantly and
    # the app scales it by PROVE_IT_TEMPO. Defaults to no sleep, so nothing that does not
    # ask for the choreography pays for it.
    sleep: object = None
    _cursor: int = 0

    def _next(self, question: str, on_status: object | None) -> Turn:
        if self._cursor >= len(self.turns):
            raise AssertionError(f"The script ran out of turns; nothing prepared for {question!r}.")
        turn = self.turns[self._cursor]
        self._cursor += 1
        self.asked.append(question)
        # Replay the recorded phases at their recorded gaps, so the offline interrogation
        # room shows the same wait the live one did. A turn with no timeline just resolves.
        if on_status is not None and turn.timeline:
            previous = 0.0
            sleeper = self.sleep if callable(self.sleep) else None
            reporter = on_status if callable(on_status) else None
            for status, elapsed in turn.timeline:
                if sleeper is not None:
                    sleeper(max(0.0, elapsed - previous))
                    previous = elapsed
                if reporter is not None:
                    reporter(status, elapsed)
        return turn

    def ask(self, question: str, on_status: object | None = None) -> Turn:
        return self._next(question, on_status)

    def follow_up(self, turn: Turn, question: str, on_status: object | None = None) -> Turn:
        # Recorded so a test can prove the repair continued the *same* conversation
        # rather than quietly opening a new one, which would lose Genie's context.
        self.followed_up_on.append(turn.conversation_id)
        return self._next(question, on_status)

    def fetch_result(self, turn: Turn) -> ResultTable:
        self.fetched.append(turn.message_id)
        return self.results.get(turn.message_id, ResultTable([], []))


def _table(columns: list[str], rows: list[list[str | None]]) -> ResultTable:
    return ResultTable([Column(c) for c in columns], rows)


# The canonical demo, offline. Rows are derived from prove_it.demo_data.OBSERVED rather
# than typed out, so the offline demo cannot say something different from the table the
# notebook builds. Importing OBSERVED costs nothing at runtime: it is a plain dict of
# NamedTuples, and the pandas/numpy the generator needs are imported inside that function.

DEMO_FIRST = Turn(
    conversation_id="demo-conversation",
    message_id="demo-message-1",
    question="opening",
    attachment_id="demo-attachment-1",
    sql=(
        "SELECT gender,\n"
        "       AVG(maths_score) AS avg_score\n"
        "FROM workspace.prove_it.student_scores\n"
        "GROUP BY gender"
    ),
    description="Average maths score for each gender.",
    thoughts=[
        ThoughtStep("UNDERSTANDING", "The claim compares maths attainment between boys and girls."),
        ThoughtStep(
            "DATA_SOURCING",
            "student_scores holds gender and maths_score. No class or teacher grouping is "
            "available in this table.",
        ),
        ThoughtStep(
            "STEPS", "Group the rows by gender, then take the mean of maths_score for each group."
        ),
    ],
)

DEMO_SECOND = Turn(
    conversation_id="demo-conversation",
    message_id="demo-message-2",
    question="repair",
    attachment_id="demo-attachment-2",
    sql=(
        "SELECT gender,\n"
        "       COUNT(*) AS students,\n"
        "       AVG(maths_score) AS avg_score,\n"
        "       STDDEV(maths_score) AS spread\n"
        "FROM workspace.prove_it.student_scores\n"
        "GROUP BY gender"
    ),
    description="Average maths score per gender, with the spread and the number of pupils.",
    thoughts=[
        ThoughtStep(
            "UNDERSTANDING",
            "The follow-up asks for variation within each group, not just the group averages.",
        ),
        ThoughtStep(
            "STEPS",
            "Add a count and a standard deviation of maths_score alongside the existing mean.",
        ),
    ],
)

DEMO_RESULTS = {
    "demo-message-1": _table(
        ["gender", "avg_score"],
        [[gender, str(o.maths_mean)] for gender, o in OBSERVED.items()],
    ),
    "demo-message-2": _table(
        ["gender", "students", "avg_score", "spread"],
        [
            [gender, str(o.students), str(o.maths_mean), str(o.maths_sd)]
            for gender, o in OBSERVED.items()
        ],
    ),
}


FIXTURES = Path(__file__).resolve().parents[3] / "fixtures"
RECORDED_DEMO = FIXTURES / "recorded-demo.json"


def case_fixture(case_key: str) -> Path:
    """Where one case's recorded conversation lives. Written by `probe_cases.py --record`."""
    return FIXTURES / f"case-{case_key}.json"


def demo_client(case_key: str | None = None) -> ScriptedGenieClient:
    """The offline client used by `PROVE_IT_OFFLINE=1`.

    Replays a real two-turn Genie conversation captured against a live Free Edition space.
    Replaying genuine output matters: the hand-written script below was a good-faith guess
    at what Genie would produce, and a demo built on a guess can be wrong about the very
    thing it is demonstrating.

    The recording is per case, and that is not a nicety. Offline mode used to hold one
    conversation and serve it whatever was asked, so opening the Berkeley case offline
    showed the admissions claim above `AVG(maths_score) FROM student_scores`. In an app
    whose whole argument is "read the query rather than the answer", showing a query that
    belongs to a different question is the worst defect available.

    Falls back to the single recording and then to the written script, so a fresh clone
    still runs before anyone has a workspace — but `tests/test_offline_fixtures.py` holds
    the docket itself to the stronger standard.
    """
    if case_key:
        recorded = case_fixture(case_key)
        if recorded.is_file():
            return client_from_fixture(recorded)
    if RECORDED_DEMO.is_file():
        return client_from_fixture(RECORDED_DEMO)
    return ScriptedGenieClient(turns=[DEMO_FIRST, DEMO_SECOND], results=dict(DEMO_RESULTS))


def fixture_payload(claim: str, turns: list[Turn], results: dict[str, ResultTable]) -> dict:
    """Serialise a live conversation into the shape `client_from_fixture` reads.

    Deliberately the inverse of that function and next to it. The writer used to live in
    `scripts/probe.py` and the reader here, which is exactly how a recorded fixture ends
    up with a field the loader silently ignores.
    """
    return {
        "claim": claim,
        "turns": [
            {
                "conversation_id": t.conversation_id,
                "message_id": t.message_id,
                "question": t.question,
                "status": t.status,
                "attachment_id": t.attachment_id,
                "sql": t.sql,
                "description": t.description,
                "text": t.text,
                "thoughts": [{"kind": s.kind, "content": s.content} for s in t.thoughts],
                "timeline": [[status, at] for status, at in t.timeline],
            }
            for t in turns
        ],
        "results": {
            message_id: {
                "columns": [c.name for c in table.columns],
                "rows": table.rows,
            }
            for message_id, table in results.items()
        },
    }


def client_from_fixture(path: str | Path) -> ScriptedGenieClient:
    """Build a client from a recorded conversation.

    Two scripts write these: `scripts/probe_cases.py --record` writes one per case into
    `fixtures/`, and `scripts/probe.py --record` writes the single demo recording that
    `PROVE_IT_FIXTURE` points at.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    turns = [
        Turn(
            conversation_id=t["conversation_id"],
            message_id=t["message_id"],
            question=t.get("question", ""),
            status=t.get("status", "COMPLETED"),
            attachment_id=t.get("attachment_id"),
            sql=t.get("sql"),
            description=t.get("description"),
            text=t.get("text"),
            thoughts=[ThoughtStep(s["kind"], s["content"]) for s in t.get("thoughts", [])],
            timeline=[(status, float(at)) for status, at in t.get("timeline", [])],
        )
        for t in payload["turns"]
    ]
    results = {
        message_id: _table(table["columns"], table["rows"])
        for message_id, table in payload.get("results", {}).items()
    }
    return ScriptedGenieClient(turns=turns, results=results)
