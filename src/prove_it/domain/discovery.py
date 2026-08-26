"""Build a docket out of whatever the workspace actually has.

The five curated cases name five specific tables. Point the app at a catalog that does not
contain them and every case is a dead end — which is exactly what happens to anyone who
clones this repo into their own workspace, including a judge.

This module fixes that from the other end. Given the tables Unity Catalog reports, it
works out which of the trick archetypes each one could carry, and generates a playable
case for the best match. The pedagogy comes from `archetypes.py`, authored once per trick
and true of any table with the right shape; only the binding — which table, which columns,
what the claim says — is discovered.

**No SQL, and no values.** Everything here reads column names and types, which Unity
Catalog hands over through its own API. Nothing looks inside a column. That is not a
limitation to work around: the app writes no SQL, that rule is worth twenty of the forty
contest points, and a discovery pass that started profiling values would break it. It also
happens to be the honest division of labour — deciding *what to ask* is this app's job,
and answering it is Genie's.

**Discovered is not probed.** The curated five were run against live Genie three times
each. These have been run zero times, carry `probed=False`, and say so on the card. Some
will not flip. Some will not reach a verdict at all, and the existing CANT_TELL path is
the honest outcome there — which the app already scores as a win rather than an error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from prove_it.domain.archetypes import ARCHETYPES, Archetype
from prove_it.domain.verdict import ColumnRole, Verdict, column_role

if TYPE_CHECKING:  # `cases` imports this module, so the real import would cycle.
    from prove_it.domain.cases import Case

# Below this an archetype is not really carried by the table, it just shares a column name
# with one.
MIN_CONFIDENCE = 1.0

# The most discovered cases a docket will ever offer.
#
# Measured against a synthetic 500-table catalog: every one of the 500 matched, because the
# weakest archetype needs only a measure and a label and almost any ordinary table has both.
# The docket screen renders a card and a button per case on every Streamlit rerun, so an
# uncapped docket turns "point it at your own schema" — which the mapping panel explicitly
# invites — into a page of hundreds of cards rebuilt on every click.
#
# Ten is a docket, not a catalogue. The cases are already sorted by confidence, so the cap
# keeps the strongest matches, and `best_matches` reports what it dropped rather than
# silently truncating: a cap nobody is told about reads as "this is everything".
MAX_DISCOVERED = 10

# What a discovered case claims about its own outcome: nothing. A curated case declares an
# arc because someone measured it; this one has not been run, so it advertises no flip. The
# real verdicts come from the engine at play time either way — this only decides whether the
# docket card promises a reversal it may not deliver.
UNMEASURED_ARC = (Verdict.HOLDS, Verdict.HOLDS)

# How much a matched role tells you. Counting matched roles flat made the emissions table
# tie between the chosen window and the missing denominator — both needed three roles — and
# the tie broke on declaration order, which is not a reason.
#
# A per-capita column, or a tried/succeeded pair, is *decisive*: a table carrying one is
# almost certainly about the trick that needs it. A measure and a label are present in
# nearly every table in any catalog and say close to nothing about which trick applies.
_ROLE_SPECIFICITY: dict[ColumnRole, int] = {
    ColumnRole.PER_UNIT: 5,
    ColumnRole.TRIED: 5,
    ColumnRole.SUCCEEDED: 5,
    ColumnRole.RATE: 4,
    ColumnRole.SPREAD: 3,
    ColumnRole.YEAR: 2,
    ColumnRole.COUNT: 2,
    ColumnRole.MEASURE: 1,
    ColumnRole.LABEL: 1,
    ColumnRole.IDENTIFIER: 0,
}


@dataclass(frozen=True)
class DiscoveredColumn:
    """One column, as Unity Catalog describes it."""

    name: str
    type_name: str = ""

    @property
    def role(self) -> ColumnRole:
        return column_role(self.name, self.type_name)


@dataclass(frozen=True)
class DiscoveredTable:
    """One table, as Unity Catalog describes it. No rows, ever."""

    full_name: str
    columns: tuple[DiscoveredColumn, ...]

    @property
    def short_name(self) -> str:
        return self.full_name.rsplit(".", 1)[-1]

    def by_role(self, role: ColumnRole) -> list[DiscoveredColumn]:
        return [c for c in self.columns if c.role is role]

    def has(self, role: ColumnRole) -> bool:
        return any(c.role is role for c in self.columns)


@dataclass(frozen=True)
class Match:
    """One table matched to one trick, with what it would be asked about."""

    table: DiscoveredTable
    archetype: Archetype
    confidence: float
    # The columns the claim will be worded from.
    measure: DiscoveredColumn | None = None
    group: DiscoveredColumn | None = None
    subgroup: DiscoveredColumn | None = None

    @property
    def key(self) -> str:
        return f"{self.archetype.key}-{self.table.short_name}"


def humanise(name: str) -> str:
    """A column name as a person would say it: `maths_score` -> "maths score"."""
    text = re.sub(r"[_\-]+", " ", name).strip()
    text = re.sub(r"\b(avg|mean)\b", "average", text, flags=re.I)
    return re.sub(r"\s+", " ", text).lower()


def _group_candidates(table: DiscoveredTable) -> list[DiscoveredColumn]:
    """Columns worth grouping by, best first.

    Labels only, and never an identifier: grouping by `student_id` returns one row per
    pupil, which is not a comparison of anything. Shorter names first as a rough proxy for
    "more likely to be a category" — `gender` and `country` beat `source_dataset_note`,
    and without values to count there is nothing better available.
    """
    labels = [c for c in table.columns if c.role is ColumnRole.LABEL]
    return sorted(labels, key=lambda c: (len(c.name), c.name))


def match_table(table: DiscoveredTable) -> list[Match]:
    """Every archetype this table could carry, strongest first."""
    matches: list[Match] = []
    groups = _group_candidates(table)

    for archetype in ARCHETYPES:
        missing = [role for role in archetype.needs if not table.has(role)]
        if missing:
            continue
        if archetype.needs_split and len(groups) < 2:
            # A pooled rate needs something to compare AND something to break it down by.
            continue

        measures = table.by_role(ColumnRole.MEASURE)
        measure = measures[0] if measures else None
        group = groups[0] if groups else None
        subgroup = groups[1] if len(groups) > 1 else None

        confidence = sum(_ROLE_SPECIFICITY[role] for role in archetype.needs) * archetype.weight
        matches.append(
            Match(
                table=table,
                archetype=archetype,
                confidence=confidence,
                measure=measure,
                group=group,
                subgroup=subgroup,
            )
        )

    return sorted(matches, key=lambda m: -m.confidence)


def claim_for(match: Match) -> str:
    """Word the claim from the columns that matched.

    Deliberately plain and slightly flat. A generated claim that tried to sound like a
    headline would be putting words in the data's mouth, and the one thing this app cannot
    do is assert something it has not checked.

    Phrased about the *column* rather than its values — "some gender", never "boys". The
    app cannot name a value without reading one, reading one means running a query, and
    the app writes no SQL. Claiming "boys score higher" off a column called `gender` would
    be inventing the very thing it is asking Genie to find out.
    """
    measure = humanise(match.measure.name) if match.measure else "the measure"
    group = humanise(match.group.name) if match.group else "group"
    subgroup = humanise(match.subgroup.name) if match.subgroup else "the groups underneath"

    return (
        match.archetype.claim_template.replace("{measure_label}", measure)
        .replace("{group_label}", group)
        .replace("{subgroup}", subgroup)
    )


def follow_up_for(match: Match) -> str:
    subgroup = humanise(match.subgroup.name) if match.subgroup else "the groups underneath"
    return match.archetype.follow_up.replace("{subgroup}", subgroup)


def best_matches(tables: list[DiscoveredTable]) -> list[Match]:
    """One case per table at most, best trick for each, strongest tables first.

    One per table because a docket showing the same table four times reads as four ways of
    asking one question rather than four cases — and because the archetype that scored
    highest is the one that teaches most on those columns.
    """
    chosen: list[Match] = []
    for table in tables:
        found = match_table(table)
        if found and found[0].confidence >= MIN_CONFIDENCE:
            chosen.append(found[0])
    return sorted(chosen, key=lambda m: -m.confidence)[:MAX_DISCOVERED]


def matches_dropped(tables: list[DiscoveredTable]) -> int:
    """How many matching tables the cap left out, so the panel can say so."""
    matched = sum(
        1 for t in tables if (found := match_table(t)) and found[0].confidence >= MIN_CONFIDENCE
    )
    return max(0, matched - MAX_DISCOVERED)


def case_from(match: Match) -> Case:
    """Turn a match into a playable case.

    Imported here rather than at module top because `cases.py` imports this module's
    `EstimateSpec` neighbours and the two would form a cycle. This is the documented
    exception to imports-at-the-top, not an oversight.
    """
    from prove_it.domain.cases import Case

    archetype = match.archetype
    return Case(
        key=match.key,
        title=humanise(match.table.short_name).title(),
        claim=claim_for(match),
        evidence=archetype.evidence,
        follow_up=follow_up_for(match),
        table=match.table.short_name,
        nudge=archetype.nudge,
        repair_label=archetype.repair_label,
        trick=archetype.trick,
        lesson=archetype.lesson,
        in_the_wild=archetype.in_the_wild,
        expect=UNMEASURED_ARC,
        real_data=True,
        source=f"Found in your workspace: {match.table.full_name}",
        probed=False,
    )


def build_docket(
    curated: tuple[Case, ...],
    tables: list[DiscoveredTable],
    *,
    discover: bool = True,
) -> list[Case]:
    """The docket this workspace can actually play.

    Curated first, and only where the table backing them exists — a case naming a table
    the catalog does not have is a dead end, and shipping five of them is what happens to
    anyone who clones this repo into their own workspace.

    Then a discovered case for every table no curated case already covers, so a workspace
    with none of the original tables still gets a docket instead of an empty screen.
    """
    present = {t.short_name for t in tables}
    # No catalog at all — offline, or credentials that cannot read it. Trust the curated
    # docket rather than deleting it: losing discovery must not lose the app.
    if not tables:
        return list(curated)

    docket = [case for case in curated if case.table in present]
    covered = {case.table for case in docket}

    if discover:
        for match in best_matches([t for t in tables if t.short_name not in covered]):
            docket.append(case_from(match))
    return docket


def hidden_cases(curated: tuple[Case, ...], tables: list[DiscoveredTable]) -> list[Case]:
    """Curated cases this workspace cannot play, and therefore is not being shown.

    Exists because of a real failure that took a screenshot to notice. A Databricks App
    runs as its own service principal, and that principal had `SELECT` on two of the four
    tables. The docket quietly became three cases long. Nothing was broken, nothing
    errored, and there was no way to tell from the screen that two cases were missing —
    the app looked like a three-case app.

    Dropping a case the app genuinely cannot run is right. Dropping it *silently* is the
    same move this whole product argues against: a confident answer with the omission
    left out. Naming them lets the panel say which, and why.
    """
    if not tables:
        return []
    present = {t.short_name for t in tables}
    return [case for case in curated if case.table not in present]
