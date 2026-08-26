"""The two inline visuals, checked as strings.

Both render HTML with an embedded <script> block, and both take their content from Genie's
result rows — data this app does not control. That combination is the one place in the
codebase where a stray character stops being cosmetic.
"""

import json

import pytest

from prove_it.domain.distribution import GroupShape
from prove_it.ui.headline_chart import render_headline_chart
from prove_it.ui.pupil_cloud import BAND, FOOT, TOP, cloud_height, render_cloud

SHAPES = [
    GroupShape("boy", 4812, 492.6, 91.7),
    GroupShape("girl", 4903, 488.1, 87.2),
]


# -- the injection that matters ----------------------------------------------------


def test_a_group_label_cannot_close_the_script_block() -> None:
    """Group labels come out of Genie's rows. `json.dumps` does not escape `<`, and the
    browser finds `</script>` by scanning raw text rather than parsing JavaScript."""
    hostile = [
        GroupShape("</script><script>alert(1)</script>", 10, 1.0, 1.0),
        GroupShape("girl", 10, 2.0, 1.0),
    ]
    html = render_cloud(hostile)

    assert "</script><script>alert(1)" not in html
    assert "\\u003c/script\\u003e" in html
    # Exactly one script block, still closed exactly once.
    assert html.count("<script>") == 1
    assert html.count("</script>") == 1


def test_the_escaped_payload_is_still_valid_json() -> None:
    """Escaping must not corrupt the data — a JSON parser reads \\u003c as `<`."""
    html = render_cloud([GroupShape("a<b", 10, 1.0, 1.0), GroupShape("c&d", 10, 2.0, 1.0)])
    start = html.index("var D = ") + len("var D = ")
    end = html.index(";", start)
    parsed = json.loads(html[start:end])

    assert [g["name"] for g in parsed["groups"]] == ["a<b", "c&d"]


def test_a_label_with_quotes_survives() -> None:
    html = render_cloud([GroupShape('he said "hi"', 10, 1.0, 1.0), GroupShape("b", 10, 2.0, 1.0)])
    start = html.index("var D = ") + len("var D = ")
    parsed = json.loads(html[start : html.index(";", start)])
    assert parsed["groups"][0]["name"] == 'he said "hi"'


def test_the_chart_escapes_its_labels_too() -> None:
    html = render_headline_chart([("<img src=x>", 10.0), ("girl", 20.0)])
    assert "<img src=x>" not in html
    assert "&lt;img" in html


# -- self-sizing ---------------------------------------------------------------------


@pytest.mark.parametrize("renderer", ["cloud", "chart"])
def test_the_frame_measures_its_content_not_the_document(renderer: str) -> None:
    """documentElement.scrollHeight is at least the frame's own height, so feeding it back
    ratchets — the panel grew to fourteen thousand pixels before this was pinned."""
    html = (
        render_cloud(SHAPES)
        if renderer == "cloud"
        else render_headline_chart([("boy", 492.6), ("girl", 488.1)])
    )
    assert "style.height = Math.ceil(root.getBoundingClientRect().height" in html
    # The comment above the fix names the trap, so match the assignment rather than the
    # phrase.
    assert "style.height = document.documentElement.scrollHeight" not in html


def test_the_canvas_height_is_never_read_back_off_the_element() -> None:
    """The second ratchet, which survived the first fix and reached 28,395px in a browser.

    `canvas.height = H * dpr` reflects into the element's `height` attribute. Reading that
    attribute back on the next resize returns the backing-store size, so on a 2x display the
    CSS height doubles every time — and the self-sizing frame faithfully follows it up.
    """
    html = render_cloud(SHAPES)
    assert "getAttribute('height')" not in html
    assert "var H = D.height;" in html
    assert f'"height": {TOP + BAND * 2 + FOOT}' in html


# -- refusing to draw ----------------------------------------------------------------


def test_nothing_is_drawn_without_two_groups() -> None:
    assert render_cloud(SHAPES[:1]) == ""
    assert render_cloud([]) == ""
    assert render_headline_chart([("boy", 1.0)]) == ""
    assert render_headline_chart([]) == ""


def test_no_chart_when_the_two_averages_are_identical() -> None:
    """There is no gap to dramatise, so there is no lesson to draw."""
    assert render_headline_chart([("boy", 490.0), ("girl", 490.0)]) == ""


def test_no_chart_when_the_two_averages_are_identical_once_rounded() -> None:
    """A deliberate consequence of rounding before measuring, not an accident.

    The chart prints its labels at one decimal place, so two means less than 0.05 apart
    render as the same number. Drawing them would produce two bars of visibly different
    heights labelled `490.0` and `490.0`, captioned "a gap of 0.0" — a chart whose subject
    is misleading pictures, being one. Refusing to draw is the honest outcome.
    """
    assert render_headline_chart([("boy", 490.02), ("girl", 490.04)]) == ""
    assert render_headline_chart([("boy", 490.0), ("girl", 490.049)]) == ""


def test_a_gap_that_survives_rounding_still_draws() -> None:
    """The dead zone above must not be wider than one rounding step."""
    chart = render_headline_chart([("boy", 490.0), ("girl", 490.06)])
    assert chart, "0.06 apart rounds to 490.0 vs 490.1 and is a real, drawable gap"
    assert "490.1" in chart


# -- the honesty disclosure ----------------------------------------------------------


