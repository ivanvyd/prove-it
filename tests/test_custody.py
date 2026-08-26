"""Provenance read off Genie's own identifiers.

The point of this module is that the app's honesty claim becomes checkable against a record
the app does not own. These tests hold the two properties that makes true: the ids are the
real ones, unmodified; and continuity is reported only when it genuinely exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from prove_it.domain.custody import (
    DISTINGUISHING_LENGTH,
    custody_of,
    evidence_tag,
    same_conversation,
)
from prove_it.genie.fake import demo_client
from prove_it.genie.models import Turn

ROOT = Path(__file__).resolve().parents[1]


def _turn(conversation: str = "c" * 32, message: str = "m" * 32, attachment: str | None = "a" * 32):
    return Turn(
        conversation_id=conversation,
        message_id=message,
        question="q",
        attachment_id=attachment,
        sql="SELECT 1",
    )


# -- the identifiers are Genie's, not ours -------------------------------------------


def test_custody_reports_the_ids_verbatim() -> None:
    """Any transformation here would break the one thing the panel is for: a judge
    comparing what is on screen against the Genie space's own conversation list."""
    turn = _turn(conversation="01f19cef42f8", message="01f19cef4300", attachment="01f19cef44ae")
    c = custody_of(turn)
    assert c is not None
    assert c.conversation_id == "01f19cef42f8"
    assert c.message_id == "01f19cef4300"
    assert c.attachment_id == "01f19cef44ae"


def test_the_evidence_tag_comes_off_the_tail_not_the_head() -> None:
    """Genie ids are time-ordered. The head is a shared timestamp prefix and carries no
    information; two different attachments would produce the same tag."""
    tag = evidence_tag(_turn(attachment="01f19cef44ae12ce9ecbfa228aea3fa6"))
    assert tag == "aea3fa6"
    assert tag is not None
    assert "01f19cef".find(tag) == -1


def test_two_different_attachments_get_different_tags() -> None:
    first = evidence_tag(_turn(attachment="01f19cef44ae12ce9ecbfa228aea3fa6"))
    second = evidence_tag(_turn(attachment="01f19cef4cf31ce8baf2a3660dd8367c"))
    assert first != second


def test_a_head_truncation_would_have_collided() -> None:
    """The regression this constant exists to prevent, stated as a test rather than a
    comment: an eight-character head would make two distinct ids identical on screen."""
    a = "01f19cef44ae12ce9ecbfa228aea3fa6"
    b = "01f19cef4cf31ce8baf2a3660dd8367c"
    assert a[:8] == b[:8], "if this ever stops being true the constant can be revisited"
    assert a[-7:] != b[-7:]


def test_the_distinguishing_length_actually_distinguishes_real_ids() -> None:
    conversation = "01f19cef42f81e17996b65ef60c957d0"
    message = "01f19cef4300183693efedf4ac9c2ebc"
    assert conversation[:DISTINGUISHING_LENGTH] != message[:DISTINGUISHING_LENGTH]


# -- continuity is only claimed when it is real --------------------------------------


def test_the_same_conversation_is_recognised() -> None:
    shared = "01f19cef42f81e17996b65ef60c957d0"
    assert same_conversation(
        _turn(conversation=shared, message="m1"),
        _turn(conversation=shared, message="m2"),
    )


def test_a_new_conversation_is_not_reported_as_continuity() -> None:
    assert not same_conversation(_turn(conversation="one"), _turn(conversation="two"))


@pytest.mark.parametrize(
    ("first", "second"),
    [(None, _turn()), (_turn(), None), (None, None)],
)
def test_a_missing_turn_never_claims_continuity(first: Turn | None, second: Turn | None) -> None:
    """A refused or unasked follow-up continued nothing. Claiming otherwise would put a
    false provenance statement on screen, which is worse than an absent one."""
    assert not same_conversation(first, second)


def test_a_turn_without_ids_has_no_custody() -> None:
    assert custody_of(None) is None
    assert custody_of(Turn(conversation_id="", message_id="", question="q")) is None


def test_a_turn_with_no_attachment_still_has_custody_but_no_tag() -> None:
    """Genie answered without writing a query — there is a message to point at, but
    nothing was sealed, so there is no evidence tag."""
    refused = _turn(attachment=None)
    assert custody_of(refused) is not None
    assert evidence_tag(refused) is None


# -- against the real recording ------------------------------------------------------


def test_the_recorded_demo_really_is_one_conversation() -> None:
    """The claim the whole custody panel rests on, checked against the actual probe run
    rather than a hand-made fixture: the retrial continued Genie's conversation."""
    client = demo_client()
    first = client.ask("boys are better at maths")
    second = client.follow_up(first, "show the spread too")

    assert same_conversation(first, second)
    assert first.message_id != second.message_id, "two turns, not one replayed twice"


@pytest.mark.skipif(
    not (ROOT / "probe-runs" / "demo-investigation.json").exists(),
    reason="the recorded probe run is gitignored; present only on a machine that ran it",
)
def test_the_recording_on_disk_agrees() -> None:
    raw = json.loads((ROOT / "probe-runs" / "demo-investigation.json").read_text(encoding="utf-8"))
    ids = _conversation_ids(raw)
    assert len(ids) >= 2, "expected at least two turns in the recording"
    assert len(set(ids)) == 1, f"the recording spans more than one conversation: {set(ids)}"


def _conversation_ids(node: object) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "conversation_id" and isinstance(value, str):
                found.append(value)
            else:
                found += _conversation_ids(value)
    elif isinstance(node, list):
        for item in node:
            found += _conversation_ids(item)
    return found
