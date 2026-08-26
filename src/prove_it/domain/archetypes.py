"""The tricks, described by the SHAPE of table they need rather than by a dataset.

The docket used to be five hand-written cases naming five specific tables. That is fine
in the workspace they were written for and useless in anyone else's: open the app against
a catalog with no `berkeley_admissions` and you get five cases that cannot run.

What makes the docket teachable is not those tables. It is the five *shapes* a misleading
number takes — a gap swamped by the spread inside each group, a total pooled across groups
that are not alike, a window someone chose, a count that measures how big a place is
rather than what it does. Those are properties of statistics, and they are true of any data
that has the right columns.

So the pedagogy is authored once here, per trick, and the *binding to data* is discovered.
An archetype says what roles it needs — a measure and a group to compare it across, a
tried/succeeded pair and something to split it by — and `discovery.py` matches that against
whatever Unity Catalog actually holds.

Two honesty rules the split has to respect:

**The lesson belongs to the shape, not the table.** Every string here is true of any table
matching the archetype. Nothing quotes a figure, names a country or claims a source,
because none of that is known until a table is bound to it.

**A discovered case is not a probed case.** The five curated cases in `cases.py` were run
against live Genie three times each and their arcs measured. A case generated here has
been run zero times, and the app says so. It may not flip. It may not even reach a verdict
— in which case the existing CANT_TELL path is the honest outcome, and the app already
treats that as a win rather than an error.
"""

from __future__ import annotations

from dataclasses import dataclass

from prove_it.domain.verdict import ColumnRole


@dataclass(frozen=True)
class Archetype:
    """One trick, and the table shape that can carry it."""

    key: str
    # The eyebrow on a generated card: the shape of evidence the first query will produce.
    evidence: str
    trick: str
    lesson: str
    in_the_wild: str
    nudge: str
    # How the claim and the follow-up are worded once a table is bound. `{measure}`,
    # `{group}`, `{entity}` and `{subgroup}` are filled from the columns that matched.
    claim_template: str
    follow_up: str
    repair_label: str
    # Column roles this archetype cannot do without. A table missing any of them is not a
    # candidate — better no case than a case whose query cannot be asked.
    needs: tuple[ColumnRole, ...] = ()
    # Roles that must be present as a *second* distinct column, e.g. something to break a
    # pooled rate down by. Kept separate from `needs` so the matcher can say which is
    # missing.
    needs_split: bool = False
    # Ranked above others when several archetypes match one table, because some tricks
    # teach more than others on the same columns.
    weight: int = 1


HIDDEN_SPREAD = Archetype(
    key="spread",
    evidence="Two averages",
    trick="The hidden spread",
    lesson=(
        "An average tells you where a group sits. It says nothing about how much the "
        "people inside it differ from each other — and usually they differ far more than "
        "the groups do."
    ),
    in_the_wild=(
        "Any headline comparing two groups by their average: salaries, test scores, waiting times."
    ),
    nudge=(
        "**Is that a fair way to check it?** An average tells you where a group sits. It "
        "says nothing about how much people inside the group differ from each other."
    ),
    claim_template="{measure_label} is really higher for some {group_label} than others",
    follow_up="show the spread too, and how many are in each group",
    repair_label="Ask Genie to show the spread too",
    needs=(ColumnRole.MEASURE, ColumnRole.LABEL),
    weight=3,
)

POOLED_RATE = Archetype(
    key="pooled_rate",
    evidence="A pooled rate",
    trick="Simpson's paradox",
    lesson=(
        "Every group inside can lean one way while the total leans the other. It happens "
        "when the groups differ in size and in difficulty, so the total is weighted by "
        "who was in which."
    ),
    in_the_wild=(
        "Hospital survival rates, drug trials, pay gaps — anywhere a total is quoted "
        "across groups that are not alike."
    ),
    nudge=(
        "**Is that a fair way to check it?** That is one rate for everybody. If the groups "
        "underneath it are not alike, the total is telling you who applied where as much "
        "as who did better."
    ),
    claim_template="some {group_label} are more likely to be selected than others",
    follow_up="break that down by {subgroup}",
    repair_label="Ask Genie to break it down",
    needs=(ColumnRole.TRIED, ColumnRole.SUCCEEDED, ColumnRole.LABEL),
    needs_split=True,
    weight=5,
)

CHOSEN_WINDOW = Archetype(
    key="window",
    evidence="A window of years",
    trick="The chosen window",
    lesson=(
        "A fall between two chosen years is a fact about those two years. It is not the "
        "same thing as a direction of travel, and the years someone picked are the part "
        "you were not shown."
    ),
    in_the_wild="Crime figures, share prices, temperature records.",
    nudge=(
        "**Is that a fair way to check it?** Those are two years someone chose. The data "
        "goes back further, and a fall between two points is not a trend."
    ),
    claim_template="{measure_label} fell sharply over the years in this data",
    follow_up="now show every year in the data, not just those",
    repair_label="Ask Genie for every year, not just those two",
    needs=(ColumnRole.YEAR, ColumnRole.MEASURE, ColumnRole.LABEL),
    weight=4,
)

MISSING_DENOMINATOR = Archetype(
    key="denominator",
    evidence="A total, not a rate",
    trick="The missing denominator",
    lesson=(
        "A total measures how big a place is as much as what it does. Divide by the "
        "people and the order can change completely — and both numbers are true."
    ),
    in_the_wild="Crime counts by city, case numbers by country, totals of anything by size.",
    nudge=(
        "**Is that a fair way to check it?** That is a total. A bigger place will have a "
        "bigger total almost whatever it does — the question is what it does per person."
    ),
    claim_template="one {group_label} is the biggest for {measure_label}",
    follow_up="now show it per person instead of the total",
    repair_label="Ask Genie to show it per person",
    needs=(ColumnRole.MEASURE, ColumnRole.PER_UNIT, ColumnRole.LABEL),
    weight=4,
)

ARCHETYPES: tuple[Archetype, ...] = (
    POOLED_RATE,
    CHOSEN_WINDOW,
    MISSING_DENOMINATOR,
    HIDDEN_SPREAD,
)
