"""The reversal picture, and the rates it draws.

Two things are being protected. The chart must draw exactly what the subgroup judge
decided — if the picture recomputed the rates itself the two could disagree, and the one
panel where that must never happen is the one whose subject is a number and a picture
telling different stories. And it inherits every trap `pupil_cloud.py` paid for, because
it is the same kind of object: an inline script rendering Genie's labels into a
self-sizing frame.
"""

from __future__ import annotations

import json

import pytest

from prove_it.case_data import BERKELEY
from prove_it.domain.verdict import Column, ResultTable, Verdict, analyse, subgroup_rates
from prove_it.ui.reversal_chart import chart_height, render_reversal

BERKELEY_TABLE = ResultTable(
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


# -- the rates the chart is given ----------------------------------------------------


def test_the_rates_match_the_published_figures() -> None:
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    assert len(groups) == 6
    by_name = {g.name: g for g in groups}

    # Department A: 512/825 men, 89/108 women.
    assert by_name["A"].left_rate == pytest.approx(62.06, abs=0.01)
    assert by_name["A"].right_rate == pytest.approx(82.41, abs=0.01)
    assert pooled[0] == pytest.approx(44.52, abs=0.02)
    assert pooled[1] == pytest.approx(30.35, abs=0.02)


def test_four_of_six_favour_women_exactly_as_the_verdict_says() -> None:
    """The chart and the sentence must never be able to disagree about the count."""
    groups, _ = subgroup_rates(BERKELEY_TABLE)
    drawn = sum(1 for g in groups if g.favours_right)
    judged = analyse(BERKELEY_TABLE)

    assert judged.verdict is Verdict.BUSTED
    assert drawn == judged.reversed_in == 4
    assert len(groups) == judged.subgroup_count == 6


def test_the_sizes_come_through_because_they_are_the_reason() -> None:
    """The reversal is caused by who applied where; a chart without sizes hides the cause."""
    groups, _ = subgroup_rates(BERKELEY_TABLE)
    by_name = {g.name: g for g in groups}
    assert by_name["A"].right_size == 108
    assert by_name["F"].right_size == 341


def test_a_table_that_is_not_a_breakdown_yields_nothing() -> None:
    flat = ResultTable(
        [Column("gender"), Column("applicants"), Column("admitted")],
        [["men", "100", "50"], ["women", "100", "40"]],
    )
    groups, pooled = subgroup_rates(flat)
    assert groups == []
    assert pooled == (0.0, 0.0)


# -- what gets drawn -----------------------------------------------------------------


def test_the_chart_draws_every_subgroup_and_the_total() -> None:
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    payload = json.loads(html[html.index("var D = ") + 8 : html.index(";\n  var root")])

    assert len(payload["rows"]) == 6
    assert payload["pooled"]["left"] == pytest.approx(44.5, abs=0.05)
    assert payload["pooled"]["right"] == pytest.approx(30.4, abs=0.05)


def test_the_total_is_drawn_on_the_same_axis_as_the_groups() -> None:
    """A second panel with its own scale would hide that the total is made of the rows
    above it, which is the only thing the picture is for."""
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    assert "the same six groups added up" in html
    # One canvas, one axis.
    assert html.count("<canvas") == 1


def test_the_reading_names_the_count_and_the_disagreement() -> None:
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    assert "did better in 4 of the 6 groups" in html
    assert "the total still favours men" in html


def test_the_reading_does_not_assume_a_singular_label() -> None:
    """Rendered live, this line read "men still comes out ahead" — the same defect the
    verdict sentences had, reintroduced in the chart. Group names come from Genie's rows
    and can be singular, plural or a proper noun."""
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    for label in ("men", "women"):
        for singular_verb in (f"{label} comes", f"{label} is ", f"{label} has "):
            assert singular_verb not in html, f"the reading assumes a singular subject: {label}"


def test_nothing_is_drawn_without_at_least_two_subgroups() -> None:
    assert render_reversal([], (0.0, 0.0)) == ""
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    assert render_reversal(groups[:1], pooled) == ""


def test_the_height_grows_with_the_number_of_subgroups() -> None:
    groups, _ = subgroup_rates(BERKELEY_TABLE)
    assert chart_height(groups) > chart_height(groups[:3])


# -- the traps this file inherits ----------------------------------------------------


def test_a_subgroup_label_cannot_close_the_script_block() -> None:
    """Subgroup names come out of Genie's rows, which this app does not control."""
    hostile = ResultTable(
        [Column(c) for c in ("dept", "gender", "applicants", "admitted")],
        [
            ["</script><script>alert(1)</script>", "men", "100", "50"],
            ["</script><script>alert(1)</script>", "women", "100", "60"],
            ["B", "men", "100", "50"],
            ["B", "women", "100", "60"],
        ],
    )
    groups, pooled = subgroup_rates(hostile)
    html = render_reversal(groups, pooled)

    assert "</script><script>alert(1)" not in html
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1


def test_the_frame_measures_its_content_not_the_document() -> None:
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    assert "style.height = Math.ceil(root.getBoundingClientRect().height" in html
    assert "style.height = document.documentElement.scrollHeight" not in html


def test_the_canvas_height_is_never_read_back_off_the_element() -> None:
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    assert "getAttribute('height')" not in html
    assert "var H = D.height;" in html


def test_the_canvas_never_asks_for_a_css_variable() -> None:
    """A canvas context cannot resolve a CSS custom property; handed one it paints black."""
    groups, pooled = subgroup_rates(BERKELEY_TABLE)
    html = render_reversal(groups, pooled)
    script = html[html.index("<script>") :]
    assert "fillStyle = 'var(" not in script
    assert "strokeStyle = 'var(" not in script
