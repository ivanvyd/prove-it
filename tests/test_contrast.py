"""Every colour pair the app paints text in, against the WCAG 2.2 AA floor.

Eight of these were below the floor when this suite was written, and every one was found by
measuring a running browser rather than by looking: the "offline demo" caption at 2.97:1,
the sealed bag's own labels at 3.32:1, Streamlit's stock info box at 2.05:1 — that last one
on the single sentence the whole product exists to deliver.

Checked here as arithmetic over the palette rather than in a browser, so it runs in the
normal suite and fails the build when someone lightens a token. The browser sweep is what
found the pairs; this is what keeps them.
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


# (what it is, foreground, background, floor). Foregrounds written as literals where the
# rule uses a literal, so this fails if either the rule or the palette drifts.
PAIRS = [
    ("body text on the sheet", PALETTE["ink"], PALETTE["sheet"], BODY),
    ("body text on paper", PALETTE["ink"], PALETTE["paper"], BODY),
    ("body text on manila", PALETTE["ink"], PALETTE["manila"], BODY),
    ("pencil prose on the sheet", PALETTE["pencil"], PALETTE["sheet"], BODY),
    ("pencil prose on paper", PALETTE["pencil"], PALETTE["paper"], BODY),
    # The line telling a visitor the demo is a recording. Was #8A8E80 at 2.97:1.
    ("the offline caption", PALETTE["faint"], PALETTE["sheet"], BODY),
    ("case eyebrow on its folder tab", "#6B5D3F", PALETTE["manila-tab"], BODY),
    ("case source line on manila", "#6E6042", PALETTE["manila"], BODY),
    ("section label on the sheet", "#64685C", PALETTE["sheet"], BODY),
    ("section label on manila", "#64685C", PALETTE["manila"], BODY),
    # The sealed evidence bag. All three were 3.32:1 on kraft.
    ("the seal's own labels", "#5A4C2E", PALETTE["kraft"], BODY),
    ("the wager written on the bag", "#5A4C2E", PALETTE["kraft"], BODY),
    ("the redacted digits", "#7E6430", PALETTE["kraft"], LARGE),
    # Where a trick shows up in the wild: the sentence a child is meant to leave with.
    ("the antibody card's wild line", "#845F1E", PALETTE["manila"], BODY),
    ("the masthead wordmark", PALETTE["bone"], PALETTE["chrome"], BODY),
    ("the masthead's gold", PALETTE["gold"], PALETTE["chrome"], BODY),
    ("verdict: looks true", PALETTE["holds"], PALETTE["holds-soft"], BODY),
    ("verdict: busted", PALETTE["busted"], PALETTE["busted-soft"], BODY),
    ("verdict: half true", PALETTE["accent"], PALETTE["accent-soft"], BODY),
    ("verdict: can't tell", PALETTE["nodata"], PALETTE["nodata-soft"], BODY),
    # Streamlit's info box, repainted. Its stock blue on blue measured 2.05:1.
    ("the repainted info box", PALETTE["ink"], PALETTE["accent-soft"], BODY),
    # The Evidence Room. The page is a dark room now, so every word that sits on the room
    # rather than on a document is a pair that did not exist before.
    ("heading on the room", PALETTE["bone"], PALETTE["room"], LARGE),
    ("body text on the room", PALETTE["bone"], PALETTE["room"], BODY),
    ("caption on the room", PALETTE["ash"], PALETTE["room"], BODY),
    ("gold label on the room", PALETTE["gold"], PALETTE["room"], BODY),
    ("body text on the room's lift", PALETTE["bone"], PALETTE["room-lift"], BODY),
    ("caption on the room's lift", PALETTE["ash"], PALETTE["room-lift"], BODY),
    # The folder flap, both ends of its gradient. The design's own values sat at 4.23:1 and
    # 3.34:1 here; the flap was lifted 15% rather than the ink darkened, which would have
    # collapsed the two ink weights onto one value.
    ("folder label on the flap", PALETTE["folder-ink-soft"], PALETTE["folder"], BODY),
    (
        "folder label on the flap's deep end",
        PALETTE["folder-ink-soft"],
        PALETTE["folder-deep"],
        BODY,
    ),
    ("folder title on the flap", PALETTE["folder-ink"], PALETTE["folder"], LARGE),
    ("folder title on the flap's deep end", PALETTE["folder-ink"], PALETTE["folder-deep"], LARGE),
    ("the open control's label", PALETTE["folder-ink"], PALETTE["folder-deep"], BODY),
    # The sheet inside the folder, which is what opening it reveals.
    ("the claim on the folder's sheet", PALETTE["ink"], PALETTE["paper"], BODY),
    ("the source line on that sheet", PALETTE["folder-sheet-ink"], PALETTE["paper"], BODY),
    # Scene two, the corkboard. Only ink clears the floor on cork — the room's own gold
    # measures 1.5:1 and the app's prose colour 2.04:1 — which is why everything that used to
    # float on the board is either in ink now or pinned to a card.
    ("the claim on the board", PALETTE["ink"], PALETTE["cork"], LARGE),
    ("a label on the board", PALETTE["ink"], PALETTE["cork"], BODY),
    ("the header on the board", PALETTE["ink"], PALETTE["cork"], BODY),
    ("the board at its darkest end", PALETTE["ink"], PALETTE["cork-deep"], BODY),
    # And what is pinned to it stays on paper, where it was already measured.
    ("Genie's reasoning, on its card", PALETTE["ink"], PALETTE["paper"], BODY),
]


@pytest.mark.parametrize("what,foreground,background,floor", PAIRS, ids=lambda v: str(v)[:34])
def test_text_clears_the_wcag_aa_floor(
    what: str, foreground: str, background: str, floor: float
) -> None:
    ratio = contrast(foreground, background)
    assert ratio >= floor, (
        f"{what}: {foreground} on {background} is {ratio:.2f}:1, below the {floor}:1 floor. "
        f"This app is read by ten-year-olds on classroom projectors — darken the foreground "
        f"rather than lowering the bar."
    )


def test_the_ratio_maths_is_right() -> None:
    """Guards the guard: a broken formula would pass every pair above silently."""
    assert contrast("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert contrast("#FFFFFF", "#FFFFFF") == pytest.approx(1.0, abs=0.01)
    assert contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.05)
