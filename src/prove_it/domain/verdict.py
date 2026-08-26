"""Turns a result table Genie returned into one of four verdicts.

The app never writes SQL and never asks a model to judge a claim. Everything here is
arithmetic over the rows Genie's own query produced, so the same input always gives the
same verdict.

The lesson the app teaches lives in the gap between two verdicts on the same claim: a
query answering exactly the question it was asked makes almost any difference look real,
and the same claim judged against a fairer query often does not survive.

Judges dispatch on the SHAPE of what came back — a rate, a series, a subgroup breakdown, a
ranking, a pair of means — never on which case is being played. That is what stops the
docket being a set of scripted demos: a claim someone types themselves reaches the same
judges, and anything none of them can read returns CANT_TELL rather than an error.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import Enum

# A standardised difference below this is treated as negligible. Cohen's convention puts
# 0.2 at the bottom of "small"; below it the groups overlap so heavily that a difference
# in means says nothing useful about any individual.
NEGLIGIBLE_EFFECT = 0.2

_MEAN_NAMES = re.compile(r"avg|mean|average|score$|_score", re.I)
_SPREAD_NAMES = re.compile(r"stddev|std_dev|spread|sd$|deviation|variance", re.I)
# Underscore-delimited, not `\b`. Two bugs have lived here. A bare `n$` matched anything
# ending in the letter n — "correlation", "median" — and a negative value in such a column
# made the weighted variance negative, which `** 0.5` turns into a complex number rather
# than raising. Replacing it with `\b` then went too far the other way: underscore is a
# word character, so `student_count` and `row_count` never hit a boundary at the keyword
# and stopped being recognised as counts at all. Snake_case columns are exactly what Genie
# emits, so the delimiter has to be the underscore itself.
_COUNT_NAMES = re.compile(r"(?:^|_)(count|students|pupils|rows|total|n)(?:_|$)", re.I)

# Added with the case docket. Same underscore-delimited discipline as _COUNT_NAMES, and
# for the same reason: these match Genie's snake_case aliases, and a bare word boundary
# does not fire inside `admit_rate` or `co2_per_capita`.
_RATE_NAMES = re.compile(r"(?:^|_)(rate|share|percent|pct|proportion)(?:_|$)", re.I)
_YEAR_NAMES = re.compile(r"(?:^|_)(year|period)(?:_|$)", re.I)
_PER_UNIT_NAMES = re.compile(r"per_capita|per_person|per_head", re.I)
_TRIED_NAMES = re.compile(r"(?:^|_)(applicants|applied|attempts|entries|eligible)(?:_|$)", re.I)
_SUCCEEDED_NAMES = re.compile(
    r"(?:^|_)(admitted|accepted|passed|selected|successes|survived)(?:_|$)", re.I
)


class ColumnRole(Enum):
    """What a column is *for*, read off its name.

    The judges below already decide this privately, one regex at a time, to work out which
    shape of result they are looking at. Discovery needs the same question answered about a
    table's columns rather than a result's, so the knowledge is named here once instead of
    being copied into a second module that would drift from it.

    Read off the name and the type, never off the values: working out what a column holds
    by looking inside it would mean the app running a query, and the app writes no SQL.
    Unity Catalog hands over names, types and comments for free.
    """

    PER_UNIT = "per_unit"
    RATE = "rate"
    SPREAD = "spread"
    TRIED = "tried"
    SUCCEEDED = "succeeded"
    YEAR = "year"
    COUNT = "count"
    MEASURE = "measure"
    LABEL = "label"
    IDENTIFIER = "identifier"


# Identifiers, in the three shapes real catalogs actually use. The underscore-delimited
# form alone missed `franchiseID`, `customerID` and `transactionID` in Databricks' own
# sample data — camelCase with a trailing ID and no separator anywhere — so every one of
# them was classified as a measure and generated a case about the average of a primary key.
#
# The camelCase arm requires a lowercase letter before the capitalised ID precisely so it
# does not fire on ordinary words that happen to end in those letters: `covid`, `valid`,
# `humid`, `grid` have no case boundary and stay measures or labels as their type decides.
# Compiled WITHOUT IGNORECASE: the camelCase arm depends on the case boundary, so the
# delimited arm spells out both cases itself rather than losing that distinction globally.
_ID_NAMES = re.compile(
    r"(?:^|_)(?i:id|key|uuid|guid)(?:_|$)"  # id, customer_id, _id_
    r"|[a-z](?:ID|Id)$"  # franchiseID, customerId
)

# Numbers that are technically averageable and never worth averaging. A case about the
# mean latitude of a bakery is arithmetic with no subject, the same failure as a case about
# the mean primary key — it just gets there by a different route.
_NOT_A_MEASURE = re.compile(
    r"(?:^|_)(latitude|longitude|lat|lon|lng|zip|zipcode|postcode|phone|year)(?:_|$)", re.I
)

_NUMERIC_TYPES = {"INT", "LONG", "BIGINT", "SMALLINT", "SHORT", "DOUBLE", "FLOAT", "DECIMAL"}

# Most specific first. `co2_per_capita` is a per-unit figure before it is a measure, and
# `admit_rate` is a rate before it is anything else — reversing this order would let the
# generic patterns swallow the columns the specific judges depend on.
_ROLE_ORDER: tuple[tuple[ColumnRole, re.Pattern[str]], ...] = (
    (ColumnRole.PER_UNIT, _PER_UNIT_NAMES),
    (ColumnRole.RATE, _RATE_NAMES),
    (ColumnRole.SPREAD, _SPREAD_NAMES),
    (ColumnRole.TRIED, _TRIED_NAMES),
    (ColumnRole.SUCCEEDED, _SUCCEEDED_NAMES),
    (ColumnRole.YEAR, _YEAR_NAMES),
    (ColumnRole.COUNT, _COUNT_NAMES),
    (ColumnRole.MEASURE, _MEAN_NAMES),
)


def is_spread_column(name: str) -> bool:
    """Does this column hold a measure of how spread out a group is?

    Public alongside `is_rate_column` for the same reason: `domain/exhibits.py` needs to
    ask it to narrate which column the repaired query added, and it had a byte-identical
    copy of this pattern. Two copies of the rule for reading a column name is exactly the
    duplication the comments above warn about — the `n$` and `\\b` bugs recorded there were
    each fixed in one place, and a second copy would have kept the old behaviour silently.
    """
    return _SPREAD_NAMES.search(name) is not None


def is_count_column(name: str) -> bool:
    """Does this column hold a row count? See `is_spread_column` for why it is public."""
    return _COUNT_NAMES.search(name) is not None


def column_role(name: str, type_name: str = "") -> ColumnRole:
    """Classify one column by its name, with its type as the tie-breaker.

    An id is checked before everything else and never becomes a measure however numeric it
    looks: `student_id` averages to a number that means nothing, and a docket case built on
    one would be arithmetic with no subject.
    """
    if _ID_NAMES.search(name):
        return ColumnRole.IDENTIFIER
    numeric = type_name.upper().split("(")[0] in _NUMERIC_TYPES
    if numeric and _NOT_A_MEASURE.search(name) and not _YEAR_NAMES.search(name):
        # Averageable and meaningless. Treated as a label rather than an identifier: a
        # zipcode or a country's latitude can legitimately group rows, it just must never
        # be the thing being averaged.
        return ColumnRole.LABEL
    for role, pattern in _ROLE_ORDER:
        # A year is a year whatever its type; the rest have to be numbers to be the thing
        # their name suggests. A STRING column called `total_band` is a label.
        if pattern.search(name) and (role is ColumnRole.YEAR or numeric):
            return role
    if numeric:
        return ColumnRole.MEASURE
    return ColumnRole.LABEL


def is_rate_column(name: str) -> bool:
    """Does this column hold a proportion?

    Public because the result table has to format rates the way the judge reads them. The
    verdict says "44.5% against 30.4%"; the table beside it rendered the same column as
    0.4 against 0.3, which is not a rounding difference — at one decimal, two of the four
    Berkeley departments that reverse stop looking like they reverse at all.
    """
    return _RATE_NAMES.search(name) is not None


class Verdict(Enum):
    """The four outcomes a claim can reach. There is no error state by design.

    HALF_TRUE was added with the case docket, because two of its cases cannot be judged
    honestly without it. China really is the largest total emitter and Bulgaria's spending
    really did halve in the nineties: calling either BUSTED teaches something false, and
    calling either HOLDS throws the lesson away. Its sentence always has the same shape —
    the number is right, the picture it paints is not — which is the commonest form real
    statistical misinformation actually takes.
    """

    HOLDS = "HOLDS"
    BUSTED = "BUSTED"
    HALF_TRUE = "HALF_TRUE"
    CANT_TELL = "CANT_TELL"


@dataclass(frozen=True)
class Column:
    name: str
    type_name: str = "STRING"


@dataclass(frozen=True)
class ResultTable:
    """The rows behind one Genie query attachment, as strings, exactly as returned."""

    columns: list[Column]
    rows: list[list[str | None]]

    def index_of(self, pattern: re.Pattern[str]) -> int | None:
        for i, col in enumerate(self.columns):
            if pattern.search(col.name):
                return i
        return None


@dataclass(frozen=True)
class Analysis:
    """Why a verdict came out the way it did, in terms a child can be shown."""

    verdict: Verdict
    reason: str
    groups: tuple[str, str] | None = None
    means: tuple[float, float] | None = None
    delta: float | None = None
    pooled_spread: float | None = None
    effect_size: float | None = None
    judged_on_spread: bool = False

    # Which judge produced this. The view picks its visual from here rather than from the
    # case, so a free-text claim that happens to return a subgroup table gets the subgroup
    # picture for free — the same reason the judges dispatch on shape and not on case id.
    mode: str = "means"
    # Ranking and per-unit comparisons: who came top, and who came top last time.
    leader: str | None = None
    previous_leader: str | None = None
    # Subgroup breakdowns: how many subgroups pointed the other way, out of how many.
    reversed_in: int | None = None
    subgroup_count: int | None = None
    # Series: the span actually examined, and the span available.
    window: tuple[float, float] | None = None
    whole_series: tuple[float, float] | None = None


def _to_float(cell: str | None) -> float | None:
    """Read a returned cell as a number, or decide it is not one.

    NaN and Infinity are rejected deliberately. `float()` accepts both, and Spark
    stringifies them into JSON results because JSON has no native representation — so a
    NaN average would otherwise sail through every guard here and be reported to a child
    as "the higher average, by nan".
    """
    if cell is None:
        return None
    try:
        value = float(str(cell).replace(",", "").strip())
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def analyse(table: ResultTable, previous: ResultTable | None = None) -> Analysis:
    """Judge whatever Genie returned, by the shape of it.

    Dispatch is on the COLUMNS THAT CAME BACK and never on which case is being played.
    That is deliberate and it is what makes the docket more than a set of scripted demos:
    a claim someone types themselves reaches exactly the same judges, so a free-text
    question that happens to return a year column is read as a series without anyone
    having anticipated it.

    `previous` is the table from the turn before, and only the per-unit judge uses it: a
    ranking by emissions per person cannot know it has overturned anything unless it can
    see what the ranking by total said. Every other judge reads one table.

    Anything none of them can read returns CANT_TELL, which the app celebrates as a win
    rather than hiding as an error.
    """
    if not table.rows:
        return Analysis(Verdict.CANT_TELL, "This query returned no rows at all.")

    # Order matters, and each guard is narrower than the one below it.
    if table.index_of(_PER_UNIT_NAMES) is not None:
        return _analyse_per_unit(table, previous)
    if _distinct_years(table) >= 2:
        return _analyse_series(table)
    if _subgroup_axes(table) is not None:
        return _analyse_subgroups(table)
    if len(table.rows) == 2 and _rate_index(table) is not None:
        return _analyse_two_rates(table)
    if len(table.rows) > 2 and table.index_of(_MEAN_NAMES) is None:
        return _analyse_ranking(table)
    return _analyse_two_means(table)


def _analyse_two_means(table: ResultTable) -> Analysis:
    """Judge a two-group comparison of averages — the original case, unchanged."""
    if len(table.rows) < 2:
        return Analysis(Verdict.CANT_TELL, "This query compared fewer than two groups.")
    if len(table.rows) > 2:
        return Analysis(
            Verdict.CANT_TELL,
            f"This query returned {len(table.rows)} groups, so there is no single "
            "comparison to make.",
        )

    mean_idx = table.index_of(_MEAN_NAMES)
    if mean_idx is None:
        return Analysis(Verdict.CANT_TELL, "This query returned no average to compare.")

    # `row[mean_idx]` is guarded rather than indexed directly, the same way `_rate_of` does
    # it. A row shorter than the column list raised IndexError straight out of `analyse` —
    # not reachable from a real Genie response, whose rows are built one cell per column,
    # but this is the third arithmetic path in one week to reach the player as an exception
    # instead of the CANT_TELL the whole engine promises, and the other two were reachable.
    means = _numbers([_cell(row, mean_idx) for row in table.rows])
    if means is None:
        return Analysis(Verdict.CANT_TELL, "The averages in this result are not numbers.")

    label_idx = _first_label_index(table, exclude={mean_idx})
    groups = (
        _label(table.rows[0], label_idx, "group 1"),
        _label(table.rows[1], label_idx, "group 2"),
    )
    # Rounded to the one decimal place the rows are displayed at, before the gap is
    # measured. Genie returns 492.64332917705605 and 488.0624311645937; subtracting those
    # gives 4.6, while the two numbers a child can see on screen give 4.5. Quoting a gap
    # the visible figures contradict is the same defect the headline chart had, and this
    # is the sentence the verdict is built on.
    a, b = round(means[0], 1), round(means[1], 1)
    delta = a - b

    spread_idx = table.index_of(_SPREAD_NAMES)
    if spread_idx is None:
        # Nothing here says how spread out the scores are, so any gap at all looks
        # decisive. This is the naive first draft, and it is the point.
        if delta == 0:
            return Analysis(
                Verdict.BUSTED,
                "The two averages are identical.",
                groups,
                (a, b),
                delta,
            )
        return Analysis(
            Verdict.HOLDS,
            # "came out with", not "has": the subject is a group label Genie returned, and
            # nothing guarantees its number. This template read "boy has the higher
            # average" on a recorded screen and would have read "boys has" the moment the
            # generator used plural labels — which is the same defect the rate sentence
            # was already rewritten to avoid. Verbs here must not agree with anything.
            f"{groups[0] if delta > 0 else groups[1]} came out with the higher average, "
            f"by {abs(delta):.1f}.",
            groups,
            (a, b),
            delta,
        )

    spreads = _numbers([_to_float(row[spread_idx]) for row in table.rows])
    if spreads is None:
        return Analysis(Verdict.CANT_TELL, "The spread values in this result are not numbers.")

    pooled = _pooled_spread(table, spreads[0], spreads[1])
    if pooled == 0:
        return Analysis(
            Verdict.CANT_TELL,
            "Every score in each group is identical, so the spread cannot be compared.",
            groups,
            (a, b),
            delta,
        )

    effect = abs(delta) / pooled
    if effect < NEGLIGIBLE_EFFECT:
        return Analysis(
            Verdict.BUSTED,
            f"The gap is {abs(delta):.1f}, but scores vary by about {pooled:.0f} inside each "
            f"group. Nearly everyone overlaps.",
            groups,
            (a, b),
            delta,
            pooled,
            effect,
            judged_on_spread=True,
        )
    return Analysis(
        Verdict.HOLDS,
        f"The gap is {abs(delta):.1f} against a spread of about {pooled:.0f}, which is a real "
        f"difference.",
        groups,
        (a, b),
        delta,
        pooled,
        effect,
        judged_on_spread=True,
    )


def _first_label_index(table: ResultTable, exclude: set[int]) -> int | None:
    """The first column that reads like a group name rather than a measurement."""
    for i in range(len(table.columns)):
        if i in exclude:
            continue
        if all(_to_float(row[i]) is None for row in table.rows):
            return i
    return None


def _pooled_spread(table: ResultTable, sd_a: float, sd_b: float) -> float:
    """Pooled standard deviation, weighted by group size when Genie returned counts."""
    count_idx = table.index_of(_COUNT_NAMES)
    if count_idx is not None:
        n_a = _to_float(table.rows[0][count_idx])
        n_b = _to_float(table.rows[1][count_idx])
        # Both counts must be real group sizes. Anything else — negative, zero, or a
        # column that merely looked like a count — falls back to the unweighted pooling
        # rather than producing a negative variance.
        if n_a is not None and n_b is not None and n_a >= 1 and n_b >= 1 and n_a + n_b > 2:
            num = (n_a - 1) * sd_a**2 + (n_b - 1) * sd_b**2
            if num >= 0:
                return (num / (n_a + n_b - 2)) ** 0.5
    return ((sd_a**2 + sd_b**2) / 2) ** 0.5


# -- shape detection -----------------------------------------------------------------


def _numeric_columns(table: ResultTable) -> list[int]:
    """Columns where every row reads as a number."""
    return [
        i
        for i in range(len(table.columns))
        if table.rows and all(_to_float(row[i]) is not None for row in table.rows if i < len(row))
    ]


def _label_columns(table: ResultTable) -> list[int]:
    """Columns that name things rather than measure them."""
    numeric = set(_numeric_columns(table))
    return [i for i in range(len(table.columns)) if i not in numeric]


def _rate_index(table: ResultTable) -> int | None:
    """A column holding a rate, or a pair of counts one can be made from."""
    direct = table.index_of(_RATE_NAMES)
    if direct is not None:
        return direct
    tried, succeeded = table.index_of(_TRIED_NAMES), table.index_of(_SUCCEEDED_NAMES)
    return succeeded if tried is not None and succeeded is not None else None


def _cell(row: list[str | None], index: int) -> float | None:
    """One numeric cell, or None when the row is too short to have it.

    A ragged row is not something a real Genie response produces — `table_from_statement`
    builds one cell per column — but "degrades to CANT_TELL rather than raising, for ANY
    response shape" is the engine's stated contract, and a contract that holds only for
    well-formed input is a contract about the input.
    """
    return _to_float(row[index]) if index < len(row) else None


def _label(row: list[str | None], index: int | None, fallback: str) -> str:
    """A group's name, or a stand-in when the column or the cell is missing."""
    if index is None or index >= len(row) or row[index] is None:
        return fallback
    return str(row[index])


