"""The plain-English annotation of Genie's SQL, checked against the queries Genie returns.

Every case below is a defect the first version shipped, found by running it over
`fixtures/` rather than over examples written to suit it. The fixtures are the real
recorded conversations, so every query shape that can reach a screen has a test here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prove_it.domain.explain import annotate

ROOT = Path(__file__).resolve().parents[1]

PARADOX = (
    "SELECT `gender`, SUM(`applicants`) AS applicants, SUM(`admitted`) AS admitted, "
    "try_divide(SUM(`admitted`),SUM(`applicants`)) AS admit_rate "
    "FROM `workspace`.`prove_it`.`berkeley_admissions` "
    "WHERE `gender` IS NOT NULL AND `applicants` IS NOT NULL GROUP BY `gender`"
)
SPREAD_V2 = (
    "SELECT `gender`, COUNT(*) AS students, AVG(`maths_score`) AS avg_score, "
    "STDDEV(`maths_score`) AS spread FROM `workspace`.`prove_it`.`student_scores` "
    "WHERE `gender` IS NOT NULL AND `maths_score` IS NOT NULL GROUP BY `gender`"
)
WINDOW_V1 = (
    "SELECT `year`, `combined_expenditure_share_gdp` "
    "FROM `workspace`.`prove_it`.`country_indicators` "
    "WHERE `entity` ILIKE '%Bulgaria%' AND `year` IN (1991, 1996) "
    "AND `combined_expenditure_share_gdp` IS NOT NULL ORDER BY `year` ASC;"
)
DENOMINATOR = (
    "WITH latest_year AS ( SELECT MAX(`year`) AS max_year "
    "FROM `workspace`.`prove_it`.`emissions` ), ranked_countries AS ( "
    "SELECT `country`, `co2`, RANK() OVER (ORDER BY `co2` DESC) AS rank "
    "FROM `workspace`.`prove_it`.`emissions` ) SELECT * FROM ranked_countries"
)


def notes_of(sql: str) -> str:
    return " ".join(f.note or "" for f in annotate(sql))


def test_a_query_that_does_not_exist_is_annotated_as_nothing() -> None:
    """A refused turn has no query, and a panel captioned "the query Genie wrote" over an
    empty box would be claiming one exists."""
    for empty in (None, "", "   "):
        assert annotate(empty) == ()


@pytest.mark.parametrize("sql", [PARADOX, SPREAD_V2, WINDOW_V1, DENOMINATOR])
def test_the_fragments_reassemble_into_the_query_exactly(sql: str) -> None:
    """The annotation is drawn over Genie's own SQL, not over a paraphrase of it.

    If the pieces did not concatenate back to the original, the panel would be showing a
    query Genie did not write — on the screen whose entire job is proving it did.
    """
    assert "".join(f.text for f in annotate(sql)) == sql


def test_the_table_loses_its_backticks_and_its_catalog() -> None:
    """`workspace`.`prove_it`.`student_scores` is not what a child calls a table.

    The first version emitted "the `emissions table" — a stray backtick — because it
    stripped the quoting before splitting on the dots rather than after.
    """
    said = notes_of(SPREAD_V2)
    assert "the student scores table" in said
    assert "`" not in said
    assert "workspace" not in said and "prove_it" not in said


def test_a_nested_call_is_read_as_the_rate_it_produces() -> None:
    """`try_divide(SUM(admitted), SUM(applicants))` is one rate, not two totals.

    The inner-call pattern matched the innermost brackets, so the note said "the total of
    admitted" and never mentioned the division that makes it a rate — on the case whose
    whole lesson is a pooled rate.
    """
    said = notes_of(PARADOX)
    assert "one number divided by another, as a rate" in said


def test_the_spread_reads_as_a_sentence() -> None:
    """ "how spread out of maths score is" was real output, because every function shared
    one "of {name}" template. Each carries its own preposition now."""
    said = notes_of(SPREAD_V2)
    assert "how spread out maths score is" in said
    assert "spread out of" not in said


def test_a_filter_that_picks_a_country_is_not_a_missing_value() -> None:
    """The window case's WHERE drops nulls AND selects Bulgaria AND picks two years.

    Sweeping every identifier in the clause into one list produced "skips rows with no
    entity", which describes the opposite of what that clause does — on the case whose
    trick IS the chosen window.
    """
    said = notes_of(WINDOW_V1)
    assert "Keeps only rows where entity is Bulgaria." in said
    assert "Keeps only year 1991 and 1996 — and nothing in between." in said
    assert "no entity" not in said
    assert "Ignores rows with no combined expenditure share gdp recorded" in said


def test_a_cte_alias_is_not_described_as_evidence() -> None:
    """`FROM latest_year` reads a working table this query just built, not a table the
    workspace holds. Calling it "the evidence: the latest year table" implied one exists."""
    said = notes_of(DENOMINATOR)
    assert "Reads back the working table this query built above." in said
    assert "the latest year table" not in said


def test_every_note_on_a_cte_query_is_locally_true() -> None:
    """The clause patterns run inside CTEs, so each note must describe only what it covers.

    A whole-query summary announced "asks for the biggest of year" about a per-person
    ranking. Annotating locally is what makes the hard query safe to explain at all.
    """
    said = notes_of(DENOMINATOR)
    assert "Builds a working table first" in said
    assert "Compares each row against all the others, in order." in said
    assert "the emissions table" in said


def fixture_queries() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for path in sorted((ROOT / "fixtures").glob("case-*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))

        def walk(node: object, name: str = path.name) -> None:
            if isinstance(node, dict):
                sql = node.get("sql")
                if isinstance(sql, str) and sql.strip():
                    found.append((name, sql))
                for value in node.values():
                    walk(value, name)
            elif isinstance(node, list):
                for item in node:
                    walk(item, name)

        walk(payload)
    return found


def test_the_fixtures_have_queries_to_annotate() -> None:
    """Guards the parametrised test below against silently covering nothing."""
    assert len(fixture_queries()) >= 10


@pytest.mark.parametrize("name,sql", fixture_queries(), ids=lambda v: str(v)[:40])
def test_every_recorded_query_gets_readable_notes(name: str, sql: str) -> None:
    """Each query the app can show gets annotated, and none of the notes are debris."""
    fragments = annotate(sql)
    notes = [f.note for f in fragments if f.note]
    assert notes, f"{name}: nothing annotated at all"
    assert "".join(f.text for f in fragments) == sql, f"{name}: fragments are lossy"
    for note in notes:
        assert note.endswith("."), f"{name}: {note!r} is not a sentence"
        assert "`" not in note, f"{name}: {note!r} leaks SQL quoting"
        assert "_" not in note, f"{name}: {note!r} leaks a raw column name"
        assert "out of " not in note, f"{name}: {note!r} reads badly"


def test_a_comma_inside_a_quoted_value_is_not_a_list_separator() -> None:
    """`IN ('Korea, Rep.', 'Egypt, Arab Rep.')` filters two countries, not four.

    Splitting the list on commas described a two-country filter as a four-country one, with
    total confidence — on exactly the comma-bearing names the window case's own table is
    full of. Found by a reviewer, not by the fixtures, which only ship a numeric IN list.
    """
    said = notes_of("SELECT * FROM t WHERE `entity` IN ('Korea, Rep.', 'Egypt, Arab Rep.')")
    assert "Keeps only entity Korea, Rep. and Egypt, Arab Rep." in said


def test_a_numeric_in_list_still_splits_on_commas() -> None:
    """The quoted-value rule must not break the unquoted case the docket actually uses."""
    said = notes_of("SELECT * FROM t WHERE `year` IN (1991, 1996)")
    assert "Keeps only year 1991 and 1996 — and nothing in between." in said


def test_a_bracket_inside_a_string_literal_is_not_a_bracket() -> None:
    """`AVG(CASE WHEN x LIKE '%(%' THEN 1 ELSE 0 END)` is an ordinary conditional rate.

    Counting every parenthesis alike meant the scan never found the closing bracket, so the
    aggregate went unexplained — and the LIKE pattern produced "keeps only rows where x is
    (", which is worse than silence.
    """
    said = notes_of("SELECT AVG(CASE WHEN `x` LIKE '%(%' THEN 1 ELSE 0 END) AS r FROM t")
    assert "This works out the average of x." in said
    assert "is (." not in said


def test_an_unbalanced_call_is_left_alone() -> None:
    """A call that never closes gets no note, and the text still round-trips."""
    sql = "SELECT AVG(`x` FROM t"
    fragments = annotate(sql)
    assert "".join(f.text for f in fragments) == sql
    assert not any("average" in (f.note or "") for f in fragments)
