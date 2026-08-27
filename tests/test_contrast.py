"""Every colour pair the Evidence Room paints text in, against the WCAG 2.2 AA floor.

The design file is reproduced surface for surface — every flap, sheet, bag and slate is
the colour it was drawn in. Where the design's own INK on those surfaces fell short of
4.5:1, the ink was darkened by the smallest step that clears the floor and the surface was
left alone; each such case is named below with the number it measured. This app is read
by ten-year-olds on classroom projectors, and a label they cannot resolve is not a label.

Checked here as arithmetic over the palette rather than in a browser, so it runs in the
normal suite and fails the build when someone lightens a token. The gradients are checked
at the point where the text actually sits, because a flap that starts at 4.9:1 and ends at
3.8:1 puts its TRAP line on the wrong end.
"""

from __future__ import annotations

import pytest

from prove_it.ui.style import PALETTE

# Text smaller than 18.66px bold / 24px regular needs 4.5:1. Larger text needs 3:1.
BODY = 4.5
LARGE = 3.0


def _luminance(colour: str) -> float:
    value = colour.lstrip("#")
    channels = []
    for at in (0, 2, 4):
        raw = int(value[at : at + 2], 16) / 255
        channels.append(raw / 12.92 if raw <= 0.03928 else ((raw + 0.055) / 1.055) ** 2.4)
    red, green, blue = channels
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(foreground: str, background: str) -> float:
    first, second = _luminance(foreground), _luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def mix(start: str, end: str, at: float) -> str:
    """The colour a two-stop gradient reaches at `at` (0..1) — where a label sits."""
    a, b = start.lstrip("#"), end.lstrip("#")
    channels = (
        round(int(a[i : i + 2], 16) * (1 - at) + int(b[i : i + 2], 16) * at) for i in (0, 2, 4)
    )
    return "#" + "".join(f"{channel:02X}" for channel in channels)


P = PALETTE
# The wager panel is a 55% wash over the desk.
PANEL = mix(P["desk-mid"], "#14100A", 0.55)

