"""Tests for the workspace setup script.

Same reasoning as the probe's tests: this runs once, against a live workspace, and a
failure there is expensive and badly timed. It cannot be run against Databricks from here,
so the parts that can be wrong on their own — warehouse selection, statement error
handling, and the check that the built table matches the numbers we publish — are covered
with fakes.

The comparison is the one that matters. If it returns "no mismatches" for a table that is
actually wrong, every figure in the app, the tests and the project story is quietly false.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import setup_workspace as sw  # noqa: E402
from prove_it.demo_data import OBSERVED  # noqa: E402


def good_rows() -> list[list[str]]:
    """What the warehouse returns when everything is right. Values arrive as strings."""
    return [[g, str(o.students), str(o.maths_mean), str(o.maths_sd)] for g, o in OBSERVED.items()]


# -- the comparison ----------------------------------------------------------------


def test_a_correctly_built_table_reports_no_mismatches() -> None:
    assert sw.compare_to_expected(good_rows()) == []


def test_a_wrong_average_is_caught() -> None:
    rows = good_rows()
    rows[0][2] = str(float(rows[0][2]) + 3.0)
    mismatched = sw.compare_to_expected(rows)
    assert len(mismatched) == 1
    assert mismatched[0][0] == rows[0][0]


def test_a_wrong_row_count_is_caught() -> None:
    rows = good_rows()
    rows[1][1] = "17"
    assert len(sw.compare_to_expected(rows)) == 1


def test_a_small_rounding_difference_is_tolerated() -> None:
    """The warehouse rounds to one decimal; that must not read as a mismatch."""
    rows = good_rows()
    rows[0][2] = str(round(float(rows[0][2]) + 0.04, 2))
    assert sw.compare_to_expected(rows) == []


def test_an_empty_result_is_a_mismatch_not_a_pass() -> None:
    """The dangerous failure: a table that returned nothing must not read as agreement."""
    mismatched = sw.compare_to_expected([])
    assert len(mismatched) == len(OBSERVED)
    assert all("missing" in str(m[2]) for m in mismatched)


def test_a_missing_group_is_reported() -> None:
    assert len(sw.compare_to_expected(good_rows()[:1])) == 1


def test_non_numeric_cells_are_reported_rather_than_crashing() -> None:
    rows = good_rows()
    rows[0][2] = "NULL"
    mismatched = sw.compare_to_expected(rows)
    assert len(mismatched) == 1


# -- SQL string building -----------------------------------------------------------


def test_an_apostrophe_in_a_comment_does_not_break_the_statement() -> None:
    """The comments are English prose about pupils. Prose acquires apostrophes.

    Before this was escaped, adding "the pupil's score" to demo_data produced a COMMENT
    statement with an unbalanced quote — broken setup at best, and at worst the text after
    the apostrophe executed against the operator's own warehouse.
    """
    comment = "One row per pupil. It's synthetic; no real pupils' data."
    statement = f"COMMENT ON TABLE t IS {sw.sql_literal(comment)}"

    assert statement.count("'") % 2 == 0, "unbalanced quotes"
    assert "''s synthetic" in statement
    assert "pupils'' data" in statement


def test_quotes_are_doubled_not_stripped() -> None:
    """The child still needs to read the comment, so the apostrophe must survive."""
    assert sw.sql_literal("it's") == "'it''s'"
    assert sw.sql_literal("plain") == "'plain'"
    assert sw.sql_literal("") == "''"


def test_a_comment_that_tries_to_close_the_statement_is_neutralised() -> None:
    hostile = "x'; DROP TABLE students; --"
    literal = sw.sql_literal(hostile)
    assert literal.count("'") % 2 == 0
    assert "''; DROP" in literal, "the closing quote must be escaped, not removed"


def test_every_shipped_comment_survives_being_quoted() -> None:
    """Guards the real values, so a future edit to demo_data cannot break setup silently."""
    from prove_it.demo_data import COLUMN_COMMENTS, TABLE_COMMENT

    for value in [TABLE_COMMENT, *COLUMN_COMMENTS.values()]:
        assert sw.sql_literal(value).count("'") % 2 == 0


# -- identifier validation ---------------------------------------------------------


@pytest.mark.parametrize("name", ["workspace", "prove_it", "a1_B2"])
def test_ordinary_identifiers_are_accepted(name: str) -> None:
    assert sw.identifier(name, "catalog") == name


@pytest.mark.parametrize(
    "name",
    ["workspace; DROP TABLE x; --", "has space", "has-dash", "", "back`tick", "a.b"],
)
def test_anything_that_is_not_a_plain_identifier_is_refused(name: str) -> None:
    """These land in DDL, where an identifier cannot be parameterised."""
    with pytest.raises(SystemExit, match="letters, digits or underscores"):
        sw.identifier(name, "catalog")


def test_the_real_data_comment_tells_genie_the_table_is_aggregate() -> None:
    """This is what lets Genie answer "this cannot say that about an individual".

    country_indicators has no per-person rows. Without saying so, Genie will happily
    compare countries in answer to a question about a person.
    """
    from prove_it.demo_data import INDICATORS_COMMENT

    lowered = INDICATORS_COMMENT.lower()
    assert "aggregate" in lowered
    assert "individual" in lowered
    assert sw.sql_literal(INDICATORS_COMMENT).count("'") % 2 == 0


# -- warehouse selection -----------------------------------------------------------


class FakeWarehouse:
    def __init__(self, id: str, name: str, state: str = "STOPPED") -> None:
        self.id = id
        self.name = name
        self.state = state


class FakeClient:
    def __init__(self, warehouses: list[FakeWarehouse]) -> None:
        self.warehouses = type("W", (), {"list": lambda _self: iter(warehouses)})()


def test_no_warehouse_at_all_exits_with_an_actionable_message() -> None:
    with pytest.raises(SystemExit, match="Free Edition"):
        sw.pick_warehouse(FakeClient([]), None)


def test_a_running_warehouse_is_preferred_over_a_stopped_one() -> None:
    client = FakeClient(
        [
            FakeWarehouse("stopped-1", "Cold", "STOPPED"),
            FakeWarehouse("running-1", "Warm", "RUNNING"),
        ]
    )
    assert sw.pick_warehouse(client, None) == "running-1"


def test_the_first_warehouse_is_used_when_none_are_running() -> None:
    client = FakeClient([FakeWarehouse("a", "A"), FakeWarehouse("b", "B")])
    assert sw.pick_warehouse(client, None) == "a"


@pytest.mark.parametrize("preferred", ["b", "B"])
def test_a_warehouse_can_be_chosen_by_id_or_name(preferred: str) -> None:
    client = FakeClient([FakeWarehouse("a", "A"), FakeWarehouse("b", "B")])
    assert sw.pick_warehouse(client, preferred) == "b"


def test_an_unknown_warehouse_name_lists_what_is_available() -> None:
    client = FakeClient([FakeWarehouse("a", "Analytics")])
    with pytest.raises(SystemExit, match="Analytics"):
        sw.pick_warehouse(client, "nope")


# -- statement execution -----------------------------------------------------------


def _response(state: str, statement_id: str | None = "stmt-1"):
    error = type("E", (), {"message": "boom"})()
    status = type("S", (), {"state": state, "error": error})()
    return type("R", (), {"status": status, "statement_id": statement_id})()


class FakeStatements:
    def __init__(self, state: str, then: list[str] | None = None) -> None:
        self.state = state
        self.then = list(then or [])
        self.executed: list[str] = []
        self.polls = 0

    def execute_statement(self, *, statement: str, warehouse_id: str, wait_timeout: str):
        self.executed.append(statement)
        return _response(self.state)

    def get_statement(self, statement_id: str):
        self.polls += 1
        return _response(self.then.pop(0) if self.then else self.state)


class ClientWithStatements:
    def __init__(self, state: str, then: list[str] | None = None) -> None:
        self.statement_execution = FakeStatements(state, then)


def test_a_successful_statement_returns_quietly() -> None:
    client = ClientWithStatements("SUCCEEDED")
    sw.sql(client, "wh", "CREATE SCHEMA x")
    assert client.statement_execution.executed == ["CREATE SCHEMA x"]


@pytest.mark.parametrize("state", ["FAILED", "CANCELED", "CLOSED"])
def test_a_failed_statement_raises_with_the_statement_in_the_message(state: str) -> None:
    """Otherwise a failure deep in setup gives you a state name and nothing to act on."""
    client = ClientWithStatements(state)
    with pytest.raises(RuntimeError) as excinfo:
        sw.sql(client, "wh", "ALTER TABLE broken ALTER COLUMN nope COMMENT 'x'")
    message = str(excinfo.value)
    assert state in message
    assert "ALTER TABLE broken" in message
    assert "boom" in message


@pytest.mark.parametrize("state", ["PENDING", "RUNNING"])
def test_a_still_running_statement_is_polled_to_completion(state: str) -> None:
    """A cold 2X-Small warehouse routinely outlives wait_timeout.

    execute_statement then returns a non-terminal state rather than an error. Treating
    that as success meant uploading a file to a volume whose CREATE had not finished, and
    a spurious data mismatch at the end that was really just timing.
    """
    client = ClientWithStatements(state, then=[state, "SUCCEEDED"])
    sw.sql(client, "wh", "CREATE VOLUME x", poll_for=30)

    assert client.statement_execution.polls >= 2, "it should have waited, not assumed"


def test_a_statement_that_fails_after_polling_still_raises() -> None:
    client = ClientWithStatements("RUNNING", then=["FAILED"])
    with pytest.raises(RuntimeError, match="FAILED"):
        sw.sql(client, "wh", "CREATE TABLE broken", poll_for=30)


def test_a_statement_that_never_finishes_gives_up_rather_than_hanging() -> None:
    client = ClientWithStatements("RUNNING", then=[])
    with pytest.raises(RuntimeError, match="RUNNING"):
        sw.sql(client, "wh", "SELECT 1", poll_for=4)
