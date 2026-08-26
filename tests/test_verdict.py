"""The verdict engine is the one place the app is allowed to draw a conclusion.

Every case here is a shape Genie can really return, including the shapes it returns when
it has not understood the question.
"""

import pytest

from prove_it.domain.verdict import (
    Analysis,
    Column,
    ResultTable,
    Verdict,
    analyse,
)


def table(columns: list[str], rows: list[list[str | None]]) -> ResultTable:
    return ResultTable([Column(c) for c in columns], rows)


# The two shapes the demo turns on -------------------------------------------------

V1 = table(
    ["gender", "avg_score"],
    [["boy", "494.2"], ["girl", "489.1"]],
)

V2 = table(
    ["gender", "students", "avg_score", "spread"],
    [["boy", "4812", "494.2", "92.6"], ["girl", "4903", "489.1", "88.4"]],
)


def test_means_only_makes_a_small_gap_look_real() -> None:
    """Genie's naive first draft. With no spread, 5 points looks like a finding."""
    result = analyse(V1)
    assert result.verdict is Verdict.HOLDS
    assert result.judged_on_spread is False
    assert result.delta == pytest.approx(5.1, abs=0.01)


def test_the_same_gap_dies_once_spread_is_in_the_query() -> None:
    """The whole lesson: same rows, same gap, one more column, opposite verdict."""
    result = analyse(V2)
    assert result.verdict is Verdict.BUSTED
    assert result.judged_on_spread is True
    assert result.effect_size == pytest.approx(0.056, abs=0.005)
    assert "overlap" in result.reason


def test_a_genuinely_large_gap_survives_the_spread_check() -> None:
    """The engine must not simply always bust a claim once spread appears."""
    big = table(
        ["gender", "students", "avg_score", "spread"],
        [["boy", "4812", "560.0", "40.0"], ["girl", "4903", "489.1", "38.0"]],
    )
    result = analyse(big)
    assert result.verdict is Verdict.HOLDS
    assert result.judged_on_spread is True
    assert result.effect_size > 1.0


def test_pooled_spread_is_weighted_by_group_size_when_counts_are_present() -> None:
    lopsided = table(
        ["gender", "students", "avg_score", "spread"],
        [["boy", "10", "500.0", "10.0"], ["girl", "9990", "480.0", "100.0"]],
    )
    result = analyse(lopsided)
    # Pooled towards the large group's spread, not the midpoint of 10 and 100.
    # Unweighted pooling would give sqrt((10^2 + 100^2)/2) ~= 71, a materially different
    # effect size, so this number is what proves the weighting is applied.
    assert result.pooled_spread == pytest.approx(99.9, abs=1.0)


def test_the_negligible_threshold_is_a_hard_boundary() -> None:
    """0.2 is a convention, so pin both sides of it deliberately rather than by accident."""
    just_under = table(
        ["gender", "avg_score", "spread"],
        [["boy", "519.0", "100.0"], ["girl", "500.0", "100.0"]],
    )
    just_over = table(
        ["gender", "avg_score", "spread"],
        [["boy", "521.0", "100.0"], ["girl", "500.0", "100.0"]],
    )
    assert analyse(just_under).verdict is Verdict.BUSTED
    assert analyse(just_over).verdict is Verdict.HOLDS


# Everything that must degrade to CANT_TELL rather than raising ---------------------


@pytest.mark.parametrize(
    ("name", "bad"),
    [
        ("one group", table(["gender", "avg_score"], [["boy", "494.2"]])),
        ("no rows", table(["gender", "avg_score"], [])),
        (
            "three groups",
            table(
                ["region", "avg_score"],
                [["north", "1"], ["south", "2"], ["east", "3"]],
            ),
        ),
        (
            "no average column",
            table(["gender", "pupils"], [["boy", "10"], ["girl", "12"]]),
        ),
        (
            "averages are not numbers",
            table(["gender", "avg_score"], [["boy", "n/a"], ["girl", "unknown"]]),
        ),
        (
            "spread is not a number",
            table(
                ["gender", "avg_score", "spread"],
                [["boy", "494.2", "-"], ["girl", "489.1", "-"]],
            ),
        ),
        (
            "no variation at all",
            table(
                ["gender", "avg_score", "spread"],
                [["boy", "500", "0"], ["girl", "480", "0"]],
            ),
        ),
        (
            "null average",
            table(["gender", "avg_score"], [["boy", None], ["girl", "489.1"]]),
        ),
    ],
)
def test_unreadable_results_are_cant_tell_never_an_error(name: str, bad: ResultTable) -> None:
    result = analyse(bad)
    assert result.verdict is Verdict.CANT_TELL, name
    assert result.reason, "a CANT_TELL must explain itself to the child"


@pytest.mark.parametrize("special", ["NaN", "nan", "Infinity", "-Infinity", "inf"])
def test_non_finite_numbers_are_not_numbers(special: str) -> None:
    """Spark stringifies NaN and Infinity into results because JSON cannot hold them.

    `float()` accepts every one of these, so without an explicit finiteness check a NaN
    average reaches the child as "the higher average, by nan" — a confident verdict built
    on a non-number.
    """
    in_mean = table(["gender", "avg_score"], [["boy", special], ["girl", "489.1"]])
    assert analyse(in_mean).verdict is Verdict.CANT_TELL

    in_spread = table(
        ["gender", "students", "avg_score", "spread"],
        [["boy", "10", "494.2", special], ["girl", "10", "489.1", "88.4"]],
    )
    assert analyse(in_spread).verdict is Verdict.CANT_TELL


