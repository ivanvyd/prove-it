"""The docket: the claims on offer, and what each one is really teaching.

Content, not logic. Nothing here decides a verdict — the judges in `verdict.py` do that,
by reading the shape of whatever Genie returned, and they never see a `Case`. That
separation is the point: a claim someone types themselves gets judged by exactly the same
arithmetic as a curated one, so the docket is a set of good starting points rather than a
set of scripted outcomes.

Every claim and follow-up here has been run against live Genie three times by
`scripts/probe_cases.py`, and the arc recorded in `expect` is what the real engine
produced over the real rows. They are not aspirations. If one stops holding, the probe
fails, and the rule is to rewrite the framing or cut the case rather than paper over it
in the view.

The antibody card is the thing a player is meant to leave with. It names the trick rather
than the answer, because "boys are not better at maths" is worth one rumour and "an
average hides how much people differ" is worth every rumour shaped like it.
"""

from __future__ import annotations

from dataclasses import dataclass

from prove_it.domain.estimate import EstimateSpec
from prove_it.domain.verdict import Verdict


@dataclass(frozen=True)
class Case:
    """One claim worth testing, and the follow-up that makes it fair."""

    key: str
    title: str
    claim: str
    # What kind of evidence the first query will produce — "Two averages", "A pooled
    # rate". This is the docket card's eyebrow, and it replaced the trick's name there on
    # purpose: once a call can be lost, a card reading "Simpson's paradox" is a bet that
    # cannot lose, and the surviving case would have had to announce "no trick". The
    # trick is named at the flip and on the antibody card, where it lands as a reveal.
    evidence: str
    follow_up: str
    table: str
    # The reveal screen has to argue that the first answer was not a fair test, and then
    # offer the fairer one. Both were hardcoded to the first case's wording — the app
    # asked "is that a fair way to check it? an average tells you where a group sits" over
    # a table of admission rates, and offered a button reading "show the spread too" that
    # had nothing to do with the department split it would actually run.
    nudge: str
    repair_label: str
    # What the trick is called, and what it does. Shown when the case closes, and kept for
    # the rest of the session.
    trick: str
    lesson: str
    # Where a player will meet the same trick outside this app.
    in_the_wild: str
    expect: tuple[Verdict, Verdict]
    # Real, published data, or generated? Said on screen every time, never implied.
    real_data: bool
    source: str = ""
    # What the player is asked to place before the seal breaks, scored against the gap the
    # verdict engine derives from Genie's rows. None where the trick is not a distance
    # between two numbers — the window and the denominator both produce no `delta`, and a
    # guess the app cannot check is worse than no guess at all.
    estimate: EstimateSpec | None = None
    # Was this case's two-turn arc measured against live Genie? True for the curated
    # docket, which `scripts/probe_cases.py` ran three times each. False for a case
    # discovered from the workspace's own tables, which has been run zero times and may
    # not flip — the card says so rather than implying a lesson nobody has checked.
    probed: bool = True

    @property
    def turns_the_verdict(self) -> bool:
        """Does the fair query actually change the answer?

        False for a case that survives scrutiny — which the docket needs at least one of,
        or it teaches that everything is a trick.
        """
        return self.expect[0] is not self.expect[1]


SPREAD = Case(
    key="spread",
    title="The average",
    claim="boys are better at maths",
    evidence="Two averages",
    follow_up="show the spread too, and how many are in each group",
    table="student_scores",
    nudge=(
        "**Is that a fair way to check it?** An average tells you where a group sits. It "
        "says nothing about how much people inside the group differ from each other."
    ),
    repair_label="Ask Genie to show the spread too",
    trick="The hidden spread",
    lesson=(
        "An average tells you where a group sits. It says nothing about how much the "
        "people inside it differ from each other — and usually they differ far more than "
        "the groups do."
    ),
    in_the_wild=(
        "Any headline comparing two groups by their average: salaries, test scores, waiting times."
    ),
    expect=(Verdict.HOLDS, Verdict.BUSTED),
    real_data=False,
    # No "Synthetic." prefix: the card already prints "Synthetic data ·" in front of this,
    # and on screen the two ran together as "Synthetic data · Synthetic. Generated from…".
    source="Generated from a fixed seed; contains no real pupils.",
    # The real gap is 4.5 points on a ruler that runs to 40. A player who expects "boys
    # are better at maths" to mean something visible places this far too high, and that
    # overshoot IS the lesson — it is the same intuition the truncated axis exploits two
    # beats later, caught here in the player's own hand before anyone has argued for it.
    estimate=EstimateSpec(
        prompt="Before you look — how many points apart are the two averages?",
        lo=0.0,
        hi=40.0,
        lo_label="No gap at all",
        hi_label="40 points apart",
        unit=" points",
    ),
)

