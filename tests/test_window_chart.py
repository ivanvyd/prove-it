"""The window chart, and the points it draws.

Bulgaria's real series throughout, because the case is about a real decline and a test
against invented numbers would not catch a chart that flatters it.
"""

from __future__ import annotations

import json

from prove_it.domain.verdict import Column, ResultTable, Verdict, analyse, series_points
from prove_it.ui.window_chart import render_window

BULGARIA = [
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

FULL = ResultTable(
    [Column("year"), Column("combined_expenditure_share_gdp")],
    [[str(y), str(v)] for y, v in BULGARIA],
)


# -- the points --------------------------------------------------------------------


def test_the_points_are_read_and_sorted() -> None:
    points = series_points(FULL)
    assert len(points) == len(BULGARIA)
    assert points == sorted(points)
    assert points[0] == (1980, 3.53)
    assert points[-1] == (2022, 4.50)


def test_the_chart_draws_what_the_judge_measured() -> None:
    """A picture that re-read the table could pick a different value column."""
    analysis = analyse(FULL)
    points = series_points(FULL)
    assert analysis.verdict is Verdict.HALF_TRUE
    assert analysis.whole_series == (points[0][1], points[-1][1])


def test_rows_out_of_order_are_still_read_in_order() -> None:
    shuffled = ResultTable(
        [Column("year"), Column("v")],
        [["2000", "1.0"], ["1990", "2.0"], ["2010", "3.0"]],
    )
    assert series_points(shuffled) == [(1990, 2.0), (2000, 1.0), (2010, 3.0)]


def test_a_table_with_no_year_yields_nothing() -> None:
    assert series_points(None) == []
    assert series_points(ResultTable([Column("gender")], [["boy"]])) == []


# -- what gets drawn -----------------------------------------------------------------


def test_the_series_is_drawn_with_its_window() -> None:
    html = render_window(series_points(FULL), window=(1991, 1996))
    payload = json.loads(html[html.index("var D = ") + 8 : html.index(";\n  var root")])

    assert len(payload["points"]) == len(BULGARIA)
    assert payload["window"] == [1991, 1996]


def test_the_reading_says_where_it_ended_up() -> None:
    html = render_window(series_points(FULL), window=(1991, 1996))
    assert "ends higher than it started" in html
    assert "3.53" in html and "4.50" in html


def test_the_window_note_names_the_real_low_point() -> None:
    """The band must not be dismissed. The fall genuinely happened."""
    html = render_window(series_points(FULL), window=(1991, 1996))
    assert "2.23" in html
    assert "They are real" in html


def test_without_a_window_no_band_is_claimed() -> None:
    html = render_window(series_points(FULL))
    payload = json.loads(html[html.index("var D = ") + 8 : html.index(";\n  var root")])
    assert payload["window"] is None
    assert "Every year in the data." in html


def test_two_points_are_a_window_not_a_series() -> None:
    """Nothing to contrast a window against, so there is no honest chart to draw."""
    assert render_window([(1991, 5.43), (1996, 2.23)]) == ""
    assert render_window([]) == ""


def test_a_series_that_really_declined_says_lower() -> None:
    falling = [(2000, 9.0), (2005, 7.0), (2010, 5.0), (2020, 3.0)]
    assert "ends lower than it started" in render_window(falling)


# -- the axis argument ---------------------------------------------------------------


def test_the_axis_starts_at_zero() -> None:
    """Deliberately unlike the headline chart earlier in the same session.

    That one truncates its axis to make four points look decisive, and says so. This one
    is arguing about a trend, and a truncated axis here would be the app playing the exact
    trick it had just finished teaching.
    """
    html = render_window(series_points(FULL), window=(1991, 1996))
    assert "var floor = 0" in html
    # The axis label proves it to a reader, not just to the renderer.
    assert "ctx.fillText('0', left - 8, bottom + 3)" in html


# -- the traps this file inherits ----------------------------------------------------


def test_the_frame_measures_its_content_not_the_document() -> None:
    html = render_window(series_points(FULL))
    assert "style.height = Math.ceil(root.getBoundingClientRect().height" in html
    assert "style.height = document.documentElement.scrollHeight" not in html


def test_the_canvas_height_is_never_read_back_off_the_element() -> None:
    html = render_window(series_points(FULL))
    assert "getAttribute('height')" not in html
    assert "var H = D.height;" in html


def test_the_canvas_never_asks_for_a_css_variable() -> None:
    html = render_window(series_points(FULL))
    script = html[html.index("<script>") :]
    assert "fillStyle = 'var(" not in script
    assert "strokeStyle = 'var(" not in script


def test_the_payload_carries_no_raw_angle_bracket() -> None:
    """This chart takes only numbers today, so nothing hostile can reach the payload — but
    it is embedded in a <script> block exactly like the two that do, and the next person to
    add a label here should inherit the escaping rather than have to notice it.

    Checked on the emitted payload rather than by feeding in a string the function never
    receives, which is what the first version of this test did and proved nothing.
    """
    html = render_window(series_points(FULL), window=(1991, 1996))
    payload = html[html.index("var D = ") + 8 : html.index(";\n  var root")]

    assert "<" not in payload and ">" not in payload
    assert json.loads(payload)["window"] == [1991, 1996]
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1