def _rate_of(table: ResultTable, row: list[str | None]) -> float | None:
    """This row's rate, preferring the two counts over a pre-computed column.

    The counts are preferred deliberately. A rate column arrives as 0.445 or as 44.5
    depending on how Genie chose to express it, while dividing admitted by applicants is
    unambiguous — and it is the arithmetic the app claims to be doing.
    """
    tried, succeeded = table.index_of(_TRIED_NAMES), table.index_of(_SUCCEEDED_NAMES)
    if tried is not None and succeeded is not None:
        n = _to_float(row[tried]) if tried < len(row) else None
        k = _to_float(row[succeeded]) if succeeded < len(row) else None
        if n is not None and k is not None and n > 0:
            return _proportion(k / n)
    direct = table.index_of(_RATE_NAMES)
    if direct is not None and direct < len(row):
        value = _to_float(row[direct])
        if value is not None:
            # Percentages and proportions both occur; normalise to a proportion.
            return _proportion(value / 100 if value > 1 else value)
    return None


def _proportion(value: float) -> float | None:
    """A rate, or None if it is not one.

    Every caller of this feeds `_cohens_h`, which takes `asin(sqrt(p))` — undefined outside
    0..1. Nothing upstream guaranteed the range: `k / n` is only a proportion if the counts
    mean what their names suggest, and the x100/÷100 heuristic above cannot tell 145 from a
    percentage. A "succeeded" column larger than its "tried" column, or a rate of 145 or
    −10, produced `ValueError: math domain error` all the way out through `commit_call` to
    a raw traceback in front of the player — the exact opposite of the rule that any result
    shape degrades to CANT_TELL rather than erroring.

    Returning None rather than clamping is deliberate: the existing `if any(r is None ...)`
    guards in both rate judges already turn that into an honest CANT_TELL, and clamping
    would invent a defensible-looking verdict from numbers that plainly do not mean what
    the app assumed. This matters more since discovery began generating cases from tables
    nobody probed — a tried/succeeded pair matched by name alone is exactly where counts
    that do not nest show up.
    """
    return value if 0.0 <= value <= 1.0 else None


