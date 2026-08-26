"""Turning a typed claim into questions for Genie.

Nothing here composes SQL. Every string that reaches Genie is a question in English,
because the moment the app writes SQL itself the Genie Agent stops being the engine.

The call a player makes on a claim lives in `domain/game.py`; this module only shapes
what Genie is asked.
"""

from __future__ import annotations

MAX_CLAIM_LENGTH = 200


class ClaimError(ValueError):
    """The claim cannot be sent to Genie as written."""


# The claim is interpolated into a double-quoted span of the question sent to Genie, so a
# double quote in the text would close that span early and let the rest read as fresh
# instructions. Folding them to single quotes keeps the child's words intact and keeps the
# boundary between "the claim" and "the instructions" where it belongs.
_QUOTE_CHARS = str.maketrans({'"': "'", "“": "'", "”": "'"})


def clean_claim(raw: str) -> str:
    """Normalise what the child typed, or say why it cannot be used."""
    claim = " ".join(raw.split()).translate(_QUOTE_CHARS)
    if not claim:
        raise ClaimError("Type something you have heard, and we will go and check it.")
    if len(claim) > MAX_CLAIM_LENGTH:
        raise ClaimError(
            f"That is a bit long to check in one go — keep it under {MAX_CLAIM_LENGTH} characters."
        )
    return claim


def opening_question(claim: str) -> str:
    """The first thing Genie is asked.

    Phrased as "test this claim", never "is this true" — the app wants a query it can
    show, and it wants Genie's honest first attempt rather than a hedged essay.
    """
    return (
        f'Someone claims: "{claim}". '
        "Compare the groups this claim is about using the data, and show the average for each "
        "group."
    )


def repair_question() -> str:
    """The follow-up that turns the naive comparison into a fair one.

    The child triggers this; the wording stays fixed so the lesson is reproducible and so
    the SQL diff between the two turns is legible to a beginner.
    """
    return (
        "Now show how spread out the individual values are within each group, and how many "
        "records are in each group, as well as the averages."
    )
