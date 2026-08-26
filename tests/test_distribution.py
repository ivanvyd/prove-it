"""Reading group shape out of the returned rows.

The rule this suite protects: draw nothing unless all three numbers are there. A cloud
rendered from a half-read table would look exactly as confident as a correct one, and the
child has no way to tell the difference.
"""

import pytest

from prove_it.domain.distribution import GroupShape, group_shapes, overlap_fraction
from prove_it.domain.verdict import Column, ResultTable

REAL = ResultTable(
    [Column(c) for c in ("gender", "students", "avg_maths_score", "spread")],
    [["boy", "4812", "492.6", "91.7"], ["girl", "4903", "488.1", "87.2"]],
)


def test_reads_the_three_numbers_genie_returned() -> None:
    shapes = group_shapes(REAL)
    assert shapes == [
        GroupShape("boy", 4812, 492.6, 91.7),
        GroupShape("girl", 4903, 488.1, 87.2),
    ]


def test_column_order_does_not_matter() -> None:
    shuffled = ResultTable(
        [Column(c) for c in ("spread", "gender", "avg_score", "students")],
        [["91.7", "boy", "492.6", "4812"], ["87.2", "girl", "488.1", "4903"]],
    )
    assert [s.name for s in group_shapes(shuffled)] == ["boy", "girl"]
    assert group_shapes(shuffled)[0].spread == 91.7


@pytest.mark.parametrize(
    "table",
    [
        # The naive first query — no spread, so nothing to draw.
        ResultTable(
            [Column("gender"), Column("avg_score")],
            [["boy", "492.6"], ["girl", "488.1"]],
        ),
        # Spread but no count.
        ResultTable(
            [Column("gender"), Column("avg_score"), Column("spread")],
            [["boy", "492.6", "91.7"], ["girl", "488.1", "87.2"]],
        ),
        # A group missing a number.
        ResultTable(
            [Column(c) for c in ("gender", "students", "avg_score", "spread")],
            [["boy", "4812", "492.6", "91.7"], ["girl", "4903", "488.1", None]],
        ),
        # Nonsense spread.
        ResultTable(
            [Column(c) for c in ("gender", "students", "avg_score", "spread")],
            [["boy", "4812", "492.6", "0"], ["girl", "4903", "488.1", "87.2"]],
        ),
    ],
)
def test_an_incompletely_described_group_draws_nothing(table: ResultTable) -> None:
    assert group_shapes(table) == []


def test_no_table_at_all_is_survivable() -> None:
    assert group_shapes(None) == []
    assert group_shapes(ResultTable([], [])) == []


def test_the_overlap_is_almost_total_for_the_real_numbers() -> None:
    """A 4.5 gap against a ~90 spread means these are the same crowd."""
    overlap = overlap_fraction(group_shapes(REAL))
    assert overlap is not None
    assert overlap > 0.95, f"expected near-total overlap, got {overlap:.3f}"


def test_two_genuinely_separate_groups_barely_overlap() -> None:
    apart = [GroupShape("a", 100, 100.0, 5.0), GroupShape("b", 100, 160.0, 5.0)]
    overlap = overlap_fraction(apart)
    assert overlap is not None
    assert overlap < 0.01


def test_overlap_needs_exactly_two_groups() -> None:
    assert overlap_fraction([]) is None
    assert overlap_fraction(group_shapes(REAL)[:1]) is None


def test_unequal_spreads_are_not_reported_as_total_overlap() -> None:
    """The textbook 2·Φ(−|Δ|/2σ) shortcut assumes equal spreads and is badly wrong here.

    Same mean, spreads of 10 and 40: the shortcut says the groups overlap completely. They
    do not — about 42% of their mass is shared. This number is shown to a child, so a
    confidently wrong statistic is exactly the thing the app teaches them to catch.
    """
    same_centre = [GroupShape("a", 100, 100.0, 10.0), GroupShape("b", 100, 100.0, 40.0)]
    overlap = overlap_fraction(same_centre)

    assert overlap is not None
    assert overlap < 0.55, "the equal-variance shortcut would have said 1.0"
    assert 0.35 < overlap < 0.50


def test_identical_groups_overlap_completely() -> None:
    twins = [GroupShape("a", 100, 50.0, 8.0), GroupShape("b", 100, 50.0, 8.0)]
    overlap = overlap_fraction(twins)
    assert overlap is not None and overlap > 0.98


def test_the_shipped_headline_number_is_defensible() -> None:
    """The claim a child actually reads for the demo data."""
    overlap = overlap_fraction(group_shapes(REAL))
    assert overlap is not None
    assert 0.95 <= overlap <= 0.99, f"got {overlap:.3f}"


def test_a_numeric_group_label_is_still_used_as_the_label() -> None:
    """year_group 7 and 8 are a real grouping; calling them group 1 and 2 loses the point."""
    by_year = ResultTable(
        [Column(c) for c in ("year_group", "students", "avg_score", "spread")],
        [["7", "120", "65.2", "12.1"], ["8", "130", "70.5", "11.4"]],
    )
    assert [s.name for s in group_shapes(by_year)] == ["7", "8"]


def test_a_text_label_still_wins_over_a_numeric_one() -> None:
    both = ResultTable(
        [Column(c) for c in ("year_group", "gender", "students", "avg_score", "spread")],
        [["7", "boy", "120", "65.2", "12.1"], ["8", "girl", "130", "70.5", "11.4"]],
    )
    assert [s.name for s in group_shapes(both)] == ["boy", "girl"]