def _distinct_years(table: ResultTable) -> int:
    """How many different years this result covers.

    A ranking for one year carries a year column too, so the count is what separates a
    series from a snapshot. Reading only the column's presence sent the emissions ranking
    to the series judge, which had nothing true to say about it.
    """
    idx = table.index_of(_YEAR_NAMES)
    if idx is None:
        return 0
    return len({str(row[idx]) for row in table.rows if idx < len(row) and row[idx] is not None})


def _subgroup_axes(table: ResultTable) -> tuple[int, int] | None:
    """(subgroup column, compared-group column) when this is a breakdown.

    A breakdown has two naming columns — department and gender — where one takes exactly
    two values and the other takes several. Anything else is not something this judge can
    read as "the same comparison, repeated inside each subgroup".
    """
    labels = _label_columns(table)
    if len(labels) < 2 or len(table.rows) < 4:
        return None
    for outer in labels:
        for inner in labels:
            if outer == inner:
                continue
            outer_values = {str(r[outer]) for r in table.rows if outer < len(r)}
            inner_values = {str(r[inner]) for r in table.rows if inner < len(r)}
            if len(inner_values) == 2 and len(outer_values) >= 2:
                return outer, inner
    return None


def _cohens_h(p_a: float, p_b: float) -> float:
    """Effect size for two proportions.

    The proportion analogue of the standardised difference the spread judge already uses,
    so both read against the same 0.2 convention. A raw percentage-point gap cannot: eight
    points means something very different at 50% than at 2%.
    """
    return abs(2 * math.asin(math.sqrt(p_a)) - 2 * math.asin(math.sqrt(p_b)))