READING = Case(
    key="reading",
    title="The gap that stays",
    claim="girls are better at reading",
    evidence="Two averages",
    follow_up="show the spread too, and how many are in each group",
    table="student_scores",
    nudge=(
        "**Is that a fair way to check it?** Same objection as before: an average says "
        "where a group sits and nothing about how much the people inside it differ."
    ),
    repair_label="Ask Genie to show the spread here too",
    # The case that SURVIVES. Same table, same follow-up and same objection as the maths
    # case — and the opposite outcome, because the gap here is wide against the spread.
    # The docket needs this or the call is not a call: a player who has learned that
    # "there's a trick" always pays has learned cynicism, which the project's own docs
    # name as the failure mode. Probed live 2/2 HOLDS -> HOLDS; the effect size is pinned
    # by tests/test_demo_data.py.
    trick="The gap that survives",
    lesson=(
        "Sometimes the fairer question agrees with the first one. A gap that stays wide "
        "next to the spread inside each group is a real difference — and telling those "
        "apart from the ones that vanish is the whole skill."
    ),
    in_the_wild=(
        "Any real effect that gets dismissed as 'just statistics'. Checking properly can "
        "confirm a claim as well as bust one."
    ),
    expect=(Verdict.HOLDS, Verdict.HOLDS),
    real_data=False,
    source="Generated from a fixed seed; contains no real pupils.",
    # Same ruler as the maths case, deliberately. This gap is 21.8 — nearly five times the
    # one that busts — and putting both on the same scale is what lets a player who has
    # played case 1 feel the difference rather than be told it.
    estimate=EstimateSpec(
        prompt="Before you look — how many points apart are the two averages?",
        lo=0.0,
        hi=40.0,
        lo_label="No gap at all",
        hi_label="40 points apart",
        unit=" points",
    ),
)

PARADOX = Case(
    key="paradox",
    title="The paradox",
    claim="men were more likely than women to be admitted to Berkeley in 1973",
    evidence="A pooled rate",
    follow_up="break that down by department",
    table="berkeley_admissions",
    nudge=(
        "**Is that a fair way to check it?** Everyone applied to a particular department, "
        "and some departments admit far more people than others. That rate is every "
        "department added together."
    ),
    repair_label="Ask Genie to break it down by department",
    trick="Simpson's paradox",
    lesson=(
        "Every group inside can lean one way while the total leans the other. It happens "
        "when the groups differ in size and in difficulty: here, women applied in larger "
        "numbers to the departments that admitted almost nobody."
    ),
    in_the_wild=(
        "Hospital survival rates, drug trials, pay gaps — anywhere a total is quoted "
        "across groups that are not alike."
    ),
    expect=(Verdict.HOLDS, Verdict.BUSTED),
    real_data=True,
    source=(
        "Bickel, Hammel & O'Connell (1975), Science 187(4175) — the six largest "
        "departments, not the whole university."
    ),
    # A different ruler and a different unit, because this case returns rates rather than
    # scores: the pooled gap is 14.2 percentage points. Worth estimating precisely because
    # the real answer here is large and the fair answer reverses anyway — being right
    # about the size of the gap and wrong about what it means is the whole of Simpson's
    # paradox, and this is the only mechanic that can make a player do both at once.
    estimate=EstimateSpec(
        prompt="Before you look — how far apart are the two admission rates?",
        lo=0.0,
        hi=40.0,
        lo_label="Identical rates",
        hi_label="40 points apart",
        unit=" pts",
    ),
)

WINDOW = Case(
    key="window",
    title="The window",
    claim="Bulgaria halved its education spending between 1991 and 1996",
    evidence="A window of years",
    follow_up="now show every year in the data, not just the 1990s",
    table="country_indicators",
    nudge=(
        "**Is that a fair way to check it?** Those are two years someone chose. The data "
        "goes back much further, and a fall between two points is not the same thing as "
        "a direction of travel."
    ),
    repair_label="Ask Genie for every year, not just those two",
    trick="The chosen window",
    lesson=(
        "A true fact about the years someone picked, told as if it were the trend. The "
        "fall really happened. It is also the reason spending is higher now than before "
        "it started."
    ),
    in_the_wild=(
        "Crime figures, share prices, temperature records — any claim that starts at a "
        "conveniently chosen year."
    ),
    expect=(Verdict.HOLDS, Verdict.HALF_TRUE),
    real_data=True,
    source="Our World in Data, education spending as a share of GDP, 1870 onwards.",
)

DENOMINATOR = Case(
    key="denominator",
    title="The denominator",
    claim="China is the world's biggest polluter",
    evidence="A total",
    follow_up="show it per person instead",
    table="emissions",
    nudge=(
        "**Is that a fair way to check it?** That is a total, and totals reward being "
        "big. China has more than four times the population of the United States."
    ),
    repair_label="Ask Genie to show it per person",
    trick="The missing denominator",
    lesson=(
        "A total measures how big a place is as much as what it does. Per person asks a "
        "different question, and both answers are true at once — which is exactly why "
        "quoting only one of them works so well."
    ),
    in_the_wild=(
        "Crime counts by city, case numbers by country, spending by department. Ask what "
        "it is being divided by, and whether it should be."
    ),
    expect=(Verdict.HOLDS, Verdict.HALF_TRUE),
    real_data=True,
    source="Our World in Data, CO2 and Greenhouse Gas Emissions (CC BY 4.0).",
)

# Order is the order they are offered in, and it is a teaching order rather than an
# arbitrary one: the spread case is the gentlest introduction to the mechanic; the
# surviving case comes second so the player learns early that "there's a trick" does not
# always pay and the call is real from here on; the paradox follows while attention is
# highest.
DOCKET: tuple[Case, ...] = (SPREAD, READING, PARADOX, WINDOW, DENOMINATOR)

BY_KEY: dict[str, Case] = {case.key: case for case in DOCKET}


def case_for(key: str) -> Case | None:
    return BY_KEY.get(key)
