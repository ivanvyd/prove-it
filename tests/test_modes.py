"""The four judges added for the case docket.

Every table here is the shape Genie actually returned during the live probe — the same
column names, the same row counts, the same values. That matters more than it looks: a
judge tested against a table someone designed for it will pass and then meet
`try_divide(SUM(admitted), SUM(applicants)) AS admit_rate` in production and have nothing
to say. The real shapes are recorded in `probe-runs/case-probe.json`.

Dispatch is on shape and never on which case is playing, so each test also pins which
judge a shape reaches. That is the property that lets a typed claim reach these judges
without anyone having anticipated it.
"""

from __future__ import annotations

import pytest

from prove_it.case_data import BERKELEY
from prove_it.domain.verdict import Column, ResultTable, Verdict, analyse


def table(names: list[str], rows: list[list[str | None]]) -> ResultTable:
    return ResultTable([Column(n) for n in names], rows)


# -- Berkeley, the flagship ----------------------------------------------------------
#
# v1 columns: gender, applicants, admitted, admit_rate       (2 rows)
# v2 columns: department, gender, applicants, admitted, admit_rate   (12 rows)

BERKELEY_V1 = table(
    ["gender", "applicants", "admitted", "admit_rate"],
    [
        ["men", "2691", "1198", "0.4452"],
        ["women", "1835", "557", "0.3035"],
    ],
)

BERKELEY_V2 = table(
    ["department", "gender", "applicants", "admitted", "admit_rate"],
    [
        row
        for d in BERKELEY
        for row in (
            [d.department, "men", str(d.men_applied), str(d.men_admitted), f"{d.men_rate:.4f}"],
            [
                d.department,
                "women",
                str(d.women_applied),
                str(d.women_admitted),
                f"{d.women_rate:.4f}",
            ],
        )
    ],
)


def test_the_pooled_admissions_query_holds() -> None:
    """The naive answer, and it is honestly true at the level it was asked."""
    result = analyse(BERKELEY_V1)
    assert result.verdict is Verdict.HOLDS
    assert result.mode == "rates"
    assert result.leader == "men"
    assert "44.5" in result.reason and "30.4" in result.reason


def test_the_department_breakdown_busts_it() -> None:
    """Simpson's paradox, decided by counting rather than by asserting."""
    result = analyse(BERKELEY_V2)
    assert result.verdict is Verdict.BUSTED
    assert result.mode == "subgroups"
    assert result.reversed_in == 4
    assert result.subgroup_count == 6
    assert "4 of the 6" in result.reason


def test_the_breakdown_reports_the_same_pooled_figures_as_the_naive_query() -> None:
    """Both turns must agree about the overall number, or the reversal looks like a
    different question rather than the same one seen properly."""
    naive, split = analyse(BERKELEY_V1), analyse(BERKELEY_V2)
    assert naive.means is not None and split.means is not None
    assert naive.means[0] == pytest.approx(split.means[0], abs=0.15)
    assert naive.means[1] == pytest.approx(split.means[1], abs=0.15)


def test_a_breakdown_that_does_not_reverse_still_holds() -> None:
    """Cynicism is the failure mode on the other side: scrutiny has to be able to confirm."""
    consistent = table(
        ["department", "gender", "applicants", "admitted"],
        [
            ["A", "men", "100", "80"],
            ["A", "women", "100", "50"],
            ["B", "men", "100", "70"],
            ["B", "women", "100", "40"],
            ["C", "men", "100", "60"],
            ["C", "women", "100", "30"],
        ],
    )
    result = analyse(consistent)
    assert result.verdict is Verdict.HOLDS
    assert result.reversed_in == 0
    assert "did not change the answer" in result.reason


@pytest.mark.parametrize(
    ("one", "other"),
    [("men", "women"), ("boy", "girl"), ("Dept A", "Dept B")],
    ids=["plural", "singular", "proper noun"],
)
def test_a_verdict_sentence_never_disagrees_with_its_own_label(one: str, other: str) -> None:
    """Group names come from Genie's rows and can be singular, plural or a proper noun.

    "Overall men comes out ahead" reached a live screen, because the sentence template
    assumed a singular subject. The templates are phrased without a verb that has to agree
    with the label, and this pins that: the label appears, and the singular verb does not.
    """
    # A genuine reversal, so the BUSTED sentence - the one carrying both labels - is what
    # gets checked. Pooled favours `one` on weight of numbers; three of four subgroups
    # favour `other`.
    breakdown = table(
        ["department", "gender", "applicants", "admitted"],
        [
            ["A", one, "100", "80"],
            ["A", other, "10", "9"],
            ["B", one, "100", "70"],
            ["B", other, "10", "8"],
            ["C", one, "10", "2"],
            ["C", other, "100", "25"],
            ["D", one, "100", "60"],
            ["D", other, "10", "5"],
        ],
    )
    result = analyse(breakdown)
    assert result.verdict is Verdict.BUSTED, "the fixture must reverse, or only one label shows"
    reason = result.reason
    assert one in reason and other in reason
    for singular_verb in (f"{one} comes", f"{other} comes", f"{one} is ", f"{other} is "):
        assert singular_verb not in reason, f"sentence assumes a singular subject: {reason}"