def _numbers(values: list[float | None]) -> list[float] | None:
    """The parsed cells, or None if any of them failed to parse.

    Every judge guards on "did every cell parse" and then indexes the list. Doing the
    guard here hands back the narrowed list the guard implies, instead of leaving a
    `type: ignore` at each use.
    """
    if any(v is None for v in values):
        return None
    return [v for v in values if v is not None]


# -- the judges ----------------------------------------------------------------------


def _analyse_two_rates(table: ResultTable) -> Analysis:
    """Two groups, compared on how often something happened to each."""
    rates = _numbers([_rate_of(table, row) for row in table.rows])
    if rates is None:
        return Analysis(Verdict.CANT_TELL, "This result has no rate that can be compared.")

    labels = _label_columns(table)
    groups = (
        (str(table.rows[0][labels[0]]), str(table.rows[1][labels[0]]))
        if labels
        else ("group 1", "group 2")
    )
    a, b = rates[0], rates[1]
    ahead = groups[0] if a > b else groups[1]

    if _cohens_h(a, b) < NEGLIGIBLE_EFFECT:
        return Analysis(
            Verdict.BUSTED,
            f"{a * 100:.1f}% against {b * 100:.1f}% — too close to call a difference.",
            groups,
            (a * 100, b * 100),
            a * 100 - b * 100,
            mode="rates",
            leader=ahead,
        )
    return Analysis(
        Verdict.HOLDS,
        f"{ahead} came out ahead: {max(a, b) * 100:.1f}% against {min(a, b) * 100:.1f}%, "
        f"a gap of {abs(a - b) * 100:.1f} points.",
        groups,
        (a * 100, b * 100),
        a * 100 - b * 100,
        mode="rates",
        leader=ahead,
    )


