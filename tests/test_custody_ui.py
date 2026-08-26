"""The seal and the provenance panel, as rendered.

These render Genie-supplied identifiers into markdown blocks with HTML enabled, so the
escaping matters as much as the layout. They also carry the app's central claim, which
means a wrong or absent string here is a credibility bug rather than a cosmetic one.
"""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from prove_it.genie.models import Turn
from prove_it.ui.render import custody_line, provenance_panel, seal_panel

APP = str(Path(__file__).resolve().parents[1] / "src" / "prove_it" / "ui" / "app.py")


def _turn(conversation: str = "c" * 32, message: str = "m" * 32, attachment: str | None = "a" * 32):
    return Turn(
        conversation_id=conversation,
        message_id=message,
        question="q",
        attachment_id=attachment,
        sql="SELECT 1",
    )


# -- the seal ------------------------------------------------------------------------


def test_the_two_seal_states_differ_only_by_the_lock() -> None:
    """The demo cuts between these two stills. A cut reads as an unlock only if nothing
    else moves, so the structure either side must be identical."""
    locked = seal_panel(opened=False, tag="aea3fa6")
    opened = seal_panel(opened=True, tag="aea3fa6")

    for fragment in ('class="blocks"', "aea3fa6", "Evidence tag"):
        assert fragment in locked and fragment in opened

    assert "🔒" in locked and "Result sealed" in locked
    assert "🔓" in opened and "Seal broken" in opened
    assert "pi-seal--open" in opened
    assert "pi-seal--open" not in locked


def test_the_seal_shows_blocked_out_digits_not_an_empty_space() -> None:
    """The result must read as withheld rather than as not-yet-arrived."""
    assert "▚▚▚.▚" in seal_panel(opened=False, tag="abc1234")


def test_the_seal_survives_a_missing_attachment_id() -> None:
    """Genie answered without writing a query: there is nothing sealed, so no tag."""
    html_out = seal_panel(opened=False, tag=None)
    assert "Evidence tag" not in html_out
    assert "Result sealed" in html_out


def test_the_locked_seal_has_no_prompt_unless_given_one() -> None:
    assert '<div class="q">' not in seal_panel(opened=False, tag="abc1234")
    assert "what would it show" in seal_panel(
        opened=False, tag="abc1234", question="what would it show"
    )


def test_an_opened_seal_does_not_claim_to_still_be_hiding_the_number() -> None:
    """The rows render directly beneath it. Blocked-out digits under "Seal broken" read as
    though the result were still withheld, which is the opposite of what just happened."""
    opened = seal_panel(opened=True, tag="abc1234")
    assert "The result is below." in opened
    # The digits stay for geometry — the strike-through in .pi-seal--open is what retires
    # them — so the class, not their absence, is what carries the meaning.
    assert "pi-seal--open" in opened


def test_a_hostile_tag_is_escaped() -> None:
    assert "<script>" not in seal_panel(opened=False, tag="<script>x</script>")
    assert "&lt;script&gt;" in seal_panel(opened=False, tag="<script>x</script>")


# -- the custody line ----------------------------------------------------------------


def test_the_custody_line_names_genie_as_the_author() -> None:
    line = custody_line(_turn())
    assert "written by Genie" in line
    assert "conversation" in line and "message" in line


def test_the_continuation_marker_only_appears_when_asked_for() -> None:
    assert "same conversation as query v1" in custody_line(_turn(), continues=True)
    assert "same conversation" not in custody_line(_turn(), continues=False)


def test_the_custody_line_is_empty_without_a_turn() -> None:
    """Renders nothing rather than an empty styled block, so a refusal screen stays clean."""
    assert custody_line(None) == ""
    assert custody_line(Turn(conversation_id="", message_id="", question="q")) == ""


def test_a_refused_turn_is_not_credited_with_writing_a_query() -> None:
    """Found by driving a refused repair, not by reading the code.

    A follow-up Genie declines still reaches Stage.REPAIRED and still shares the first
    query's conversation id, so the retrial screen rendered "same conversation as query
    v1 · written by Genie" underneath a turn that produced no SQL whatsoever. That is a
    false authorship claim on the one screen whose entire purpose is verifiable
    authorship.
    """
    refused = Turn(
        conversation_id="01f19cef42f81e17996b65ef60c957d0",
        message_id="01f1ffffffffffffffffffffffffffff",
        question="show the spread too",
        text="I cannot rewrite that query.",
    )
    assert not refused.has_query
    assert custody_line(refused) == ""
    assert custody_line(refused, continues=True) == ""


def test_a_turn_with_an_attachment_but_no_sql_is_also_refused() -> None:
    """`has_query` needs both. Half a query is not a query."""
    half = Turn(conversation_id="c" * 32, message_id="m" * 32, question="q", attachment_id="a" * 32)
    assert custody_line(half) == ""


def test_ids_are_truncated_far_enough_to_stay_distinct() -> None:
    line = custody_line(
        Turn(
            conversation_id="01f19cef42f81e17996b65ef60c957d0",
            message_id="01f19cef4300183693efedf4ac9c2ebc",
            question="q",
            attachment_id="01f19cef44ae12ce9ecbfa228aea3fa6",
            sql="SELECT 1",
        )
    )
    assert "01f19cef42f8" in line
    assert "01f19cef4300" in line, "an 8-char truncation would have collapsed these to one"


def test_hostile_ids_are_escaped() -> None:
    hostile = Turn(
        conversation_id="<img src=x>" + "c" * 24,
        message_id="<b>" + "m" * 24,
        question="q",
        attachment_id="a" * 32,
        sql="SELECT 1",
    )
    line = custody_line(hostile)
    assert line, "a turn with a query must still render"
    assert "<img src=x>" not in line
    assert "&lt;img" in line


# -- the provenance panel ------------------------------------------------------------


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
    """The other half of the refused-repair defect.

    The refusal shares the first query's conversation id, so the note claimed "both
    queries carry the same conversation id" while the table listed a single row.
    """
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


# -- end to end ----------------------------------------------------------------------


def test_the_sealed_screen_carries_a_real_evidence_tag() -> None:
    app = AppTest.from_file(APP, default_timeout=30).run()
    card = next(b for b in app.button if "the average" in str(b.label).lower())
    app = card.click().run()
    assert not app.exception

    rendered = "\n".join(str(m.value) for m in app.markdown)
    assert "Evidence tag" in rendered
    assert "Result sealed" in rendered

    tag = app.session_state["investigation"].first.attachment_id[-7:]
    assert tag in rendered, "the tag on screen must be Genie's real attachment id"


def test_the_retrial_screen_shows_the_shared_conversation() -> None:
    """The strongest claim in the app, checked where a child actually sees it."""
    app = AppTest.from_file(APP, default_timeout=30).run()
    app = next(b for b in app.button if "the average" in str(b.label).lower()).click().run()
    app = next(b for b in app.button if "trick" in str(b.label).lower()).click().run()
    app = next(b for b in app.button if "spread" in str(b.label).lower()).click().run()
    assert not app.exception

    rendered = "\n".join(str(m.value) for m in app.markdown)
    assert "same conversation as query v1" in rendered

    inv = app.session_state["investigation"]
    assert inv.first.conversation_id == inv.second.conversation_id
