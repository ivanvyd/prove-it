"""Tests for the day-one gate.

The probe is the one script whose failure is most expensive: it runs once, against a
live workspace, at the start of the build, and its verdict decides whether the concept
proceeds. A crash or a wrong summary there costs a day and sends the project in the wrong
direction, so it gets covered even though it cannot be run against Genie from here.

The round-trip test is the important one. The probe writes a fixture and the app reads
one; nothing previously proved those were the same format.
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import probe  # noqa: E402
from prove_it.genie.fake import (  # noqa: E402
    DEMO_FIRST,
    DEMO_RESULTS,
    DEMO_SECOND,
    ScriptedGenieClient,
    client_from_fixture,
)
from prove_it.genie.models import Turn  # noqa: E402


def demo_client() -> ScriptedGenieClient:
    return ScriptedGenieClient(turns=[DEMO_FIRST, DEMO_SECOND], results=dict(DEMO_RESULTS))


# -- number sniffing ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("492.6", True),
        ("4,812", True),
        ("-3", True),
        ("1.2e3", True),
        ("boy", False),
        ("", False),
        (None, False),
        ("N/A", False),
    ],
)
def test_numeric_recognises_what_it_should(cell: object, expected: bool) -> None:
    assert probe._numeric(cell) is expected


# -- one probe attempt -------------------------------------------------------------


def test_a_successful_attempt_records_the_shape_of_the_answer() -> None:
    obs = probe.probe_once(demo_client(), "boys are better at maths", 1)

    assert obs.got_query is True
    assert obs.rows == 2
    assert obs.cols == 2
    assert obs.first_cell_numeric is True
    assert "AVG" in obs.sql
    assert obs.thought_kinds == ["UNDERSTANDING", "DATA_SOURCING", "STEPS"]
    assert obs.error == ""


def test_a_refusal_is_recorded_rather_than_raised() -> None:
    refusal = Turn(
        conversation_id="c",
        message_id="m",
        question="q",
        text="There is nothing about phones in this data.",
    )
    obs = probe.probe_once(ScriptedGenieClient(turns=[refusal]), "kids with phones read worse", 1)

    assert obs.got_query is False
    assert "phones" in obs.refusal
    assert obs.error == ""


class Exploding:
    """The workspace is unreachable — the probe must survive and say so."""

    def ask(self, question: str):
        raise ConnectionError("no route to host")

    def follow_up(self, turn, question: str):
        raise ConnectionError("no route to host")

    def fetch_result(self, turn):
        raise ConnectionError("no route to host")


def test_a_dead_workspace_produces_an_observation_not_a_crash() -> None:
    obs = probe.probe_once(Exploding(), "anything", 1)

    assert obs.status == "ERROR"
    assert obs.got_query is False
    assert "ConnectionError" in obs.error


def test_a_failure_fetching_rows_is_recorded_against_the_attempt() -> None:
    class FetchFails(ScriptedGenieClient):
        def fetch_result(self, turn):
            raise TimeoutError("warehouse asleep")

    client = FetchFails(turns=[DEMO_FIRST])
    obs = probe.probe_once(client, "boys are better at maths", 1)

    assert obs.got_query is True
    assert "TimeoutError" in obs.error
    assert obs.rows == 0


# -- the verdict -------------------------------------------------------------------


def observation(
    *,
    got_query: bool = True,
    rows: int = 2,
    numeric: bool = True,
    thoughts: list[str] | None = None,
    naive: bool = True,
) -> probe.Observation:
    return probe.Observation(
        claim="c",
        attempt=1,
        seconds=3.0,
        status="COMPLETED",
        got_query=got_query,
        thought_kinds=thoughts if thoughts is not None else ["STEPS"],
        rows=rows,
        cols=2,
        first_cell_numeric=numeric,
        first_draft_naive=naive,
    )


# -- the kill risk: is Genie's first draft actually naive? --------------------------


@pytest.mark.parametrize(
    ("sql", "naive"),
    [
        ("SELECT gender, AVG(maths_score) AS avg_score FROM t GROUP BY gender", True),
        ("SELECT gender, COUNT(*) AS students, AVG(x) FROM t GROUP BY gender", True),
        ("SELECT gender, AVG(x), STDDEV(x) AS spread FROM t GROUP BY gender", False),
        ("SELECT gender, AVG(x), stddev_samp(x) FROM t GROUP BY gender", False),
        ("SELECT gender, VARIANCE(x) FROM t GROUP BY gender", False),
        ("SELECT gender, PERCENTILE(x, 0.5) FROM t GROUP BY gender", False),
        # MIN and MAX together are a range, and a range discloses spread.
        ("SELECT gender, MIN(x), MAX(x) FROM t GROUP BY gender", False),
        # But a lone MAX in a filter is ordinary "latest year" logic and reveals nothing.
        (
            "SELECT gender, AVG(maths_score) AS avg_score FROM t "
            "WHERE exam_year = (SELECT MAX(exam_year) FROM t) GROUP BY gender",
            True,
        ),
        (
            "SELECT gender, AVG(x) FROM t GROUP BY gender HAVING COUNT(*) > MIN(x)",
            True,
        ),
    ],
)
def test_a_first_draft_that_already_reports_variation_is_not_naive(sql: str, naive: bool) -> None:
    """If Genie volunteers the spread up front there is no gap to open, and no lesson."""
    turn = Turn(
        conversation_id="c",
        message_id="m",
        question="q",
        attachment_id="a",
        sql=sql,
    )
    obs = probe.probe_once(ScriptedGenieClient(turns=[turn]), "claim", 1)
    assert obs.first_draft_naive is naive


def test_the_gate_fails_when_genie_gives_the_answer_away() -> None:
    """This outranks the hit rate: a helpful Genie here means there is no product."""
    too_helpful = [observation(naive=False) for _ in range(10)]
    assert probe.summarise(too_helpful) == 2


def test_the_gate_tolerates_the_occasional_non_naive_draft() -> None:
    mostly_naive = [observation() for _ in range(9)] + [observation(naive=False)]
    assert probe.summarise(mostly_naive) == 0


def test_all_good_attempts_pass_the_gate() -> None:
    assert probe.summarise([observation() for _ in range(10)]) == 0


def test_a_shaky_hit_rate_warns_rather_than_passing() -> None:
    mixed = [observation() for _ in range(7)] + [observation(got_query=False) for _ in range(3)]
    assert probe.summarise(mixed) == 2


def test_a_bad_hit_rate_fails_the_gate() -> None:
    bad = [observation() for _ in range(2)] + [observation(got_query=False) for _ in range(8)]
    assert probe.summarise(bad) == 2


def test_no_observations_at_all_is_reported_not_divided_by() -> None:
    assert probe.summarise([]) == 1


def test_every_attempt_refused_does_not_divide_by_zero() -> None:
    """thought_rate divides by the number of queries, which can legitimately be zero."""
    assert probe.summarise([observation(got_query=False) for _ in range(5)]) == 2


def test_a_result_with_one_row_does_not_count_as_usable() -> None:
    """One group is not a comparison, so it must not inflate the gate's hit rate."""
    assert probe.summarise([observation(rows=1) for _ in range(10)]) == 2