@dataclass(frozen=True)
class Subgroup:
    """One subgroup's two rates, as percentages, with the sizes behind them."""

    name: str
    left: str
    right: str
    left_rate: float
    right_rate: float
    left_size: float
    right_size: float

    @property
    def favours_right(self) -> bool:
        return self.right_rate > self.left_rate


def subgroup_rates(table: ResultTable) -> tuple[list[Subgroup], tuple[float, float]]:
    """Per-subgroup rates and the pooled pair, or ([], (0, 0)) if this is not a breakdown.

    Public because the reversal chart draws exactly what the subgroup judge decided on. If
    the picture were to recompute the rates itself, the two could disagree — and the one
    place that must never happen is the panel whose entire job is showing that a number and
    a picture can tell different stories.
    """
    axes = _subgroup_axes(table)
    if axes is None:
        return [], (0.0, 0.0)
    outer, inner = axes
    sides = sorted({str(r[inner]) for r in table.rows if inner < len(r)})
    if len(sides) != 2:
        return [], (0.0, 0.0)

    tried_idx = table.index_of(_TRIED_NAMES)
    collected: dict[str, dict[str, tuple[float, float]]] = {}
    for row in table.rows:
        if outer >= len(row) or inner >= len(row):
            continue
        rate = _rate_of(table, row)
        if rate is None:
            return [], (0.0, 0.0)
        size = (_to_float(row[tried_idx]) or 0.0) if tried_idx is not None else 0.0
        collected.setdefault(str(row[outer]), {})[str(row[inner])] = (rate, size)

    left, right = sides
    groups = [
        Subgroup(
            name=name,
            left=left,
            right=right,
            left_rate=values[left][0] * 100,
            right_rate=values[right][0] * 100,
            left_size=values[left][1],
            right_size=values[right][1],
        )
        for name, values in sorted(collected.items())
        if len(values) == 2
    ]
    if len(groups) < 2:
        return [], (0.0, 0.0)

    pooled = []
    for side in (left, right):
        hits = sum(v[side][0] * v[side][1] for v in collected.values() if len(v) == 2)
        total = sum(v[side][1] for v in collected.values() if len(v) == 2)
        pooled.append((hits / total * 100) if total else 0.0)
    return groups, (pooled[0], pooled[1])