@pytest.mark.parametrize(
    ("one", "other"),
    [("men", "women"), ("boy", "girl"), ("Dept A", "Dept B")],
    ids=["plural", "singular", "proper noun"],
)
def test_the_two_means_sentence_also_never_agrees_with_its_label(one: str, other: str) -> None:
    """The same rule, on the judge the test above did not reach.

    The agreement check only ever covered the subgroup sentence, so the two-means one kept
    "{label} has the higher average" and shipped it to a recorded screen as "boy has the
    higher average, by 4.5." — which would have become "boys has" the moment the generator
    used plural labels. A rule enforced on one of five judges is not enforced.
    """
    means = table(["gender", "avg_score"], [[one, "492.6"], [other, "488.1"]])
    result = analyse(means)

    assert result.verdict is Verdict.HOLDS
    assert one in result.reason
    for singular_verb in (f"{one} has", f"{other} has", f"{one} is ", f"{other} is "):
        assert singular_verb not in result.reason, (
            f"sentence assumes a singular subject: {result.reason}"
        )


def test_rates_too_close_together_are_busted() -> None:
    close = table(
        ["gender", "applicants", "admitted"],
        [["man", "1000", "500"], ["woman", "1000", "505"]],
    )
    result = analyse(close)
    assert result.verdict is Verdict.BUSTED
    assert "too close" in result.reason


def test_a_percentage_point_gap_is_judged_against_where_it_sits() -> None:
    """Cohen's h, not a raw gap: five points at 50% is noise, five points at 2% is not."""
    middle = table(
        ["group", "applicants", "admitted"],
        [["a", "1000", "500"], ["b", "1000", "530"]],
    )
    low = table(
        ["group", "applicants", "admitted"],
        [["a", "1000", "10"], ["b", "1000", "40"]],
    )
    assert analyse(middle).verdict is Verdict.BUSTED
    assert analyse(low).verdict is Verdict.HOLDS


# -- the window ----------------------------------------------------------------------


def test_a_two_point_window_reports_what_it_shows() -> None:
    """The naive answer honours the years it was given. It is not wrong, it is narrow."""
    result = analyse(
        table(["year", "combined_expenditure_share_gdp"], [["1991", "5.43"], ["1996", "2.23"]])
    )
    assert result.verdict is Verdict.HOLDS
    assert result.mode == "series"
    assert "fell" in result.reason


def test_the_whole_series_makes_the_window_half_true() -> None:
    """Bulgaria's real series: the collapse happened, and it was not the trend."""
    series = [
        (1980, 3.53),
        (1990, 4.45),
        (1991, 5.43),
        (1992, 5.26),
        (1993, 4.95),
        (1994, 4.17),
        (1995, 2.37),
        (1996, 2.23),
        (1998, 2.74),
        (2001, 3.38),
        (2008, 4.22),
        (2013, 4.06),
        (2019, 4.21),
        (2022, 4.50),
    ]
    result = analyse(
        table(["year", "combined_expenditure_share_gdp"], [[str(y), str(v)] for y, v in series])
    )
    assert result.verdict is Verdict.HALF_TRUE
    assert result.mode == "series"
    assert "2.23" in result.reason, "it should name the low point it really reached"
    assert "not the trend" in result.reason


def test_a_series_that_really_did_decline_is_not_softened() -> None:
    """HALF_TRUE must not become the answer to everything. A real fall still holds."""
    result = analyse(
        table(
            ["year", "value"], [["2000", "9.0"], ["2005", "7.0"], ["2010", "5.0"], ["2020", "3.0"]]
        )
    )
    assert result.verdict is Verdict.HOLDS
    assert "fell" in result.reason


