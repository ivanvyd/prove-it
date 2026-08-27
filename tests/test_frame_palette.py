"""Every inline-HTML component paints in the page's palette.

This exists because of a defect that no other test and no responsive sweep could see.

The six visuals are mounted with `st.components.v1.html`, which renders each one into a
sandboxed iframe. An iframe is a separate document, so the stylesheet's custom properties
never reach it: inside those frames `var(--rule, #E3E4DE)` always resolves to the fallback,
and a bare hex is simply a bare hex. Every one of them therefore carried its own copy of
the colours — and when the Case Files rework repainted `style.py`, the copies stayed on the
old paper-and-ink palette. The page was manila and serif; the flip beat, the Berkeley
reversal chart and the evidence room went on drawing themselves near-white and sans-serif.

Nothing caught it. The suite was green, `ruff` was clean, and the responsive sweep measured
overflow and console errors, not whether two documents agreed about what colour they were.
It is only visible by looking at a rendered frame next to the page it sits on.

So the check is mechanical: render every component and assert that each colour it emits is
one the palette actually declares. A future repaint of `PALETTE` cannot leave a frame
behind without turning this red.
"""

from __future__ import annotations

import re

import pytest

from prove_it.domain.distribution import GroupShape
from prove_it.domain.game import Call, Stake
from prove_it.domain.verdict import Subgroup
from prove_it.ui.board import render_board
from prove_it.ui.headline_chart import render_headline_chart
from prove_it.ui.interrogation import render_room
from prove_it.ui.kit import copy_frame
from prove_it.ui.pupil_cloud import render_cloud
from prove_it.ui.query_panel import render_query_panel
from prove_it.ui.reversal_chart import render_reversal
from prove_it.ui.style import FONTS, PALETTE
from prove_it.ui.window_chart import render_window

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
# A colour written as a numeric triplet is the same drift in different clothes. The
# Berkeley chart's gridlines were `rgba(95,108,122,…)` — a shade no palette token has —
# and the hex-only check waved them through.
RGB = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)")
# The pre-rework palette, named so a revert is caught by name rather than by absence.
RETIRED = {
    "#FBFAF6": "paper",
    "#17222C": "ink",
    "#E3E4DE": "rule",
    "#5F6C7A": "pencil",
    "#A83A34": "busted",
    "#21567F": "accent",
    "#F7F0E0": "nodata-soft",
}

SHAPES = [GroupShape("boy", 4812, 492.6, 91.7), GroupShape("girl", 4903, 488.1, 87.2)]
MEANS = [("boy", 492.6), ("girl", 488.1)]
SUBGROUPS = [
    Subgroup("A", "men", "women", 62.0, 82.0, 825, 108),
    Subgroup("B", "men", "women", 63.0, 68.0, 560, 25),
    Subgroup("C", "men", "women", 37.0, 34.0, 325, 593),
]


def _board() -> str:
    """The board at the retrial, which is the phase that draws every item it has: both
    warrants, the emptied bag, the strip, the stamps and the tag."""
    import os

    os.environ["PROVE_IT_OFFLINE"] = "1"
    from prove_it.config import Settings
    from prove_it.domain.cases import case_for
    from prove_it.domain.exhibits import exhibits_for
    from prove_it.session import Investigation

    case = case_for("paradox")
    assert case is not None
    inv = Investigation.open_case(case, Settings.from_env().build_client(case.key))
    inv.ask_genie()
    inv.commit_call(Call.TRICK, Stake.HUNCH, None)
    inv.repair(None, asked=case.follow_up)
    exhibits = exhibits_for(inv.first.sql, inv.second.sql, inv.second_result, inv.second_analysis)
    return render_board(inv, number=3, phase="retrial", exhibits=exhibits)


# The root element of each frame, and the selector its stylesheet declares it under. The
# root is what the rest of the component inherits from, so it is the one rule that must set
# a font — see the test below.
ROOTS = {
    "board": "body",
    "copy_frame": "button",
    "interrogation": ".ir",
    "reversal_chart": ".rv",
    "window_chart": ".wc",
    "pupil_cloud": ".pc",
    "headline_chart": ".hc",
    "query_panel": ".qp",
}