def test_a_column_merely_ending_in_n_is_not_a_group_count() -> None:
    """ "correlation" ends in "n". Matching it as a count made the variance negative, and
    a negative variance raised to 0.5 is complex, which crashed the comparison."""
    collision = table(
        ["gender", "avg_score", "spread", "correlation"],
        [["boy", "500.0", "40.0", "-50"], ["girl", "480.0", "1.0", "60"]],
    )
    result = analyse(collision)

    assert result.verdict in {Verdict.HOLDS, Verdict.BUSTED}
    assert result.pooled_spread is not None
    assert isinstance(result.pooled_spread, float)
    assert result.pooled_spread > 0


def test_a_column_that_is_not_a_count_is_not_treated_as_one() -> None:
    """Names that merely contain the letters must not be read as group sizes."""
    from prove_it.domain.verdict import _COUNT_NAMES

    for name in ("correlation", "median", "duration", "attention", "percentile"):
        assert not _COUNT_NAMES.search(name), name


def test_a_real_count_column_is_still_used_for_weighting() -> None:
    """The pattern must recognise genuine count columns, snake_case included.

    Underscore is a word character, so an earlier `\\b`-anchored version silently stopped
    matching `student_count` and `row_count` — the exact aliases Genie emits — and quietly
    fell back to unweighted pooling, which can change the verdict a child is shown.
    """
    for name in (
        "students",
        "count",
        "n",
        "total",
        "rows",
        "student_count",
        "row_count",
        "total_count",
        "n_students",
        "num_students",
    ):
        weighted = table(
            ["gender", name, "avg_score", "spread"],
            [["boy", "10", "500.0", "10.0"], ["girl", "9990", "480.0", "100.0"]],
        )
        result = analyse(weighted)
        assert result.pooled_spread == pytest.approx(99.9, abs=1.0), name


def test_nonsense_counts_fall_back_to_unweighted_pooling() -> None:
    nonsense = table(
        ["gender", "students", "avg_score", "spread"],
        [["boy", "-5", "500.0", "40.0"], ["girl", "0", "480.0", "30.0"]],
    )
    result = analyse(nonsense)
    # Unweighted: sqrt((40^2 + 30^2) / 2) = 35.36
    assert result.pooled_spread == pytest.approx(35.36, abs=0.1)


def test_identical_averages_bust_the_claim_outright() -> None:
    same = table(["gender", "avg_score"], [["boy", "492.0"], ["girl", "492.0"]])
    assert analyse(same).verdict is Verdict.BUSTED


def test_thousands_separators_in_returned_cells_are_read_as_numbers() -> None:
    """Genie formats large numbers with commas often enough to matter."""
    commas = table(
        ["region", "students", "avg_score", "spread"],
        [["north", "12,400", "500.0", "90.0"], ["south", "11,900", "504.0", "88.0"]],
    )
    result = analyse(commas)
    assert result.verdict is Verdict.BUSTED
    assert result.pooled_spread == pytest.approx(89.0, abs=1.0)


def test_group_labels_are_taken_from_the_first_non_numeric_column() -> None:
    result: Analysis = analyse(V2)
    assert result.groups == ("boy", "girl")


def test_the_stated_gap_matches_the_numbers_on_screen() -> None:
    """Genie returns full precision; the rows render at one decimal place.

    Measuring the gap before rounding put "by 4.6" on the same screen as a table reading
    492.6 and 488.1 and a chart captioned "a gap of 4.5". A child who subtracts the two
    visible numbers must get the number the app just said, or the app is doing the exact
    thing it teaches them to catch.
    """
    table = ResultTable(
        [Column("gender"), Column("avg_maths_score")],
        [["boy", "492.64332917705605"], ["girl", "488.0624311645937"]],
    )
    analysis = analyse(table)

    assert "4.5" in analysis.reason, analysis.reason
    assert "4.6" not in analysis.reason
    assert analysis.delta is not None
    assert abs(analysis.delta) == pytest.approx(492.6 - 488.1, abs=1e-9)


# -- rates that are not rates ---------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "columns", "rows"),
    [
        (
            "a percentage past 100 that the x100 heuristic cannot recognise",
            [Column("group_name", "STRING"), Column("admit_rate", "DOUBLE")],
            [["men", "145"], ["women", "50"]],
        ),
        (
            "a negative rate",
            [Column("group_name", "STRING"), Column("admit_rate", "DOUBLE")],
            [["men", "-10"], ["women", "50"]],
        ),
        (
            "counts that do not nest — more admitted than applied",
            [Column("gender", "STRING"), Column("applicants", "INT"), Column("admitted", "INT")],
            [["men", "10", "50"], ["women", "100", "20"]],
        ),
    ],
)
def test_a_rate_outside_zero_to_one_is_cant_tell_and_never_an_exception(
    label: str, columns: list[Column], rows: list[list[str]]
) -> None:
    """Found by an independent correctness review and reproduced before the fix.

    `_cohens_h` takes `asin(sqrt(p))`, undefined outside 0..1, and nothing upstream
    guaranteed the range: `k / n` is only a proportion if the counts mean what their names
    suggest, and the x100 heuristic cannot tell 145 from a percentage. All three shapes
    below raised `ValueError: math domain error`, which escaped `commit_call` uncaught and
    reached the player as a raw traceback — the precise opposite of the rule that any
    result shape degrades to CANT_TELL.

    The sibling test named for this invariant existed already but was parametrised only
    with two-means tables, so the rate judge's half of it was never exercised. This matters
    more since discovery began generating cases from tables nobody probed: a tried/succeeded
    pair matched on column names alone is exactly where counts that do not nest turn up.
    """
    analysis = analyse(ResultTable(columns=columns, rows=rows))
    assert analysis.verdict is Verdict.CANT_TELL, label