def test_a_series_that_only_rose_busts_a_claim_of_decline() -> None:
    result = analyse(table(["year", "value"], [["2000", "1.0"], ["2010", "2.0"], ["2020", "3.0"]]))
    assert result.verdict is Verdict.BUSTED
    assert "rose" in result.reason


# -- the denominator -----------------------------------------------------------------
#
# v1 columns: country, co2, year, rank   (159 rows, ranked by total)
# v2 columns: country, co2, co2_per_capita, year   (10 rows, ranked per person)

EMISSIONS_V1 = table(
    ["country", "co2", "year", "rank"],
    [
        ["China", "11902.5", "2023", "1"],
        ["United States", "4911.4", "2023", "2"],
        ["India", "3062.3", "2023", "3"],
        ["Russia", "1815.9", "2023", "4"],
    ],
)

EMISSIONS_V2 = table(
    ["country", "co2", "co2_per_capita", "year"],
    [
        ["Qatar", "128.4", "38.84", "2023"],
        ["Bahrain", "35.1", "23.27", "2023"],
        ["Trinidad and Tobago", "32.0", "22.83", "2023"],
        ["United States", "4911.4", "14.30", "2023"],
    ],
)


def test_the_total_ranking_holds() -> None:
    result = analyse(EMISSIONS_V1)
    assert result.verdict is Verdict.HOLDS
    assert result.mode == "ranking"
    assert result.leader == "China"
    assert "2.4 times" in result.reason


def test_a_single_year_ranking_is_not_read_as_a_series() -> None:
    """Every row carries year 2023. Reading the column's presence rather than its distinct
    values sent this to the series judge, which had nothing true to say about it."""
    assert analyse(EMISSIONS_V1).mode == "ranking"


def test_per_person_overturns_the_total_without_calling_it_false() -> None:
    result = analyse(EMISSIONS_V2, previous=EMISSIONS_V1)
    assert result.verdict is Verdict.HALF_TRUE
    assert result.mode == "per_unit"
    assert result.leader == "Qatar"
    assert result.previous_leader == "China"
    assert "Both are true" in result.reason


def test_per_person_without_the_previous_turn_makes_no_claim_about_a_change() -> None:
    """It cannot know it overturned anything, so it must not say it did."""
    result = analyse(EMISSIONS_V2)
    assert result.verdict is Verdict.HOLDS
    assert result.previous_leader is None
    assert "was top" not in result.reason


def test_a_leader_that_survives_the_denominator_still_holds() -> None:
    same = table(
        ["country", "co2", "co2_per_capita", "year"],
        [["Qatar", "128.4", "38.84", "2023"], ["Bahrain", "35.1", "23.27", "2023"]],
    )
    previous = table(
        ["country", "co2", "year"],
        [["Qatar", "128.4", "2023"], ["Bahrain", "35.1", "2023"]],
    )
    result = analyse(same, previous=previous)
    assert result.verdict is Verdict.HOLDS
    assert "top either way" in result.reason


# -- the original case still routes where it did -------------------------------------


def test_the_spread_case_is_untouched() -> None:
    naive = table(["gender", "avg_score"], [["boy", "492.64"], ["girl", "488.06"]])
    repaired = table(
        ["gender", "students", "avg_score", "spread"],
        [["boy", "4812", "492.64", "91.7"], ["girl", "4903", "488.06", "87.2"]],
    )
    assert analyse(naive).verdict is Verdict.HOLDS
    assert analyse(naive).mode == "means"
    assert analyse(repaired).verdict is Verdict.BUSTED
    assert analyse(repaired).judged_on_spread


# -- everything else falls through to CANT_TELL --------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        table([], []),
        table(["gender"], [["boy"], ["girl"]]),
        table(["year", "value"], [["2000", "not a number"]]),
        table(["country", "co2_per_capita"], [["Qatar", "n/a"]]),
        table(["department", "gender", "applicants"], [["A", "men", "0"], ["A", "women", "0"]]),
    ],
    ids=["empty", "no measure", "one bad year", "bad per-person", "no sizes"],
)
def test_unreadable_shapes_land_on_cant_tell(bad: ResultTable) -> None:
    """Never an error screen, for any shape. CANT_TELL is a first-class outcome."""
    assert analyse(bad).verdict is Verdict.CANT_TELL


def test_a_nan_never_reaches_a_verdict() -> None:
    """Spark stringifies NaN into JSON results, and float() accepts it."""
    result = analyse(table(["year", "value"], [["2000", "NaN"], ["2010", "3.0"]]))
    assert result.verdict is Verdict.CANT_TELL
