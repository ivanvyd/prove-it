"""Two requirements that shipped without the test their own spec named.

`docs/requirement.md` gives each requirement a "testable as" column. R3 and R11 were built
and then never covered:

- **R3** — "The app renders Genie's `thoughts` as ordered, typed reasoning steps", to be
  tested "over a recorded fixture with >=2 thought types". `render_thoughts` had no test at
  all. It is the entire right-hand column of beat 2 — the thing that makes the sealed screen
  worth looking at rather than just a withheld answer.

- **R11** — "A curated rumour deck is available as a fallback path if free text proves
  unreliable", to be tested as "config flag toggles input mode". `PROVE_IT_FREE_TEXT=0` is
  the documented escape hatch if a live space turns out to mangle typed claims, and nothing
  had ever run it. An untested fallback is not a fallback.
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from prove_it.genie.models import ThoughtStep, Turn
from prove_it.ui.board import thought_cards

APP = str(Path(__file__).resolve().parents[1] / "src" / "prove_it" / "ui" / "app.py")


def all_text(app: AppTest) -> str:
    """Markdown, status widgets and the inline frames — the board is one of the latter."""
    parts: list[str] = []
    for group in (app.markdown, app.caption, app.info, app.success, app.warning):
        parts += [str(element.value) for element in group]
    for element in app._tree.get("iframe") or []:
        srcdoc = getattr(getattr(element, "proto", None), "srcdoc", "")
        if srcdoc:
            parts.append(srcdoc)
    return "\n".join(parts)


# -- R11: the deck-only fallback -----------------------------------------------------


@pytest.fixture
def deck_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVE_IT_FREE_TEXT", "0")


@pytest.fixture
def free_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PROVE_IT_FREE_TEXT", raising=False)


def test_the_flag_off_removes_the_text_box(deck_only: None) -> None:
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not app.exception
    assert len(app.text_input) == 0, (
        "PROVE_IT_FREE_TEXT=0 is the fallback for a space that mishandles typed claims; "
        "leaving the box on screen defeats the point of the flag"
    )


def test_the_flag_off_still_leaves_a_way_in(deck_only: None) -> None:
    """Turning off the only other input would strand the child on beat 1."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    labels = [str(b.label) for b in app.button]
    assert len(labels) >= 4, f"the docket should still be offered; got {labels}"
    assert any("the average" in label.lower() for label in labels)


def test_a_deck_card_drives_the_whole_flow_with_free_text_off(deck_only: None) -> None:
    """The fallback has to reach a verdict, not merely render."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()
    assert not app.exception

    # The design's wager: a slip, a coin, then the seal.
    for label in ("trick", "hunch", "break the seal"):
        button = next((b for b in app.button if label in str(b.label).lower()), None)
        assert button, f"no {label!r} control; buttons: {[b.label for b in app.button]}"
        app = button.click().run()
        assert not app.exception

    # The rows are pinned to the board, which is one inline frame — all_text reaches it.
    text = all_text(app)
    assert "Looks true" in text or "Busted" in text, f"no verdict reached: {text[-400:]}"
    assert "Called:" in text
    assert app.session_state["investigation"].first_result is not None


def test_the_flag_on_restores_the_text_box(free_text: None) -> None:
    """Guards the fixture itself: without it the first test proves nothing. The sheet to
    write on is inside case file Nº 0, so the folder has to be opened first."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    own = next(b for b in app.button if "open case 0" in str(b.label).lower())
    app = own.click().run()
    assert len(app.text_input) == 1


def test_the_flag_off_removes_case_file_zero(deck_only: None) -> None:
    app = AppTest.from_file(APP, default_timeout=30).run()
    assert not any("open case 0" in str(b.label).lower() for b in app.button)


def test_the_flag_defaults_to_on() -> None:
    """Free text is the strongest Genie-centrality argument, so it must be the default."""
    from prove_it.config import Settings

    os.environ.pop("PROVE_IT_FREE_TEXT", None)
    assert Settings.from_env().free_text is True


# -- R3: the reasoning trace ---------------------------------------------------------


def _thoughts_on_screen(app: AppTest) -> list[str]:
    """The reasoning cards live on the board, which is one inline frame."""
    return [
        getattr(getattr(e, "proto", None), "srcdoc", "")
        for e in (app._tree.get("iframe") or [])
        if 'id="er-reason"' in getattr(getattr(e, "proto", None), "srcdoc", "")
    ]


