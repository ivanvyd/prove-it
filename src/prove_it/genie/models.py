"""What the app keeps from a Genie turn.

These are deliberately not the SDK's types. The app shows a child the SQL Genie wrote and
the steps it took, and it must keep working when a field the SDK declares as optional
comes back empty — which on Free Edition is a live possibility rather than a hypothetical.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Order matters: this is the order the reasoning is shown in, and it follows the order a
# person would reconstruct the query in — what was asked, what it means, where to look,
# what rules applied, what to compute.
THOUGHT_ORDER = (
    "DESCRIPTION",
    "UNDERSTANDING",
    "DATA_SOURCING",
    "INSTRUCTIONS",
    "STEPS",
)

THOUGHT_LABELS = {
    "DESCRIPTION": "What it understood",
    "UNDERSTANDING": "How it read the question",
    "DATA_SOURCING": "Where it looked",
    "INSTRUCTIONS": "Rules it followed",
    "STEPS": "What it worked out",
}


@dataclass(frozen=True)
class ThoughtStep:
    """One typed step from Genie's reasoning trace."""

    kind: str
    content: str

    @property
    def label(self) -> str:
        return THOUGHT_LABELS.get(self.kind, self.kind.replace("_", " ").capitalize())


@dataclass(frozen=True)
class Turn:
    """One question and Genie's answer to it, with the result rows deliberately absent.

    `attachment_id` is the handle the app needs to fetch rows later. Holding the handle
    without using it is the whole product: the SQL goes on screen immediately, the
    numbers stay sealed until the child has committed to a prediction.
    """

    conversation_id: str
    message_id: str
    question: str
    status: str = "COMPLETED"
    attachment_id: str | None = None
    sql: str | None = None
    description: str | None = None
    text: str | None = None
    thoughts: list[ThoughtStep] = field(default_factory=list)
    # What Genie was doing while the app waited: (status, seconds since the question was
    # sent), one entry per poll. FETCHING_METADATA, ASKING_AI, EXECUTING_QUERY, COMPLETED.
    # Recorded live so the offline replay can show the same wait at the same pace, and
    # kept on the turn because it is a fact about this answer, not about the client.
    timeline: list[tuple[str, float]] = field(default_factory=list)

    @property
    def has_query(self) -> bool:
        """Did Genie actually write a query we can show and later run?"""
        return bool(self.attachment_id and self.sql)

    @property
    def ordered_thoughts(self) -> list[ThoughtStep]:
        known = {t.kind: t for t in self.thoughts}
        ordered = [known[k] for k in THOUGHT_ORDER if k in known]
        extra = [t for t in self.thoughts if t.kind not in THOUGHT_ORDER]
        return ordered + extra

    @property
    def refusal_text(self) -> str | None:
        """Genie's own words for why it produced no query, if it said anything."""
        if self.has_query:
            return None
        return self.text or self.description
