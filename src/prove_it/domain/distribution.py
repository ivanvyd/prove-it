"""Reading per-group shape out of the repaired query's rows.

The repaired query returns three numbers per group — how many, the average, and the
spread. That is enough to draw the distribution the averages were hiding, which is the one
thing this app asserts in prose and has never shown.

What it is *not* is the pupils themselves. Genie returned aggregates; getting nine
thousand individual rows would need another query, and the app does not write queries.
So anything drawn from this is a reconstruction from three numbers, and every screen that
uses it has to say so. In an app whose whole argument is "do not take the summary on
faith", quietly presenting invented dots as the class would be the exact sin it teaches
children to catch.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from prove_it.domain.verdict import (
    _COUNT_NAMES,
    _MEAN_NAMES,
    _SPREAD_NAMES,
    ResultTable,
    _to_float,
)


def _label_index(table: ResultTable, measures: set[int]) -> int | None:
    """Which column names the groups.

    Prefers a column of non-numeric values, which is the usual case ("boy"/"girl"). Falls
    back to the first remaining column even when it is numeric, because plenty of real
    groupings are — year_group 7 and 8, exam_year 2019 and 2022 — and labelling those
    "group 1" and "group 2" throws away the only thing that made the chart worth reading.
    """
    remaining = [i for i in range(len(table.columns)) if i not in measures]
    for i in remaining:
        if all(_to_float(row[i]) is None for row in table.rows if i < len(row)):
            return i
    return remaining[0] if remaining else None


@dataclass(frozen=True)
class GroupShape:
    """One group's size, centre and spread, as returned."""

    name: str
    count: int
    mean: float
    spread: float


def group_shapes(table: ResultTable | None) -> list[GroupShape]:
    """Every group the table describes completely enough to draw.

    Returns an empty list unless all three numbers are present for every group — a
    half-described distribution is worse than none, because it would be drawn confidently
    and be wrong.
    """
    if table is None or not table.rows:
        return []

    mean_idx = table.index_of(_MEAN_NAMES)
    spread_idx = table.index_of(_SPREAD_NAMES)
    count_idx = table.index_of(_COUNT_NAMES)
    if mean_idx is None or spread_idx is None or count_idx is None:
        return []

    label_idx = _label_index(table, {mean_idx, spread_idx, count_idx})

    shapes: list[GroupShape] = []
    for position, row in enumerate(table.rows):
        mean = _to_float(row[mean_idx]) if mean_idx < len(row) else None
        spread = _to_float(row[spread_idx]) if spread_idx < len(row) else None
        count = _to_float(row[count_idx]) if count_idx < len(row) else None
        if mean is None or spread is None or count is None:
            return []
        if count < 1 or spread <= 0:
            return []
        name = (
            str(row[label_idx])
            if label_idx is not None and label_idx < len(row)
            else (f"group {position + 1}")
        )
        shapes.append(GroupShape(name=name, count=int(count), mean=mean, spread=spread))
    return shapes


def group_means(table: ResultTable | None) -> list[tuple[str, float]]:
    """Just the label and the average per group.

    Separate from `group_shapes` on purpose: the naive first query returns no spread and
    no count, so it can never produce a `GroupShape`, and inventing one with zeroes to get
    a chart drawn would be exactly the kind of quiet fabrication this app argues against.
    """
    if table is None or not table.rows:
        return []

    mean_idx = table.index_of(_MEAN_NAMES)
    if mean_idx is None:
        return []

    label_idx = next(
        (
            i
            for i in range(len(table.columns))
            if i != mean_idx and all(_to_float(row[i]) is None for row in table.rows)
        ),
        None,
    )

    out: list[tuple[str, float]] = []
    for position, row in enumerate(table.rows):
        mean = _to_float(row[mean_idx]) if mean_idx < len(row) else None
        if mean is None:
            return []
        name = (
            str(row[label_idx])
            if label_idx is not None and label_idx < len(row)
            else (f"group {position + 1}")
        )
        out.append((name, mean))
    return out


def overlap_fraction(shapes: list[GroupShape]) -> float | None:
    """How much of the two groups sit on top of each other.

    The overlapping coefficient: the area under the lower of the two density curves. It is
    integrated numerically rather than taken from the textbook 2·Φ(−|Δ|/2σ) shortcut,
    because that shortcut assumes the two spreads are equal and goes badly wrong when they
    are not — two groups sharing a mean with spreads of 10 and 40 genuinely overlap about
    42%, and the shortcut reports 100%.

    That matters more here than the arithmetic suggests: this number is shown to a child as
    "about X% of the two groups sit on top of each other". A confidently wrong statistic is
    exactly what the app exists to teach them to catch.
    """
    if len(shapes) != 2:
        return None
    a, b = shapes
    if a.spread <= 0 or b.spread <= 0:
        return None

    lo = min(a.mean - 6 * a.spread, b.mean - 6 * b.spread)
    hi = max(a.mean + 6 * a.spread, b.mean + 6 * b.spread)
    steps = 2000
    width = (hi - lo) / steps

    total = 0.0
    for i in range(steps + 1):
        x = lo + i * width
        density = min(_normal_pdf(x, a.mean, a.spread), _normal_pdf(x, b.mean, b.spread))
        # Trapezoid: the ends count half.
        total += density * (0.5 if i in (0, steps) else 1.0)
    return min(1.0, total * width)


def _normal_pdf(x: float, mean: float, spread: float) -> float:
    z = (x - mean) / spread
    return math.exp(-0.5 * z * z) / (spread * math.sqrt(2 * math.pi))
