"""Building a docket from whatever the workspace has, rather than from what mine had.

The five curated cases name five specific tables. Anyone who clones this repo into their
own workspace — a judge, most obviously — has none of them, and every case is a dead end.
These tests pin the way out: match trick archetypes against Unity Catalog's own
description of the tables, and generate a case for the best fit.

Everything here works on names, types and comments. Nothing looks inside a column, because
the app writes no SQL and a discovery pass that profiled values would break the rule worth
half the contest score.
"""

from __future__ import annotations

from prove_it.domain.archetypes import ARCHETYPES
from prove_it.domain.discovery import (
    DiscoveredColumn,
    DiscoveredTable,
    best_matches,
    claim_for,
    follow_up_for,
    humanise,
    match_table,
)
from prove_it.domain.verdict import ColumnRole, column_role


def table(name: str, *cols: tuple[str, str]) -> DiscoveredTable:
    return DiscoveredTable(
        full_name=f"workspace.demo.{name}",
        columns=tuple(DiscoveredColumn(n, t) for n, t in cols),
    )


# The real shapes, as Unity Catalog reported them from a live workspace.
PUPILS = table(
    "student_scores",
    ("student_id", "INT"),
    ("gender", "STRING"),
    ("maths_score", "DOUBLE"),
    ("reading_score", "DOUBLE"),
    ("school_id", "STRING"),
    ("year_group", "INT"),
    ("exam_year", "INT"),
)
ADMISSIONS = table(
    "berkeley_admissions",
    ("department", "STRING"),
    ("gender", "STRING"),
    ("applicants", "INT"),
    ("admitted", "INT"),
)
EMISSIONS = table(
    "emissions",
    ("country", "STRING"),
    ("year", "INT"),
    ("co2", "DOUBLE"),
    ("co2_per_capita", "DOUBLE"),
)


# -- reading a column's job off its name ----------------------------------------------


def test_an_identifier_never_becomes_a_measure_however_numeric_it_is() -> None:
    """`student_id` averages to a number that means nothing, and a case built on one
    would be arithmetic with no subject."""
    assert column_role("student_id", "INT") is ColumnRole.IDENTIFIER
    assert column_role("school_id", "STRING") is ColumnRole.IDENTIFIER


def test_the_specific_roles_win_over_the_generic_ones() -> None:
    """`co2_per_capita` is a per-unit figure before it is a measure, and `admit_rate` is a
    rate before anything else. Reversing that order lets the generic patterns swallow the
    columns the specific judges depend on."""
    assert column_role("co2_per_capita", "DOUBLE") is ColumnRole.PER_UNIT
    assert column_role("admit_rate", "DOUBLE") is ColumnRole.RATE
    assert column_role("co2", "DOUBLE") is ColumnRole.MEASURE


def test_a_word_that_is_not_a_number_is_a_label() -> None:
    assert column_role("gender", "STRING") is ColumnRole.LABEL
    assert column_role("country", "STRING") is ColumnRole.LABEL


def test_a_year_is_a_year_whatever_type_it_is_stored_as() -> None:
    assert column_role("year", "INT") is ColumnRole.YEAR
    assert column_role("year", "STRING") is ColumnRole.YEAR


def test_the_tried_and_succeeded_pair_is_recognised() -> None:
    """Without both, a rate cannot be computed and the pooled-rate trick has nothing to
    stand on."""
    assert column_role("applicants", "INT") is ColumnRole.TRIED
    assert column_role("admitted", "INT") is ColumnRole.SUCCEEDED


# -- matching a table to a trick ------------------------------------------------------


def test_an_admissions_table_carries_the_pooled_rate_trick() -> None:
    best = match_table(ADMISSIONS)
    assert best, "a tried/succeeded pair with two labels must match something"
    assert best[0].archetype.key == "pooled_rate"
    assert best[0].subgroup is not None, "the breakdown needs a second thing to split by"


def test_an_emissions_table_carries_the_missing_denominator() -> None:
    best = match_table(EMISSIONS)
    assert best[0].archetype.key == "denominator"


def test_a_pupil_table_carries_the_hidden_spread() -> None:
    keys = [m.archetype.key for m in match_table(PUPILS)]
    assert "spread" in keys


def test_a_table_missing_a_required_role_matches_nothing_rather_than_guessing() -> None:
    """Better no case than a case whose query cannot be asked."""
    useless = table("lookup", ("code", "STRING"), ("label_text", "STRING"))
    assert match_table(useless) == []


