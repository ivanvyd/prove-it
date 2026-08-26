"""The estimate: make the player place the number before the seal breaks.

The gap this closes was the owner's, verbatim — the player "mostly READS and then CLICKS
ONE OF TWO BUTTONS". A call is a real decision, but it is one bit of input, and one bit
does not feel like playing.

The mechanic is borrowed from a result rather than invented: Kim, Reinecke & Hullman,
*Explaining the Gap: Visualizing One's Predictions Improves Recall and Comprehension of
Data* (CHI 2017, Best Paper). Asking someone to commit to where they think the data lands,
and then showing them their line against the real one, measurably improves what they
remember and understand — because the surprise is theirs rather than the author's.

This app already has the one thing that technique needs and most products cannot offer: a
moment where the query is on screen and the answer genuinely is not. The estimate goes
exactly there.

Three rules keep it honest:

**It only appears where an answer can exist.** The gap is scored against `Analysis.delta`,
which the verdict engine computes arithmetically from Genie's returned rows. Two of the
five cases — the window and the denominator — produce no delta at all, because their
tricks are not a distance between two numbers. Asking for a guess there would be asking
for a number the app cannot check, which is the trap this design most wanted to avoid.

**It cannot be lost.** Landing near the real gap pays; landing far away pays nothing and
costs nothing. The call is still the decision with something at stake, and this is a
second chance to be right rather than a second chance to be punished. The gamification
literature is consistent that mechanics supporting competence beat mechanics applying
pressure, and the docket's whole posture is that a wrong player is never shut out.

**Tolerance is a fraction of the scale, not of the answer.** Judging "within 10% of the
true value" would make a 4.5-point gap essentially unguessable and a 21.8-point gap easy,
which measures the case rather than the player.
"""

from __future__ import annotations

from dataclasses import dataclass

# What a close estimate is worth. Deliberately smaller than a called verdict (100 × stake)
# — this is a supporting mechanic, and a player who guesses numbers well but calls every
# case wrong should not out-score one who reads the evidence right.
DEAD_ON_POINTS = 150
CLOSE_POINTS = 75

# As a fraction of the scale the player was given.
DEAD_ON_BAND = 0.05
CLOSE_BAND = 0.15


@dataclass(frozen=True)
class EstimateSpec:
    """The question, and the ruler it is answered on.

    Authored per case rather than derived from Genie's response, and that is forced rather
    than chosen: before the seal breaks the app holds the SQL and the reasoning but no
    columns and no rows, so there is nothing in the response to build a scale from. The
    curated case is the only thing that knows what is about to be measured.
    """

    prompt: str
    lo: float
    hi: float
    lo_label: str
    hi_label: str
    unit: str = ""
    decimals: int = 1

    def fraction_of(self, value: float) -> float:
        """Where a real value sits on this ruler, clamped to it."""
        if self.hi == self.lo:
            return 0.0
        return min(1.0, max(0.0, (value - self.lo) / (self.hi - self.lo)))


@dataclass(frozen=True)
class EstimateResult:
    """How close the player got, and what it paid."""

    guess: float
    actual: float
    spec: EstimateSpec
    label: str
    points: int

    @property
    def error(self) -> float:
        return abs(self.guess - self.actual)

    @property
    def landed(self) -> bool:
        """Did it pay anything at all? Used to decide whether to celebrate."""
        return self.points > 0


def score_estimate(guess: float, actual: float, spec: EstimateSpec) -> EstimateResult:
    """Settle one estimate. Pure, so the reveal animation and the run cannot disagree.

    `actual` is `Analysis.delta` — a number the verdict engine derived from the rows Genie
    returned, never an opinion and never anything this app chose.
    """
    span = abs(spec.hi - spec.lo) or 1.0
    off = abs(guess - actual) / span
    if off <= DEAD_ON_BAND:
        return EstimateResult(guess, actual, spec, "Dead on", DEAD_ON_POINTS)
    if off <= CLOSE_BAND:
        return EstimateResult(guess, actual, spec, "Close read", CLOSE_POINTS)
    return EstimateResult(guess, actual, spec, "Wide of it", 0)


def verdict_gap(delta: float | None) -> float | None:
    """The distance the player was asked to estimate, from the analysis.

    Unsigned on purpose. `delta` carries a sign — the reading case comes back at −21.8
    because girls score higher — and "how far apart are they" is a question about
    distance, not direction. The direction is what the *call* is for.
    """
    return None if delta is None else abs(delta)
