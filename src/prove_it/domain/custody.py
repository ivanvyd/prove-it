"""Where each query on screen came from, in Genie's own identifiers.

The app claims every query was written by Genie. Until now that claim was only ever
asserted — by the README, by a build gate nobody watching the app can see, and by a counter
the app computes about itself. A number an app computes about its own honesty is exactly
the move this product exists to argue against.

These identifiers are different because they are checkable somewhere the app does not
control. `conversation_id` and `message_id` name a real exchange in the Genie space's own
history, so the app's word can be held against Genie's record.

The strongest of them is the one that costs nothing: **both queries carry the same
conversation id**. That is the multi-turn claim made visible. The follow-up did not open a
new conversation and re-ask; it continued the one Genie was already in, which is the reason
Genie is load-bearing here rather than a SQL generator that could be swapped for a template.

Nothing in here is a secret. These are opaque workspace-scoped handles, useless without
authentication to the workspace that issued them, which is why they can go on screen and
into a public write-up.
"""

from __future__ import annotations

from dataclasses import dataclass

from prove_it.genie.models import Turn

# Genie ids are time-ordered, so every id minted in the same span shares a long prefix —
# all three ids in the recorded demo begin `01f19cef`. Truncating to eight characters would
# therefore make two *different* ids look identical, which is worse than not showing them:
# it would quietly disprove the one thing the panel exists to demonstrate.
TAG_LENGTH = 7
DISTINGUISHING_LENGTH = 12


def evidence_tag(turn: Turn | None) -> str | None:
    """A short, human-sayable handle for the sealed result.

    Taken from the tail rather than the head, because the head is the shared timestamp
    prefix and carries no information. This is the child-facing form: it reads as an
    evidence tag on a sealed bag, which is the frame the rest of the app already uses.
    """
    if turn is None or not turn.attachment_id:
        return None
    return turn.attachment_id[-TAG_LENGTH:]


@dataclass(frozen=True)
class Custody:
    """One query's provenance, as Genie recorded it."""

    conversation_id: str
    message_id: str
    attachment_id: str | None

    @property
    def short_conversation(self) -> str:
        return self.conversation_id[:DISTINGUISHING_LENGTH]

    @property
    def short_message(self) -> str:
        return self.message_id[:DISTINGUISHING_LENGTH]


def custody_of(turn: Turn | None) -> Custody | None:
    if turn is None or not turn.conversation_id or not turn.message_id:
        return None
    return Custody(
        conversation_id=turn.conversation_id,
        message_id=turn.message_id,
        attachment_id=turn.attachment_id,
    )


def same_conversation(first: Turn | None, second: Turn | None) -> bool:
    """Did the repaired query continue the first one's conversation?

    False when either turn is missing, which is the honest answer: an unasked follow-up
    did not continue anything, and the panel must not claim continuity it cannot show.
    """
    a, b = custody_of(first), custody_of(second)
    if a is None or b is None:
        return False
    return a.conversation_id == b.conversation_id