def test_a_rate_table_with_only_one_label_cannot_be_broken_down() -> None:
    """Simpson's paradox needs something to compare AND something to split by. One label
    gives you the pooled rate and nowhere to go."""
    flat = table("flat", ("gender", "STRING"), ("applicants", "INT"), ("admitted", "INT"))
    assert [m.archetype.key for m in match_table(flat)] != ["pooled_rate"]


# -- building the docket --------------------------------------------------------------


def test_each_table_contributes_at_most_one_case() -> None:
    """A docket showing one table four times reads as four ways of asking one question."""
    matches = best_matches([PUPILS, ADMISSIONS, EMISSIONS])
    assert len(matches) == 3
    assert len({m.table.full_name for m in matches}) == 3


def test_an_empty_catalog_yields_an_empty_docket_rather_than_an_error() -> None:
    assert best_matches([]) == []


def test_a_catalog_of_junk_yields_nothing_rather_than_nonsense() -> None:
    junk = [table("t1", ("a_id", "STRING")), table("t2", ("note", "STRING"))]
    assert best_matches(junk) == []


# -- the wording ----------------------------------------------------------------------


def test_a_column_name_is_said_the_way_a_person_would_say_it() -> None:
    assert humanise("maths_score") == "maths score"
    assert humanise("avg_score") == "average score"
    assert humanise("co2_per_capita") == "co2 per capita"


def test_a_generated_claim_names_the_column_it_will_actually_be_tested_on() -> None:
    match = match_table(PUPILS)[0]
    claim = claim_for(match)
    assert claim
    assert claim[0].islower(), claim
    assert any(word in claim for word in ("score", "maths", "reading")), claim


def test_a_generated_follow_up_names_the_split_it_will_ask_for() -> None:
    match = next(m for m in match_table(ADMISSIONS) if m.archetype.key == "pooled_rate")
    assert "{subgroup}" not in follow_up_for(match), "the template must be filled in"


def test_no_generated_string_ever_quotes_a_figure_or_a_source() -> None:
    """The lesson belongs to the SHAPE, not the table. A curated case can cite Bickel 1975
    because someone checked it; an archetype cannot cite anything, because it does not know
    what table it will be bound to."""
    for archetype in ARCHETYPES:
        prose = " ".join(
            [archetype.lesson, archetype.in_the_wild, archetype.nudge, archetype.trick]
        )
        assert "%" not in prose, f"{archetype.key} quotes a figure"
        assert "19" not in prose and "20" not in prose, f"{archetype.key} names a year"


# -- the docket this workspace can actually play --------------------------------------


def test_a_workspace_without_my_tables_still_gets_a_docket() -> None:
    """The complaint this whole module exists for. Someone clones the repo into their own
    workspace, has none of `student_scores`/`berkeley_admissions`/`emissions`, and used to
    get five cases that all dead-end."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    theirs = [
        table("sales", ("region", "STRING"), ("rep", "STRING"), ("revenue", "DOUBLE")),
        table(
            "hiring",
            ("team", "STRING"),
            ("stage", "STRING"),
            ("applicants", "INT"),
            ("accepted", "INT"),
        ),
    ]
    docket = build_docket(DOCKET, theirs)

    assert docket, "a workspace with usable tables must never show an empty docket"
    assert all(not c.probed for c in docket), "none of these were measured against Genie"
    assert {c.table for c in docket} <= {"sales", "hiring"}
    assert not any(c.table == "student_scores" for c in docket), (
        "a curated case whose table is absent is a dead end and must not be offered"
    )


def test_curated_cases_survive_where_their_table_is_present() -> None:
    """In the workspace they were written for, nothing changes: the probed cases are
    better than anything discovery can generate, because their arcs were measured."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    mine = [
        PUPILS,
        ADMISSIONS,
        EMISSIONS,
        table(
            "country_indicators",
            ("entity", "STRING"),
            ("year", "INT"),
            ("combined_expenditure_share_gdp", "DOUBLE"),
        ),
    ]
    docket = build_docket(DOCKET, mine)

    keys = {c.key for c in docket}
    assert {"spread", "reading", "paradox", "window", "denominator"} <= keys
    assert all(c.probed for c in docket if c.key in {"spread", "paradox"})


def test_discovery_never_duplicates_a_table_a_curated_case_already_covers() -> None:
    """Otherwise Berkeley appears twice: once as the checked Simpson's paradox case and
    once as a generated near-copy of it."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    docket = build_docket(DOCKET, [ADMISSIONS])
    assert [c.table for c in docket] == ["berkeley_admissions"]
    assert len(docket) == 1


def test_an_unreadable_catalog_keeps_the_curated_docket_rather_than_emptying_it() -> None:
    """Discovery failing must not take the app down with it. Offline mode and missing
    credentials both land here."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    assert build_docket(DOCKET, []) == list(DOCKET)