def _analyse_subgroups(table: ResultTable) -> Analysis:
    """The same comparison, repeated inside each subgroup.

    The judge that busts Simpson's paradox, and the arithmetic is deliberately the kind
    anyone can check by eye: work out each subgroup's two rates, see which side wins in
    each, and count. When the pooled answer points one way and most of the subgroups point
    the other, the pooled answer was about who was in which subgroup.
    """
    axes = _subgroup_axes(table)
    if axes is None:
        return Analysis(Verdict.CANT_TELL, "This result is not a breakdown of two groups.")
    outer, inner = axes
    sides = sorted({str(r[inner]) for r in table.rows if inner < len(r)})
    if len(sides) != 2:
        return Analysis(Verdict.CANT_TELL, "This breakdown does not compare two groups.")

    tried_idx = table.index_of(_TRIED_NAMES)
    per_subgroup: dict[str, dict[str, tuple[float, float]]] = {}
    for row in table.rows:
        if outer >= len(row) or inner >= len(row):
            continue
        rate = _rate_of(table, row)
        if rate is None:
            return Analysis(Verdict.CANT_TELL, "This breakdown has no rate to compare.")
        size = (_to_float(row[tried_idx]) or 0.0) if tried_idx is not None else 0.0
        per_subgroup.setdefault(str(row[outer]), {})[str(row[inner])] = (rate, size)

    complete = {k: v for k, v in per_subgroup.items() if len(v) == 2}
    if len(complete) < 2:
        return Analysis(
            Verdict.CANT_TELL, "Not enough subgroups have both groups in them to compare."
        )

    # Pooled: every subgroup added back together, which is what the naive query did.
    totals = {
        side: (
            sum(v[side][0] * v[side][1] for v in complete.values()),
            sum(v[side][1] for v in complete.values()),
        )
        for side in sides
    }
    if any(n == 0 for _, n in totals.values()):
        return Analysis(Verdict.CANT_TELL, "This breakdown has no group sizes to weight by.")
    pooled = {side: hits / n for side, (hits, n) in totals.items()}
    leader = max(pooled, key=lambda s: pooled[s])
    other = next(s for s in sides if s != leader)

    against = sum(1 for v in complete.values() if v[other][0] > v[leader][0])
    total = len(complete)
    groups = (leader, other)
    means = (pooled[leader] * 100, pooled[other] * 100)

    if against * 2 > total:
        return Analysis(
            Verdict.BUSTED,
            # Phrased without a verb that has to agree with the label. Group names arrive
            # from Genie's rows and can be singular or plural — "boy", "men", "Dept A" —
            # and "Overall men comes out ahead" reached a live screen before this.
            f"Overall, {leader}: {means[0]:.1f}% against {means[1]:.1f}%. But {other} did "
            f"better in {against} of the {total} groups underneath. The overall figure is "
            f"about who applied where, not about who did better.",
            groups,
            means,
            means[0] - means[1],
            mode="subgroups",
            leader=leader,
            reversed_in=against,
            subgroup_count=total,
        )
    return Analysis(
        Verdict.HOLDS,
        f"Overall, {leader}: {means[0]:.1f}% against {means[1]:.1f}% — and still ahead in "
        f"{total - against} of the {total} groups underneath. Breaking it down did not "
        f"change the answer.",
        groups,
        means,
        means[0] - means[1],
        mode="subgroups",
        leader=leader,
        reversed_in=against,
        subgroup_count=total,
    )