FRAMES = {
    "board": _board,
    "copy_frame": lambda: copy_frame("I checked a rumour against real data."),
    "interrogation": lambda: render_room(phase="THINKING", started_at_ms=1000.0, done=False),
    "reversal_chart": lambda: render_reversal(SUBGROUPS, (44.5, 30.4)),
    "window_chart": lambda: render_window(
        [(1990.0, 3.5), (1991.0, 4.1), (1992.0, 4.4), (1996.0, 3.9)], (1991.0, 1996.0)
    ),
    "pupil_cloud": lambda: render_cloud(SHAPES),
    "headline_chart": lambda: render_headline_chart(MEANS),
    "query_panel": lambda: render_query_panel(
        "SELECT `gender`, AVG(`maths_score`) AS avg_score "
        "FROM `workspace`.`prove_it`.`student_scores` GROUP BY `gender`"
    ),
}


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_a_frame_paints_only_in_colours_the_palette_declares(name: str) -> None:
    """The check that would have caught the rework leaving six frames behind."""
    markup = FRAMES[name]()
    assert markup, f"{name} rendered nothing, so this test proves nothing"

    declared = {value.upper() for value in PALETTE.values()}
    used = {match.upper() for match in HEX.findall(markup)}
    used |= {f"#{int(r):02X}{int(g):02X}{int(b):02X}" for r, g, b in RGB.findall(markup)}
    stray = sorted(used - declared)
    assert not stray, (
        f"{name} paints in {stray}, which the palette does not declare. "
        f"An iframe cannot read the page's CSS variables — import the value from "
        f"prove_it.ui.style instead of writing the hex here."
    )


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_no_frame_has_drifted_back_to_the_pre_rework_palette(name: str) -> None:
    """Named separately from the check above so the failure says *which* old colour came
    back, rather than only that some undeclared hex appeared."""
    markup = FRAMES[name]().upper()
    revived = {old: token for old, token in RETIRED.items() if old in markup}
    assert not revived, (
        f"{name} is painting in the retired palette again: "
        f"{ {old: f'was --{token}' for old, token in revived.items()} }"
    )


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_a_frame_sets_a_font_rather_than_inheriting_the_browser_default(name: str) -> None:
    """The other half of the same defect: the frames were sans-serif on a serif page.

    An iframe does not inherit the parent's font either, so a component that names no
    family gets the browser's default and reads as a different product.
    """
    markup = FRAMES[name]()
    assert "font-family" in markup, f"{name} names no font family at all"
    assert FONTS["mono"] in markup or FONTS["body"] in markup, (
        f"{name} sets a font, but not one of the two stacks the page uses — so it will "
        f"render in a different typeface from everything around it."
    )
    # Checked by absence as well as presence: a frame that names the right stack in one
    # rule and the old default in another still comes out sans-serif where it matters,
    # and the positive check above cannot see that.
    for default in ("system-ui", "-apple-system", "Segoe UI"):
        assert default not in markup, (
            f"{name} still falls back to {default!r}. Neither page stack contains it, so "
            f"whatever rule names it renders in a different typeface from the page."
        )


@pytest.mark.parametrize("name", sorted(FRAMES))
def test_the_frames_root_sets_a_font_so_children_inherit_one(name: str) -> None:
    """The subtler half, found by reading computed styles in a real browser.

    Every child in these components names its own font — except the notes. `.rv-note`, the
    caption under the Berkeley slopegraph that admits what the dots are, set a size, a
    line-height and a colour but no family. Its parent set none either, so it inherited the
    *document* default and rendered in Times New Roman: honest text, in the one typeface
    that appears nowhere else in the product, directly beneath the app's most load-bearing
    chart.

    Asserting on the root rule rather than on every child is deliberate — it is the rule
    that makes the question moot for every element below it.
    """
    markup = FRAMES[name]()
    root = ROOTS[name]
    start = markup.find(f"{root} {{")
    assert start != -1, f"{name} declares no rule for its root {root}"
    rule = markup[start : markup.find("}", start)]
    assert "font-family" in rule, (
        f"{name}'s root rule ({root}) sets no font-family, so any child that does not name "
        f"one inherits the browser default rather than the page's. Add font-family to "
        f"{root} rather than to each child that turns out to need it."
    )