PAIRS = [
    # -- the archive: text on the room -------------------------------------------------
    ("the hero's rule line on the room", P["ash"], P["room"], BODY),
    ("the hero's subtitle on the wall", P["mist"], P["wall-mid"], BODY),
    ("the nameplate's gold on the room", P["gold"], P["room"], BODY),
    ("the standing facts on the desk", P["ash"], P["desk-deep"], BODY),
    # -- the folders: the design's flaps, with ink measured where the labels sit -------
    # The design's #4A3A1E measured 3.79:1 at the TRAP line; the ink is darker here.
    ("folder label, mid-flap", P["kraft-ink"], mix(P["folder"], P["folder-deep"], 0.45), BODY),
    ("folder title, mid-flap", P["ink-brown"], mix(P["folder"], P["folder-deep"], 0.45), LARGE),
    (
        "up-next label, mid-flap",
        P["kraft-ink"],
        mix(P["folder-next"], P["folder-next-deep"], 0.45),
        BODY,
    ),
    # The design's #3A3018 measured 3.26:1 on the darker folder; the ink is darker here.
    (
        "own-folder label, mid-flap",
        P["folder-own-label"],
        mix(P["folder-own"], P["folder-own-deep"], 0.45),
        BODY,
    ),
    (
        "own-folder title",
        P["folder-own-ink"],
        mix(P["folder-own"], P["folder-own-deep"], 0.45),
        LARGE,
    ),
    ("the claim on the sheet inside", P["ink-type"], P["cream"], BODY),
    ("the source tag on the sheet inside", P["pencil-warm"], P["cream"], BODY),
    ("the UP NEXT badge", P["bone"], P["red"], BODY),
    # -- the board: every word is on a document ---------------------------------------
    ("the clipping's label", P["pencil-warm"], P["clipping"], BODY),
    ("the claim on the clipping", P["ink-warm"], P["clipping"], BODY),
    ("the reasoning card's label", P["navy"], P["paper"], BODY),
    ("the reasoning on its card", P["ink-brown"], P["paper"], BODY),
    ("the warrant's label", P["pencil-warm"], P["cream"], BODY),
    ("the query on the warrant", P["ink-warm"], P["cream"], BODY),
    ("a keyword on the warrant", P["red-sql"], P["cream"], BODY),
    ("an added column on the second warrant", P["green-deep"], P["green-mark"], BODY),
    # The design's #4A3A1E measured 4.17:1 on the lower half of the bag.
    ("the bag's label, lower half", P["kraft-ink"], mix(P["kraft"], P["kraft-mid"], 0.6), BODY),
    ("the band on the bag", P["wax-ink"], P["red"], BODY),
    ("the tag card on the bag", P["slate"], P["paper"], BODY),
    ("the strip's label", P["pencil-strip"], P["paper"], BODY),
    ("the rows on the strip", P["ink-warm"], P["paper"], BODY),
    ("the strip's table head", P["pencil-strip"], P["table-head"], BODY),
    ("the same-conversation tag", P["red"], P["paper"], BODY),
    ("the custody tag", P["kraft-ink-soft"], P["tag"], BODY),
    ("a hand-written note on cream", P["red-hand"], P["cream"], BODY),
    # -- the desk -----------------------------------------------------------------------
    ("the slate's label", P["kraft-ink-soft"], P["kraft"], BODY),
    ("the slate's title", P["ink-warm"], P["kraft"], BODY),
    ("the wager's question on the panel", P["mist"], PANEL, BODY),
    ("the wager's title on the panel", P["gold-pale"], PANEL, BODY),
    ("the stake's note on the panel", P["ash"], PANEL, BODY),
    ("a coin's face", P["gold-pale"], PANEL, BODY),
    ("the certain coin's face", P["certain-ink"], PANEL, BODY),
    ("a slip", P["ink-warm"], P["cream"], BODY),
    ("the seal's text on the wax", P["wax-ink"], P["wax"], BODY),
    ("the seal's hint", P["mist"], PANEL, BODY),
    ("a chit", P["chit-ink"], P["chit"], BODY),
    ("the review's question", P["bone"], PANEL, BODY),
    ("the review's text", P["mist"], PANEL, BODY),
    # The button is a red-lit → wax gradient; its label sits across the middle of it.
    ("the cross-examine button", P["wax-ink"], mix(P["red-lit"], P["wax"], 0.5), BODY),
    ("the close-the-case button", P["chrome"], P["gold"], BODY),
    # -- the kit -------------------------------------------------------------------------
    ("the card's head", P["bone"], P["chrome"], BODY),
    ("the card's lesson", P["slate"], P["paper"], BODY),
    ("the card's wild line", P["pencil-strip"], P["paper"], BODY),
    ("a kit slot", P["ash"], P["room"], BODY),
    ("the share card's footer", P["kraft-ink"], P["cream"], BODY),
    # -- the receipt --------------------------------------------------------------------
    ("the receipt's rows", P["ink-warm"], P["cream"], BODY),
    ("the receipt's values", P["pencil-warm"], P["cream"], BODY),
    ("verdict: looks true", P["holds"], P["paper"], BODY),
    ("verdict: busted", P["busted"], P["paper"], BODY),
    ("verdict: half true", P["accent"], P["paper"], BODY),
    ("verdict: can't tell", P["nodata"], P["paper"], BODY),
]


@pytest.mark.parametrize("what,foreground,background,floor", PAIRS, ids=lambda v: str(v)[:34])
def test_text_clears_the_wcag_aa_floor(
    what: str, foreground: str, background: str, floor: float
) -> None:
    ratio = contrast(foreground, background)
    assert ratio >= floor, (
        f"{what}: {foreground} on {background} is {ratio:.2f}:1, below the {floor}:1 floor. "
        f"This app is read by ten-year-olds on classroom projectors — darken the ink "
        f"rather than lowering the bar, and leave the design's surface alone."
    )


def test_the_ratio_maths_is_right() -> None:
    """Guards the guard: a broken formula would pass every pair above silently."""
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert contrast("#FFFFFF", "#FFFFFF") == pytest.approx(1.0, abs=0.01)
    assert contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.05)
    assert mix("#000000", "#FFFFFF", 0.5) == "#808080"