def series_points(table: ResultTable | None) -> list[tuple[float, float]]:
    """(year, value) pairs, sorted, or [] when this is not a series.

    Public for the same reason `subgroup_rates` is: the window chart draws exactly the
    points the series judge measured. A picture that re-read the table itself could pick a
    different value column and disagree with the sentence beside it.
    """
    if table is None or not table.rows:
        return []
    year_idx = table.index_of(_YEAR_NAMES)
    if year_idx is None:
        return []
    value_idx = next((i for i in _numeric_columns(table) if i != year_idx), None)
    if value_idx is None:
        return []

    points = []
    for row in table.rows:
        year = _to_float(row[year_idx]) if year_idx < len(row) else None
        value = _to_float(row[value_idx]) if value_idx < len(row) else None
        if year is not None and value is not None:
            points.append((year, value))
    return sorted(points)


def _analyse_series(table: ResultTable) -> Analysis:
    """A measure over time, judged on whether the span shown speaks for the whole run."""
    if table.index_of(_YEAR_NAMES) is None:
        return Analysis(Verdict.CANT_TELL, "This result has no year to read.")
    points = series_points(table)
    if not points:
        return Analysis(Verdict.CANT_TELL, "This result has nothing measured to follow.")
    if len(points) < 2:
        return Analysis(Verdict.CANT_TELL, "There are not enough years here to see a trend.")
    (first_year, first), (last_year, last) = points[0], points[-1]
    change = last - first
    direction = "fell" if change < 0 else "rose"

    # Two points is a window someone chose. More is a series — and a series can contradict
    # the window inside it, which is the whole case.
    if len(points) == 2:
        return Analysis(
            Verdict.HOLDS,
            f"Between {first_year:.0f} and {last_year:.0f} it {direction} from {first:.2f} "
            f"to {last:.2f}.",
            mode="series",
            window=(first, last),
        )

    worst_year, worst = min(points, key=lambda p: p[1])
    if change >= 0 and worst < first:
        return Analysis(
            Verdict.HALF_TRUE,
            f"It did fall — as low as {worst:.2f} in {worst_year:.0f}. But across the whole "
            f"run it {direction} from {first:.2f} in {first_year:.0f} to {last:.2f} in "
            f"{last_year:.0f}. The fall was real, and it was not the trend.",
            mode="series",
            window=(worst, last),
            whole_series=(first, last),
        )
    if change < 0:
        return Analysis(
            Verdict.HOLDS,
            f"Across the whole run it {direction} from {first:.2f} in {first_year:.0f} to "
            f"{last:.2f} in {last_year:.0f}.",
            mode="series",
            whole_series=(first, last),
        )
    return Analysis(
        Verdict.BUSTED,
        f"Across the whole run it {direction} from {first:.2f} in {first_year:.0f} to "
        f"{last:.2f} in {last_year:.0f}.",
        mode="series",
        whole_series=(first, last),
    )


