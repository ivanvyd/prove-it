"""Turning the added columns into named exhibits.

The retrial screen needs to say what each new column *revealed*, not just that it appeared.
Everything narrated here has to come from the rows Genie returned — the moment this starts
inventing a phrase the arithmetic cannot back, the screen becomes theatre and the app loses
the thing it is arguing for.

Note the deliberate framing: the narration describes what the column showed, never that v2
beat v1. A courtroom has a winner, and a child who learns "newer queries win" has learned
the wrong rule.
"""

import pytest

from prove_it.domain.exhibits import Exhibit, exhibits_for
from prove_it.domain.verdict import Column, ResultTable, analyse

V1 = "SELECT `gender`, AVG(`maths_score`) AS avg_maths_score FROM `t` GROUP BY `gender`"
V2 = (
    "SELECT `gender`, COUNT(*) AS students, AVG(`maths_score`) AS avg_maths_score, "
    "STDDEV(`maths_score`) AS spread FROM `t` GROUP BY `gender`"
)

RESULT = ResultTable(
    [Column(c) for c in ("gender", "students", "avg_maths_score", "spread")],
    [["boy", "4812", "492.6", "91.7"], ["girl", "4903", "488.1", "87.2"]],
)


def build() -> list[Exhibit]:
    return exhibits_for(V1, V2, RESULT, analyse(RESULT))


def test_one_exhibit_per_column_genie_added() -> None:
    found = build()
    assert [e.alias for e in found] == ["students", "spread"]
    assert [e.label for e in found] == ["A", "B"]


def test_each_exhibit_quotes_the_real_numbers_from_the_rows() -> None:
    """Narration must be readable off the table, not invented."""
    by_alias = {e.alias: e for e in build()}

    assert "4,812" in by_alias["students"].narration
    assert "4,903" in by_alias["students"].narration
    assert "91.7" in by_alias["spread"].narration or "92" in by_alias["spread"].narration


def test_the_spread_exhibit_explains_the_overlap_rather_than_the_win() -> None:
    """The lesson is that v2 is fairer, not that it is stronger."""
    spread = {e.alias: e for e in build()}["spread"]

    lowered = spread.narration.lower()
    assert "overlap" in lowered or "same range" in lowered or "vary" in lowered
    for triumphal in ("beat", "wins", "better query", "wrong query"):
        assert triumphal not in lowered


def test_the_sql_fragment_is_carried_so_the_badge_can_sit_on_it() -> None:
    fragments = {e.alias: e.fragment for e in build()}
    assert "COUNT(*) AS students" in fragments["students"]
    assert "STDDEV" in fragments["spread"]


def test_a_column_with_no_special_meaning_still_gets_an_honest_line() -> None:
    v2 = "SELECT `gender`, AVG(`x`) AS avg_x, MIN(`x`) AS lowest FROM `t` GROUP BY `gender`"
    table = ResultTable(
        [Column(c) for c in ("gender", "avg_x", "lowest")],
        [["boy", "10.0", "2.0"], ["girl", "11.0", "3.0"]],
    )
    found = exhibits_for(
        "SELECT `gender`, AVG(`x`) AS avg_x FROM `t` GROUP BY `gender`", v2, table, analyse(table)
    )

    assert [e.alias for e in found] == ["lowest"]
    assert found[0].narration, "an unrecognised column still needs something true said about it"
    # Whole numbers render without a trailing .0 — "2 and 3" is what a child should read.
    assert "2 and 3" in found[0].narration


def test_no_added_columns_means_no_exhibits() -> None:
    assert exhibits_for(V1, V1, RESULT, analyse(RESULT)) == []


@pytest.mark.parametrize("missing", [None, ""])
def test_missing_sql_is_survivable(missing: str | None) -> None:
    assert exhibits_for(missing, missing, RESULT, analyse(RESULT)) == []


def test_a_column_added_in_sql_but_absent_from_the_rows_is_skipped() -> None:
    """Genie can alias something the result set does not carry; do not narrate a guess."""
    v2 = V2 + ", MAX(`x`) AS ceiling"
    found = exhibits_for(V1, v2, RESULT, analyse(RESULT))
    assert "ceiling" not in [e.alias for e in found]


# -- the weighting exhibit, which the paradox case needs -----------------------------


def _berkeley_breakdown() -> ResultTable:
    from prove_it.case_data import BERKELEY

    return ResultTable(
        [Column(c) for c in ("department", "gender", "applicants", "admitted")],
        [
            row
            for d in BERKELEY
            for row in (
                [d.department, "men", str(d.men_applied), str(d.men_admitted)],
                [d.department, "women", str(d.women_applied), str(d.women_admitted)],
            )
        ],
    )


def test_a_subgroup_repair_produces_no_column_exhibits() -> None:
    """The gap this exists to fill, stated as a test.

    `exhibits_for` narrates the columns a repair ADDED. A breakdown adds a GROUP BY and no
    column at all, so it finds nothing — and the flagship case reached the retrial screen
    with an empty exhibits list.
    """
    from prove_it.domain.verdict import analyse

    table = _berkeley_breakdown()
    before = "SELECT gender, SUM(applicants) AS applicants FROM t GROUP BY gender"
    after = (
        "SELECT department, gender, SUM(applicants) AS applicants "
        "FROM t GROUP BY department, gender"
    )
    assert exhibits_for(before, after, table, analyse(table)) == []


def test_the_weighting_exhibit_explains_who_applied_where() -> None:
    from prove_it.domain.exhibits import weighting_exhibits

    found = weighting_exhibits(_berkeley_breakdown())
    assert len(found) == 2

    joined = " ".join(e.narration for e in found)
    # Read off the rows, not written down: men 825+560+325, women 108+25+593.
    assert "1,710 men" in joined and "726 women" in joined
    assert "981 men" in joined and "1,109 women" in joined
    assert "reason the totals disagree" in joined


def test_the_easiest_and_hardest_halves_do_not_overlap() -> None:
    """Every subgroup appears in exactly one half, or the arithmetic double-counts."""
    from prove_it.domain.exhibits import weighting_exhibits

    first, second = (e.narration for e in weighting_exhibits(_berkeley_breakdown()))
    in_first = {d for d in "ABCDEF" if f"{d}," in first}
    in_second = {d for d in "ABCDEF" if f"{d}," in second}

    assert in_first | in_second == set("ABCDEF"), "a department went missing"
    assert not (in_first & in_second), "a department appears in both halves"
    assert len(in_first) == len(in_second) == 3


def test_too_few_subgroups_produce_nothing() -> None:
    """Two subgroups cannot be split into halves without comparing one against one."""
    from prove_it.domain.exhibits import weighting_exhibits

    small = ResultTable(
        [Column(c) for c in ("dept", "gender", "applicants", "admitted")],
        [
            ["A", "men", "100", "80"],
            ["A", "women", "100", "50"],
            ["B", "men", "100", "70"],
            ["B", "women", "100", "40"],
        ],
    )
    assert weighting_exhibits(small) == []


def test_a_table_that_is_not_a_breakdown_produces_nothing() -> None:
    from prove_it.domain.exhibits import weighting_exhibits

    assert weighting_exhibits(None) == []
    flat = ResultTable(
        [Column("gender"), Column("avg_score")], [["boy", "492.6"], ["girl", "488.1"]]
    )
    assert weighting_exhibits(flat) == []
