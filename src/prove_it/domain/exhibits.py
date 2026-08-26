"""What each column Genie added actually revealed.

The repaired query does not just differ from the first one — it shows something the first
one hid. This turns each added column into a named exhibit with a line of narration read
straight off the returned rows.

Two rules hold this together:

Everything said is quoted from the data. `diff_tokens` already knows which fragments are
new and the result table already holds their values, so nothing here needs inventing. The
moment a line appears that the arithmetic cannot back, the screen becomes theatre — and
theatre is precisely what this app exists to argue against.

And the narration describes what the column *showed*, never that the second query beat the
first. A courtroom has a winner; a child who takes away "newer queries win" has learned the
wrong rule. The second query is fairer, not stronger.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from prove_it.domain.sqldiff import Change, diff_tokens
from prove_it.domain.verdict import (
    Analysis,
    ResultTable,
    _to_float,
    is_count_column,
    is_spread_column,
    subgroup_rates,
)

# `AS <alias>`, which is how every column the app cares about is named — the space
# instructions ask Genie for exactly this and the verdict engine reads the same aliases.
_ALIAS = re.compile(r"\bAS\s+`?([A-Za-z_][A-Za-z0-9_]*)`?", re.I)

# Spread and count detection comes from `verdict.py`, which owns column-name knowledge.
# This module used to carry byte-identical copies of both patterns — and verdict.py's own
# comments record two bugs already fixed in exactly those regexes, either of which a second
# copy would have silently kept.

LABELS = "ABCDEFGH"


@dataclass(frozen=True)
class Exhibit:
    """One column the repaired query added, and what it showed."""

    label: str
    alias: str
    fragment: str
    narration: str


def _column_values(table: ResultTable, alias: str) -> list[str]:
    for i, column in enumerate(table.columns):
        if column.name.lower() == alias.lower():
            return [str(row[i]) for row in table.rows if i < len(row) and row[i] is not None]
    return []


def _pretty(value: str) -> str:
    number = _to_float(value)
    if number is None:
        return value
    if number == int(number):
        return f"{int(number):,}"
    return f"{number:,.1f}"


def _narrate(alias: str, values: list[str], analysis: Analysis) -> str:
    """Say what this column showed, in a sentence a ten-year-old can read."""
    shown = " and ".join(_pretty(v) for v in values)

    if is_spread_column(alias):
        if analysis.pooled_spread and analysis.delta is not None:
            return (
                f"Scores vary by about {analysis.pooled_spread:.0f} inside each group "
                f"({shown}), while the gap between the groups is only "
                f"{abs(analysis.delta):.1f}. Almost everyone is in the same range."
            )
        return f"How much the scores vary inside each group: {shown}."

    if is_count_column(alias):
        return f"How many are in each group: {shown}. Now the averages can be compared fairly."

    return f"Genie also returned {alias}: {shown}."


def weighting_exhibits(table: ResultTable | None) -> list[Exhibit]:
    """Why the total can disagree with every part: who went where.

    `exhibits_for` narrates the columns a repair ADDED, which is the whole story when the
    repair adds a spread or a count. A subgroup breakdown adds no column at all — it adds
    a GROUP BY — so that function finds nothing and the flagship case reached the retrial
    screen with no exhibits on it.

    The missing explanation is the one that makes Simpson's paradox stop being a magic
    trick: the groups did not apply to the same places. Ranking the subgroups by how many
    of ALL applicants they admitted, and then saying who applied to the easiest and who to
    the hardest, is the whole mechanism — and every number in it is read off the rows.
    """
    groups, _ = subgroup_rates(table) if table is not None else ([], (0.0, 0.0))
    if len(groups) < 4:
        # Fewer than four subgroups cannot be split into an easiest and a hardest half
        # without the two overlapping, and a comparison of one against one is noise.
        return []

    left, right = groups[0].left, groups[0].right

    # "Easiest" means most likely to admit anyone at all, both groups pooled — not the
    # rate for either side, which is the thing being explained rather than the yardstick.
    def overall(group) -> float:
        total = group.left_size + group.right_size
        if total <= 0:
            return 0.0
        return (group.left_rate * group.left_size + group.right_rate * group.right_size) / total

    ranked = sorted(groups, key=overall, reverse=True)
    half = len(ranked) // 2
    easiest, hardest = ranked[:half], ranked[half:]

    def split(bucket) -> tuple[int, int, float, float]:
        return (
            int(sum(g.left_size for g in bucket)),
            int(sum(g.right_size for g in bucket)),
            min(overall(g) for g in bucket),
            max(overall(g) for g in bucket),
        )

    easy_left, easy_right, easy_lo, easy_hi = split(easiest)
    hard_left, hard_right, hard_lo, hard_hi = split(hardest)
    if not (easy_left + easy_right) or not (hard_left + hard_right):
        return []

    names = lambda bucket: ", ".join(g.name for g in bucket)  # noqa: E731
    return [
        Exhibit(
            label=LABELS[0],
            alias="who applied where",
            # No fragment. `render_diff` matches this against the added SQL text to
            # place a badge, and a breakdown adds no column to badge — the change is
            # structural. It would also be a SQL literal in application code, which
            # the no-SQL gate correctly refused when this said "GROUP BY".
            fragment="",
            narration=(
                f"The easiest groups to get into ({names(easiest)}, admitting "
                f"{easy_lo:.0f}–{easy_hi:.0f}%) had {easy_left:,} {left} and "
                f"{easy_right:,} {right}."
            ),
        ),
        Exhibit(
            label=LABELS[1],
            alias="and where they did not",
            # No fragment. `render_diff` matches this against the added SQL text to
            # place a badge, and a breakdown adds no column to badge — the change is
            # structural. It would also be a SQL literal in application code, which
            # the no-SQL gate correctly refused when this said "GROUP BY".
            fragment="",
            narration=(
                f"The hardest ({names(hardest)}, admitting {hard_lo:.0f}–{hard_hi:.0f}%) "
                f"had {hard_left:,} {left} and {hard_right:,} {right}. That is the whole "
                f"reason the totals disagree with the groups underneath them."
            ),
        ),
    ]


def exhibits_for(
    before_sql: str | None,
    after_sql: str | None,
    table: ResultTable | None,
    analysis: Analysis,
) -> list[Exhibit]:
    """One exhibit per column the repaired query added and the rows actually carry.

    A column aliased in SQL but missing from the result set is skipped rather than
    narrated, because there is nothing true to say about it.
    """
    if not before_sql or not after_sql or table is None:
        return []

    seen: set[str] = set()
    found: list[Exhibit] = []

    for segment in diff_tokens(before_sql, after_sql):
        if segment.change is not Change.ADDED:
            continue
        for alias in _ALIAS.findall(segment.text):
            key = alias.lower()
            if key in seen:
                continue
            values = _column_values(table, alias)
            if not values:
                continue
            seen.add(key)
            found.append(
                Exhibit(
                    label=LABELS[len(found) % len(LABELS)],
                    alias=alias,
                    fragment=segment.text.strip(" ,"),
                    narration=_narrate(alias, values, analysis),
                )
            )
    return found
