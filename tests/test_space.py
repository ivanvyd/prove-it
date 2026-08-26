"""The Genie space configuration, checked for the things the docket depends on.

These instructions are the most load-bearing configuration in the product and the least
visible from the code that relies on them. Nothing in Python breaks if someone reasonably
decides Genie should be more helpful and volunteers the spread in its first answer — every
test stays green, the app still runs, and every case in the docket quietly stops having a
lesson.

So the properties the cases rest on are asserted here rather than left to a careful reader.
"""

from __future__ import annotations

import pytest

from prove_it.genie.space import INSTRUCTIONS, TABLES, instruction_lines


def test_tables_are_sorted_by_identifier() -> None:
    """The serialized_space API rejects any other order, with an error that never
    mentions sorting."""
    assert list(TABLES) == sorted(TABLES)


def test_every_case_table_is_declared() -> None:
    needed = {
        "workspace.prove_it.student_scores",
        "workspace.prove_it.berkeley_admissions",
        "workspace.prove_it.country_indicators",
        "workspace.prove_it.emissions",
    }
    assert needed <= set(TABLES)


def test_no_duplicate_tables() -> None:
    assert len(set(TABLES)) == len(TABLES)


# -- the rule the whole docket rests on ----------------------------------------------


def test_answering_exactly_what_was_asked_is_stated_and_prioritised() -> None:
    """Every case is the gap between a plain first answer and a fairer second one.

    An instruction set that makes Genie thorough does not improve the app, it deletes the
    lesson from all four cases at once.
    """
    assert "ANSWER EXACTLY WHAT WAS ASKED" in INSTRUCTIONS
    assert "most important rule" in INSTRUCTIONS
    body = INSTRUCTIONS[INSTRUCTIONS.index("ANSWER EXACTLY WHAT WAS ASKED") :]
    for volunteered in ("standard deviations", "breakdowns", "per-person figures"):
        assert volunteered in body, f"the rule should forbid volunteering {volunteered}"


def test_the_naive_answer_is_protected_for_each_case_shape() -> None:
    """One clause per case, each stopping the first answer from pre-empting its repair."""
    # paradox: do not split by department unless asked
    assert "Do not break the answer down by department unless you are asked to" in INSTRUCTIONS
    # window: honour a named period rather than widening it
    assert "If the question names a period or two particular years, return only those" in (
        INSTRUCTIONS
    )


def test_a_rate_is_never_summed() -> None:
    """The probe caught Genie returning SUM(co2_per_capita) across 270 years.

    That is not a slow query or an odd shape, it is arithmetic that means nothing, and it
    was presented as an answer. The rule exists because the model will otherwise treat a
    rate column like any other numeric column.
    """
    assert "NEVER ADD UP A FIGURE THAT IS ALREADY PER PERSON" in INSTRUCTIONS
    assert "produces a number that means nothing" in INSTRUCTIONS


def test_biggest_returns_a_ranking_not_a_winner() -> None:
    """A single row cannot show a rank flip, and the flip is the denominator case."""
    assert "top ten" in INSTRUCTIONS
    assert "not just the single leader" in INSTRUCTIONS


def test_cant_tell_is_instructed_rather_than_guessed_at() -> None:
    assert "WHEN THE DATA CANNOT ANSWER THE QUESTION" in INSTRUCTIONS
    assert "Do not guess" in INSTRUCTIONS
    assert "name the column that would be needed" in INSTRUCTIONS


def test_genie_does_not_editorialise_about_claims() -> None:
    """A model volunteering that a claim is offensive answers the question the app is
    deliberately refusing to answer for the player."""
    assert "never as a fact to be confirmed" in INSTRUCTIONS
    assert "the data answers, not you" in INSTRUCTIONS


# -- what the app reads --------------------------------------------------------------


@pytest.mark.parametrize("alias", ["avg_score", "spread", "students", "admit_rate"])
def test_stable_column_aliases_are_named(alias: str) -> None:
    """The verdict engine dispatches on returned column names, so these are an interface
    between two systems that never import each other."""
    assert alias in INSTRUCTIONS


def test_every_table_is_described_to_the_model() -> None:
    for table in TABLES:
        short = table.rsplit(".", 1)[-1]
        assert short in INSTRUCTIONS, f"{short} is declared but never described"


def test_the_berkeley_description_prevents_a_university_wide_claim() -> None:
    """The pooled figures from six departments are not the famous university-wide ones."""
    assert "only those six departments" in INSTRUCTIONS


def test_emissions_is_described_as_countries_only() -> None:
    """Aggregates are filtered at load. Saying so stops Genie hunting for a World row."""
    assert "no World or continent row" in INSTRUCTIONS


# -- the payload shape ---------------------------------------------------------------


def test_instructions_serialise_as_a_list_of_lines() -> None:
    """`content` is a list of lines, not one string with newlines in it."""
    lines = instruction_lines()
    assert isinstance(lines, list)
    assert len(lines) > 20
    assert all(isinstance(line, str) for line in lines)
    assert not any("\n" in line for line in lines)


def test_no_trailing_blank_line() -> None:
    lines = instruction_lines()
    assert lines[0].strip()
    assert lines[-1].strip()
