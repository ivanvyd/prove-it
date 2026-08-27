"""The provenance panel and the evidence tag, as rendered.

These render Genie-supplied identifiers into markup with HTML enabled, so the escaping
matters as much as the layout. They also carry the app's central claim, which means a
wrong or absent string here is a credibility bug rather than a cosmetic one.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from prove_it.genie.models import Turn
from prove_it.ui.render import provenance_panel

APP = str(Path(__file__).resolve().parents[1] / "src" / "prove_it" / "ui" / "app.py")


def _turn(conversation: str = "c" * 32, message: str = "m" * 32, attachment: str | None = "a" * 32):
    return Turn(
        conversation_id=conversation,
        message_id=message,
        question="q",
        attachment_id=attachment,
        sql="SELECT 1",
    )


class _Inv:
    """Just enough of an Investigation for the panel, which reads only two attributes."""

    def __init__(self, first: Turn | None, second: Turn | None) -> None:
        self.first = first
        self.second = second


def test_the_panel_states_the_continuity_when_it_is_real() -> None:
    shared = "01f19cef42f81e17996b65ef60c957d0"
    panel = provenance_panel(
        _Inv(_turn(conversation=shared, message="m1"), _turn(conversation=shared, message="m2"))
    )
    assert "same conversation id" in panel
    assert "not a template run twice" in panel


def test_the_panel_does_not_claim_continuity_across_two_conversations() -> None:
    panel = provenance_panel(_Inv(_turn(conversation="one"), _turn(conversation="two")))
    assert "same conversation id" not in panel
    assert "message history" in panel


def test_the_panel_carries_full_untruncated_ids() -> None:
    """The whole point is that a judge can compare these against Genie's own history."""
    full = "01f19cef42f81e17996b65ef60c957d0"
    panel = provenance_panel(_Inv(_turn(conversation=full), None))
    assert full in panel


def test_the_panel_is_empty_with_nothing_to_show() -> None:
    assert provenance_panel(_Inv(None, None)) == ""


def test_the_panel_handles_a_first_query_alone() -> None:
    """A CANT_TELL run never reaches a second query."""
    panel = provenance_panel(_Inv(_turn(), None))
    assert panel
    assert panel.count("<tr>") == 2, "header row plus exactly one query row"


def test_the_panel_omits_a_refused_follow_up_and_drops_its_continuity_claim() -> None:
    """The refusal shares the first query's conversation id, so the note claimed "both
    queries carry the same conversation id" while the table listed a single row."""
    shared = "01f19cef42f81e17996b65ef60c957d0"
    refused = Turn(
        conversation_id=shared,
        message_id="01f1ffffffffffffffffffffffffffff",
        question="show the spread too",
        text="I cannot rewrite that query.",
    )
    panel = provenance_panel(_Inv(_turn(conversation=shared), refused))

    assert panel.count("<tr>") == 2, "header plus the one query that was actually written"
    assert "same conversation id" not in panel
    assert "01f1ffffffff" not in panel


def test_the_panel_is_empty_when_nothing_was_ever_written() -> None:
    refusal = Turn(conversation_id="c" * 32, message_id="m" * 32, question="q", text="no.")
    assert provenance_panel(_Inv(refusal, None)) == ""


def test_hostile_ids_are_escaped_on_the_panel() -> None:
    hostile = Turn(
        conversation_id="<img src=x>" + "c" * 24,
        message_id="<b>" + "m" * 24,
        question="q",
        attachment_id="a" * 32,
        sql="SELECT 1",
    )
    panel = provenance_panel(_Inv(hostile, None))
    assert panel, "a turn with a query must still render"
    assert "<img src=x>" not in panel
    assert "&lt;img" in panel


# -- end to end ----------------------------------------------------------------------


def _frames(app: AppTest) -> str:
    return "\n".join(
        getattr(getattr(e, "proto", None), "srcdoc", "") for e in (app._tree.get("iframe") or [])
    )


def test_the_sealed_bag_carries_a_real_evidence_tag() -> None:
    """The tag on the bag is Genie's real attachment handle — the thing the app is holding
    and refusing to spend until the child has committed. Printing it makes the seal a
    picture of a fact instead of a decorative padlock."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()
    assert not app.exception

    board = _frames(app)
    assert "do not open" in board
    assert "Result rows inside" in board
    tag = app.session_state["investigation"].first.attachment_id[-7:]
    assert f"TAG <b>{tag}</b>" in board, "the tag on screen must be Genie's real attachment id"


def test_the_warrant_names_genie_as_the_author_with_its_own_ids() -> None:
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()
    inv = app.session_state["investigation"]
    board = _frames(app)
    assert "Written by Genie" in board
    assert inv.first.conversation_id[:12] in board
    assert inv.first.message_id[:12] in board