def test_the_cloud_says_the_dots_are_a_reconstruction() -> None:
    """Load-bearing: an app teaching children to distrust a confident summary cannot
    quietly present invented individuals as the class."""
    html = render_cloud(SHAPES)
    assert "not the individual rows" in html
    assert "three numbers Genie returned" in html


def test_the_chart_names_the_trick_it_is_playing() -> None:
    html = render_headline_chart([("boy", 492.6), ("girl", 488.1)])
    assert "axis starts at" in html
    assert "not 0" in html


def test_the_cloud_reports_the_real_total_not_the_drawn_sample() -> None:
    """Dots are capped for performance; the headcount must stay honest."""
    assert "9,715 pupils" in render_cloud(SHAPES)


def test_reduced_motion_is_respected() -> None:
    assert "prefers-reduced-motion" in render_cloud(SHAPES)


def test_cloud_height_grows_with_the_number_of_groups() -> None:
    three = [*SHAPES, GroupShape("other", 100, 490.0, 90.0)]
    assert cloud_height(three) > cloud_height(SHAPES)


def test_the_spread_can_be_driven_a_step_at_a_time() -> None:
    """The toggle animates on requestAnimationFrame, which suits a person and defeats a
    frame-by-frame screen recorder: the transition finishes in about a second of real
    time while a recorder has captured four frames, so the crowd appears to jump rather
    than spread. `__setMix` is the deterministic way in, and it is also the only way a
    test can reach the transition at all."""
    html = render_cloud(SHAPES)
    assert "window.__setMix" in html
    # It must move the caption too, or a stepped recording shows the wrong line under
    # the right picture.
    setter = html[html.index("window.__setMix") :]
    body = setter[: setter.index("};")]
    assert "caption()" in body and "draw()" in body


def test_every_place_that_states_the_gap_agrees() -> None:
    """Three components compute the same gap from the same rows, and all three appear on
    screen together. Two of them were rounding and one was not, so a rendered frame showed
    "Two averages, 4.6 apart" directly above "The gap is 4.5".

    Genie returns full precision; everything on screen is printed at one decimal place.
    The number a child gets by subtracting the two visible averages is the only number any
    of these may state.
    """
    import json
    import re

    from prove_it.domain.distribution import group_means
    from prove_it.domain.verdict import Column, ResultTable, analyse

    raw = ResultTable(
        [Column("gender"), Column("avg_maths_score")],
        [["boy", "492.64332917705605"], ["girl", "488.0624311645937"]],
    )
    expected = round(492.6 - 488.1, 1)

    verdict = analyse(raw).reason
    assert f"{expected:.1f}" in verdict, verdict

    chart = render_headline_chart(group_means(raw))
    assert float(re.search(r"a gap of\s+([\d.]+)", chart).group(1)) == expected

    cloud = render_cloud(SHAPES)
    payload = json.loads(cloud[cloud.index("var D = ") + 8 : cloud.index(";\n  var root")])
    means = [g["mean"] for g in payload["groups"]]
    assert round(abs(means[0] - means[1]), 1) == expected
    assert all(m == round(m, 1) for m in means), "the cloud must carry displayable means"


# -- the reversal chart's group labels ------------------------------------------------


def test_a_subgroup_label_cannot_inject_markup_into_the_reversal_chart() -> None:
    """Found by an independent security review, reproduced before it was fixed.

    `Subgroup.left/.right/.name` are `str(row[...])` straight off Genie's result rows —
    data this app does not control. `render_reversal` interpolated them into the HTML body
    with no escaping, and the frame it renders into is same-origin with scripts enabled, so
    a group label of `<img src=x onerror=...>` was script execution rather than a cosmetic
    bug. The sibling components all escaped or JSON-encoded the same class of value; this
    one did both for the payload and neither for the body.
    """
    from prove_it.domain.verdict import Subgroup
    from prove_it.ui.reversal_chart import render_reversal

    hostile = "<img src=x onerror=alert(1)>"
    groups = [
        Subgroup("A", hostile, "women", 62.0, 82.0, 825, 108),
        Subgroup("B", hostile, "women", 63.0, 68.0, 560, 25),
        Subgroup("C", hostile, "women", 37.0, 34.0, 325, 593),
    ]
    markup = render_reversal(groups, (44.5, 30.4))

    assert hostile not in markup, "a raw tag from Genie's rows reached the HTML body"
    assert "&lt;img" in markup, "the label should still be shown, escaped"


def test_the_reversal_chart_payload_is_not_double_escaped() -> None:
    """The other half of the same fix. The JSON payload is read back by `JSON.parse` and
    painted with `fillText` onto a canvas — which has no markup to inject into and would
    render `&amp;lt;` literally. Escaping at the source would have fixed the XSS and broken
    the picture, so the two destinations get different forms of the same name.
    """
    import json
    import re

    from prove_it.domain.verdict import Subgroup
    from prove_it.ui.reversal_chart import render_reversal

    groups = [
        Subgroup("A", "men", "women", 62.0, 82.0, 825, 108),
        Subgroup("B", "men", "women", 63.0, 68.0, 560, 25),
    ]
    markup = render_reversal(groups, (44.5, 30.4))
    payload = re.search(r"var D = (\{.*?\});", markup, re.S)
    assert payload, "the script payload should be findable"
    data = json.loads(
        payload.group(1).replace("\u003c", "<").replace("\u003e", ">").replace("\u0026", "&")
    )
    assert data["leftName"] == "men", "canvas labels must be the plain name"