def test_the_reasoning_panel_renders_every_thought_in_order() -> None:
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()
    assert not app.exception

    rendered = "\n".join(_thoughts_on_screen(app))
    assert rendered, "beat 2 rendered no reasoning steps at all"

    steps = app.session_state["investigation"].first.ordered_thoughts
    assert len(steps) >= 2, "the fixture must exercise more than one thought type"
    assert len({s.kind for s in steps}) >= 2, "R3 asks for >=2 distinct thought types"

    # The panel escapes step text before rendering, so compare against the escaped form.
    # This proves nothing is dropped and that the panel follows `ordered_thoughts`; it
    # cannot prove the ordering itself, because the recorded fixture already arrives in
    # THOUGHT_ORDER. The shuffled case below is what actually guards the sort.
    positions = [rendered.index(html.escape(s.content)) for s in steps]
    assert positions == sorted(positions), "the panel did not follow ordered_thoughts"


def test_steps_are_reordered_into_reading_order() -> None:
    """Genie does not promise an order, and the recorded fixture happens to arrive already
    sorted — so the render test above would pass even if the sort were removed."""
    scrambled = _turn(
        thoughts=[
            ThoughtStep(kind="STEPS", content="what to compute"),
            ThoughtStep(kind="DESCRIPTION", content="what was asked"),
            ThoughtStep(kind="DATA_SOURCING", content="where to look"),
            ThoughtStep(kind="UNDERSTANDING", content="what it means"),
        ]
    )
    assert [s.kind for s in scrambled.ordered_thoughts] == [
        "DESCRIPTION",
        "UNDERSTANDING",
        "DATA_SOURCING",
        "STEPS",
    ]


def test_an_unrecognised_kind_sorts_last_rather_than_vanishing() -> None:
    mixed = _turn(
        thoughts=[
            ThoughtStep(kind="MYSTERY", content="new from Genie"),
            ThoughtStep(kind="DESCRIPTION", content="what was asked"),
        ]
    )
    assert [s.kind for s in mixed.ordered_thoughts] == ["DESCRIPTION", "MYSTERY"]


def test_each_step_is_labelled_with_its_type() -> None:
    """ "Typed" is the requirement, not just "listed". An unlabelled run of sentences reads
    as prose and loses the point that this is Genie's own working, step by step."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()

    rendered = "\n".join(_thoughts_on_screen(app))
    for step in app.session_state["investigation"].first.ordered_thoughts:
        assert step.label in rendered, f"the {step.kind} step rendered without its label"


def _turn(
    *,
    sql: str | None = None,
    description: str | None = None,
    thoughts: list[ThoughtStep] | None = None,
) -> Turn:
    """A Turn with the three identity fields filled in, which no test here cares about."""
    return Turn(
        conversation_id="c1",
        message_id="m1",
        question="q",
        sql=sql,
        description=description,
        thoughts=thoughts or [],
    )


def test_no_thoughts_falls_back_to_the_description_rather_than_an_empty_box() -> None:
    """The probe says thoughts come back 14/14 on Free Edition, but that is one space on
    one day. If it ever changes, the column must not become an empty frame."""
    cards = thought_cards(_turn(sql="SELECT 1", description="Compared the two averages."), None)
    assert "Compared the two averages." in cards
    assert "What Genie understood" in cards


def test_neither_thoughts_nor_description_still_renders_a_card() -> None:
    cards = thought_cards(_turn(sql="SELECT 1"), None)
    assert "did not explain" in cards


def test_the_table_is_the_last_card_and_typed() -> None:
    """The design's WHERE IT LOOKED card: the table name, in the typewriter face."""
    cards = thought_cards(_turn(sql="SELECT 1", description="d"), "workspace.prove_it.t")
    assert cards.endswith("workspace.prove_it.t</div></div>")
    assert 'class="b typed"' in cards


def test_a_thought_cannot_inject_markup() -> None:
    """Step text is Genie's, rendered into a document with HTML enabled."""
    hostile = _turn(
        sql="SELECT 1",
        thoughts=[ThoughtStep(kind="STEPS", content="<img src=x onerror=alert(1)>")],
    )
    cards = thought_cards(hostile, None)
    assert "<img" not in cards
    assert "&lt;img" in cards


def test_an_unknown_thought_type_is_still_shown() -> None:
    """THOUGHT_ORDER is a curated list; Genie adding a new kind must not silently drop it."""
    step = ThoughtStep(kind="SOMETHING_NEW", content="a step nobody planned for")
    assert step.label == "Something new"
    assert step in _turn(thoughts=[step]).ordered_thoughts