def _analyse_ranking(table: ResultTable) -> Analysis:
    """Who came top, and by how far."""
    numeric = [i for i in _numeric_columns(table) if not _YEAR_NAMES.search(table.columns[i].name)]
    # A rank column is an index, not the measure being ranked; drop it unless it is all
    # there is.
    measures = [i for i in numeric if not _RATE_NAMES.search(table.columns[i].name)] or numeric
    labels = _label_columns(table)
    if not measures or not labels:
        return Analysis(Verdict.CANT_TELL, "There is nothing ranked in this result.")

    measure, name = measures[0], labels[0]
    ranked = []
    for row in table.rows:
        value = _to_float(row[measure]) if measure < len(row) else None
        if value is not None and name < len(row):
            ranked.append((value, str(row[name])))
    if len(ranked) < 2:
        return Analysis(Verdict.CANT_TELL, "There are not enough rows here to rank.")

    ranked.sort(reverse=True)
    (top, leader), (second, runner_up) = ranked[0], ranked[1]
    margin = (
        f" — {top / second:.1f} times {runner_up}, the next one down."
        if second
        else f", ahead of {runner_up}."
    )
    return Analysis(
        Verdict.HOLDS,
        f"{leader} is top, at {top:,.1f}{margin}",
        mode="ranking",
        leader=leader,
        means=(top, second),
    )


def _analyse_per_unit(table: ResultTable, previous: ResultTable | None) -> Analysis:
    """The same places, measured per person instead of in total.

    The only judge that reads the previous turn, because on its own a per-person ranking
    is just another ranking. What makes it a verdict is that the question was asked about
    a total and the answer changes when the denominator does — and both answers are true,
    which is exactly where HALF_TRUE earns its place.
    """
    per_unit_idx = table.index_of(_PER_UNIT_NAMES)
    labels = _label_columns(table)
    if per_unit_idx is None or not labels:
        return Analysis(Verdict.CANT_TELL, "There is no per-person figure here to compare.")

    name = labels[0]
    ranked = []
    for row in table.rows:
        value = _to_float(row[per_unit_idx]) if per_unit_idx < len(row) else None
        if value is not None and name < len(row):
            ranked.append((value, str(row[name])))
    if not ranked:
        return Analysis(Verdict.CANT_TELL, "The per-person figures here are not numbers.")

    ranked.sort(reverse=True)
    top_value, leader = ranked[0]

    was = _analyse_ranking(previous) if previous is not None else None
    former = was.leader if was is not None else None
    if former is None:
        return Analysis(
            Verdict.HOLDS,
            f"Per person, {leader} is top at {top_value:,.2f}.",
            mode="per_unit",
            leader=leader,
        )
    if former == leader:
        return Analysis(
            Verdict.HOLDS,
            f"{leader} is top either way — by the total and per person, at {top_value:,.2f}.",
            mode="per_unit",
            leader=leader,
            previous_leader=former,
        )
    return Analysis(
        Verdict.HALF_TRUE,
        f"By the total, {former} was top. Per person it is {leader}, at {top_value:,.2f}. "
        f"Both are true: a total measures how big a place is as much as what it does.",
        mode="per_unit",
        leader=leader,
        previous_leader=former,
    )