def test_a_generated_case_says_where_it_came_from() -> None:
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    docket = build_docket(
        DOCKET,
        [
            table(
                "hiring",
                ("team", "STRING"),
                ("stage", "STRING"),
                ("applicants", "INT"),
                ("accepted", "INT"),
            )
        ],
    )
    case = docket[0]
    assert "workspace.demo.hiring" in case.source
    assert case.probed is False


def test_a_generated_case_claims_no_arc_it_has_not_measured() -> None:
    """A curated case advertises `HOLDS -> BUSTED` because someone ran it. A generated one
    must not promise a flip that may never happen."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket

    # A table no curated case covers, or `build_docket` correctly returns the probed one.
    theirs = table(
        "power_use", ("country", "STRING"), ("kwh", "DOUBLE"), ("kwh_per_capita", "DOUBLE")
    )
    docket = build_docket(DOCKET, [theirs])
    generated = docket[0]
    assert generated.probed is False
    assert generated.turns_the_verdict is False, "no unmeasured case may advertise a flip"


def test_cases_the_app_cannot_read_are_named_rather_than_silently_dropped() -> None:
    """The bug this whole reporting path exists for.

    A Databricks App runs as its own service principal, not as the person who deployed it.
    Ours had SELECT on two of four tables, so the docket quietly became three cases long —
    nothing errored, nothing looked wrong, and there was no way to tell from the screen
    that two cases were missing. Dropping a case the app cannot run is right; dropping it
    silently is the omission this product spends its runtime arguing against.
    """
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import build_docket, hidden_cases

    # Exactly what the service principal could see: two of the four tables.
    visible = [
        PUPILS,
        table(
            "country_indicators",
            ("entity", "STRING"),
            ("year", "INT"),
            ("combined_expenditure_share_gdp", "DOUBLE"),
        ),
    ]
    docket = build_docket(DOCKET, visible)
    hidden = hidden_cases(DOCKET, visible)

    assert len(docket) == 3, "the observed symptom: DOCKET 0/3 instead of 0/5"
    assert {c.table for c in hidden} == {"berkeley_admissions", "emissions"}
    assert all(c.probed for c in hidden), "only checked cases can go missing this way"


def test_nothing_is_reported_hidden_when_the_catalog_could_not_be_read() -> None:
    """No catalog means no knowledge, not bad news. The curated docket stands whole, so
    there is nothing missing to report — claiming otherwise would be alarming and wrong."""
    from prove_it.domain.cases import DOCKET
    from prove_it.domain.discovery import hidden_cases

    assert hidden_cases(DOCKET, []) == []


def test_a_huge_catalog_yields_a_docket_not_a_catalogue() -> None:
    """Measured against a synthetic 500-table catalog: every one matched, because the
    weakest archetype needs only a measure and a label and almost any table has both.

    The docket screen renders a card and a button per case on every Streamlit rerun, so an
    uncapped docket turned "point it at your own schema" — which the mapping panel
    explicitly invites — into hundreds of cards rebuilt on every click.
    """
    from prove_it.domain.discovery import MAX_DISCOVERED, best_matches, matches_dropped

    tables = []
    for i in range(500):
        cols = [DiscoveredColumn(f"name_{i}", "STRING"), DiscoveredColumn(f"amount_{i}", "DOUBLE")]
        tables.append(DiscoveredTable(f"cat.sch.t{i}", tuple(cols)))

    matches = best_matches(tables)
    assert len(matches) == MAX_DISCOVERED
    # And the cap is reported rather than silent — a truncation nobody is told about
    # reads as "this is everything".
    assert matches_dropped(tables) == 500 - MAX_DISCOVERED


def test_the_cap_keeps_the_strongest_matches() -> None:
    """Truncating the sorted list is only correct if it is still sorted by confidence."""
    from prove_it.domain.discovery import best_matches

    strong = ADMISSIONS  # pooled rate: the highest-specificity archetype
    weak = [
        DiscoveredTable(
            f"cat.sch.w{i}",
            (DiscoveredColumn(f"name_{i}", "STRING"), DiscoveredColumn(f"amount_{i}", "DOUBLE")),
        )
        for i in range(20)
    ]
    matches = best_matches([*weak, strong])
    assert matches[0].archetype.key == "pooled_rate", "the strongest match must survive the cap"
