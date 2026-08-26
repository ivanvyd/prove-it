"""Line-level diff between the two queries Genie wrote.

The diff is the screenshot the whole project is built around, so it is computed here and
tested, rather than improvised in the view. Both inputs are Genie's own SQL, unmodified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import Enum


class Change(Enum):
    SAME = "same"
    ADDED = "added"
    REMOVED = "removed"


@dataclass(frozen=True)
class DiffLine:
    change: Change
    text: str


# Split into words, punctuation and runs of whitespace, keeping every character so the
# pieces can be reassembled into the original string exactly.
_TOKENS = re.compile(r"\s+|\w+|[^\w\s]")


def diff_tokens(before: str | None, after: str | None) -> list[DiffLine]:
    """Diff two queries at token level, returning contiguous same/added/removed runs.

    Line-level diffing was written against a hand-formatted example and does not survive
    real Genie output: Genie emits a query as one long line, so a line diff reports the
    entire statement as removed and re-added, and the two highlighted columns that are the
    whole point of the screen never appear.

    Token level works for both shapes, and it keeps the text verbatim — the segments
    concatenate back to exactly what Genie wrote.
    """
    old = _TOKENS.findall(before or "")
    new = _TOKENS.findall(after or "")
    matcher = SequenceMatcher(None, old, new, autojunk=False)

    segments: list[DiffLine] = []

    def push(change: Change, text: str) -> None:
        if not text:
            return
        if segments and segments[-1].change is change:
            segments[-1] = DiffLine(change, segments[-1].text + text)
        else:
            segments.append(DiffLine(change, text))

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            push(Change.SAME, "".join(new[j1:j2]))
        elif tag == "insert":
            push(Change.ADDED, "".join(new[j1:j2]))
        elif tag == "delete":
            push(Change.REMOVED, "".join(old[i1:i2]))
        elif tag == "replace":
            push(Change.REMOVED, "".join(old[i1:i2]))
            push(Change.ADDED, "".join(new[j1:j2]))
    return segments


def _key(line: str) -> str:
    """What counts as "the same line" for matching purposes.

    A trailing comma is punctuation, not meaning: adding a column to a SELECT list puts a
    comma on the line above it, and without this the diff would report that line as
    deleted and re-added. A child reading the diff should see only the columns that
    actually appeared.
    """
    return line.strip().rstrip(",")


def diff_sql(before: str | None, after: str | None) -> list[DiffLine]:
    """Compare two queries line by line.

    Whitespace is normalised on the right of each line only — Genie's indentation is
    part of what the child is reading, so it is preserved.
    """
    old = (before or "").splitlines()
    new = (after or "").splitlines()
    matcher = SequenceMatcher(None, [_key(line) for line in old], [_key(line) for line in new])

    lines: list[DiffLine] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            lines.extend(DiffLine(Change.SAME, line.rstrip()) for line in new[j1:j2])
        elif tag == "insert":
            lines.extend(DiffLine(Change.ADDED, line.rstrip()) for line in new[j1:j2])
        elif tag == "delete":
            lines.extend(DiffLine(Change.REMOVED, line.rstrip()) for line in old[i1:i2])
        elif tag == "replace":
            lines.extend(DiffLine(Change.REMOVED, line.rstrip()) for line in old[i1:i2])
            lines.extend(DiffLine(Change.ADDED, line.rstrip()) for line in new[j1:j2])
    return lines


def added_count(lines: list[DiffLine]) -> int:
    return sum(1 for line in lines if line.change is Change.ADDED)