def test_missing_thoughts_still_allows_a_pass() -> None:
    """An empty thoughts array weakens beat 2 but must not fail the concept."""
    assert probe.summarise([observation(thoughts=[]) for _ in range(10)]) == 0


# -- the fixture round trip --------------------------------------------------------


def test_a_recorded_fixture_can_be_replayed_by_the_app(tmp_path: Path) -> None:
    """The probe writes it and prove_it.genie.fake reads it. Prove they agree."""
    path = tmp_path / "demo-investigation.json"
    probe.record_demo_fixture(demo_client(), "boys are better at maths", path)

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["claim"] == "boys are better at maths"
    assert len(payload["turns"]) == 2

    replayed = client_from_fixture(path)
    first = replayed.ask("anything")
    assert first.sql == DEMO_FIRST.sql
    assert [t.kind for t in first.thoughts] == [t.kind for t in DEMO_FIRST.thoughts]

    rows = replayed.fetch_result(first)
    assert rows.rows == DEMO_RESULTS["demo-message-1"].rows
    assert [c.name for c in rows.columns] == [
        c.name for c in DEMO_RESULTS["demo-message-1"].columns
    ]


def test_a_recorded_refusal_round_trips_too(tmp_path: Path) -> None:
    refusal = Turn(conversation_id="c", message_id="m", question="q", text="cannot answer that")
    path = tmp_path / "refusal.json"
    probe.record_demo_fixture(ScriptedGenieClient(turns=[refusal]), "unanswerable", path)

    replayed = client_from_fixture(path)
    turn = replayed.ask("anything")
    assert turn.has_query is False
    assert turn.refusal_text == "cannot answer that"
