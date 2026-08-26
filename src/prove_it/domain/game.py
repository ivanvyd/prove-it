"""The game on top of the verdicts: the call, the stake, and what a run is worth.

Everything here is derived from a `Verdict` the arithmetic judges already reached. Nothing
looks at rows, at Genie, or at anyone's opinion — which is what lets a scoreboard sit on
this product without touching the rule that a verdict is arithmetic, never authority.

The economy:

    CALLED IT              +100 × stake
    VERDICT OVERTURNED     +250
    CASE CLOSED            +150
    CAN'T-TELL CALLED      +200   the hardest skill
    DOCKET CLEARED         +500

and its ladder: RUMOUR HEARER 0 → EVIDENCE CLERK 500 → FIELD INVESTIGATOR 1200 →
CHIEF EXAMINER 2500.

The stake is a MULTIPLIER, not a currency that gets spent: you are betting how sure you
are, and being sure and wrong costs the same multiple it would have paid. That is the
design's "stakes multiply wins and misses in the certainty ledger", and it is the whole
reason a call can be felt. Kahoot's own playtests found the streak outweighed the points.

Duolingo's streak wager is the closest published measurement — +14% Day-7 retention — but
this file used to cite it for *loss aversion*, and that is not what Duolingo said. Their
post attributes the lift to the reward for completing the wager: "learners were more likely
to stick around until the 7th day because that's when they get rewarded". The number was
right and the mechanism was invented, which in an app about checking claims is the one
mistake it cannot afford to make in its own source. What the stake here actually borrows is
the wager *shape* — commit up front, find out later — not a theory of why it works.
The version before this one scored a logical property instead of the world, so two of its
three answers were always right and nothing was ever at stake.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import assert_never

from prove_it.domain.estimate import EstimateResult
from prove_it.domain.verdict import Verdict


class Call(Enum):
    """What the player says will happen when the claim is checked fairly."""

    HOLDS_UP = "It holds up"
    TRICK = "There's a trick"
    # Offered only on a claim the player typed. On the docket every case has been probed
    # to reach a verdict, so "can't say" would be a call with no way to win.
    CANT_SAY = "The data can't say"


class Stake(Enum):
    """How sure. The value is what the call is multiplied by, win or lose."""

    HUNCH = 1
    FAIRLY_SURE = 2
    CERTAIN = 3

    @property
    def multiplier(self) -> int:
        return self.value

    @property
    def label(self) -> str:
        return _STAKE_LABELS[self]


_STAKE_LABELS = {
    Stake.HUNCH: "Hunch",
    Stake.FAIRLY_SURE: "Fairly sure",
    Stake.CERTAIN: "Certain",
}


class Outcome(Enum):
    RIGHT = "right"
    WRONG = "wrong"
    # The data could not rule and the player had not called that. Nobody is punished for
    # a cold warehouse; nothing is scored and the streak stands.
    VOID = "void"


# The design's economy, named so the numbers appear once.
CALL_POINTS = 100
OVERTURNED_POINTS = 250
CASE_CLOSED_POINTS = 150
CANT_TELL_POINTS = 200
DOCKET_CLEARED_POINTS = 500


def winning_call(verdict: Verdict) -> Call:
    """Which call the final verdict pays. Exactly one per verdict, and HALF TRUE pays the
    trick: the number was right and the picture was not, so the answer moved — which is
    also what the antibody wall already counts as overturned."""
    match verdict:
        case Verdict.HOLDS:
            return Call.HOLDS_UP
        case Verdict.BUSTED | Verdict.HALF_TRUE:
            return Call.TRICK
        case Verdict.CANT_TELL:
            return Call.CANT_SAY
        case _:
            assert_never(verdict)


@dataclass(frozen=True)
class Award:
    """One line on the payout chit: what it was for, and what it paid."""

    label: str
    points: int


@dataclass(frozen=True)
class Settlement:
    outcome: Outcome
    awards: tuple[Award, ...]
    streak_after: int

    @property
    def points(self) -> int:
        return sum(a.points for a in self.awards)


def settle(
    call: Call,
    stake: Stake,
    first_verdict: Verdict,
    final_verdict: Verdict,
    streak_before: int,
    *,
    clears_docket: bool = False,
) -> Settlement:
    """Settle one case. Pure, so the slam animation and the run cannot disagree.

    `first_verdict` is the naive one and `final_verdict` the one after cross-examination;
    they differ exactly when the fairer query overturned the answer, which is the moment
    the product exists for and the biggest single award on the board.
    """
    awards: list[Award] = []

    if final_verdict is Verdict.CANT_TELL and call is not Call.CANT_SAY:
        # Genie could not rule and the player had not predicted that. Nothing is scored,
        # nothing is lost, and the streak survives.
        return Settlement(Outcome.VOID, (), streak_before)

    right = call is winning_call(final_verdict)
    staked = CALL_POINTS * stake.multiplier
    if right:
        awards.append(Award(f"Called it × {stake.label.lower()}", staked))
        if call is Call.CANT_SAY:
            # The design gives this its own line: spotting that the data cannot answer is
            # the hardest skill on the docket, and it pays more than a straight call.
            awards.append(Award("Can't-tell called", CANT_TELL_POINTS))
    else:
        awards.append(Award(f"Missed × {stake.label.lower()}", -staked))

    if first_verdict is not final_verdict:
        # Paid whether or not the call was right: the overturning happened, the player
        # made it happen by cross-examining, and the lesson landed either way.
        awards.append(Award("Verdict overturned", OVERTURNED_POINTS))

    awards.append(Award("Case closed", CASE_CLOSED_POINTS))
    if clears_docket:
        awards.append(Award("Docket cleared", DOCKET_CLEARED_POINTS))

    return Settlement(
        Outcome.RIGHT if right else Outcome.WRONG,
        tuple(awards),
        streak_before + 1 if right else 0,
    )


@dataclass(frozen=True)
class CaseCall:
    """One case as it was called, and what it paid."""

    key: str
    call: Call
    stake: Stake
    verdict: Verdict
    settlement: Settlement
    # The score before this case paid out, so a screen can count from there to the total
    # without re-deriving the floor at zero.
    points_before: int = 0


@dataclass
class Run:
    """One session's score. Points never go below zero: a player on nothing who is wrong
    stays on nothing — losing what you do not have is not a debt."""

    calls: list[CaseCall] = field(default_factory=list)
    points: int = 0
    streak: int = 0
    best_streak: int = 0

    def close(
        self,
        key: str,
        call: Call,
        stake: Stake,
        first_verdict: Verdict,
        final_verdict: Verdict,
        *,
        docket_size: int = 0,
        estimate: EstimateResult | None = None,
    ) -> Settlement:
        """Settle a case onto the run. Idempotent per case: Streamlit reruns the receipt on
        every interaction and the payout must not stack.

        `estimate` is the gap the player marked before the seal broke, already scored. It
        arrives here rather than being computed here so `settle` stays a pure function of
        verdicts — the estimate is judged against `Analysis.delta`, which belongs to the
        result rather than to the game.
        """
        for done in self.calls:
            if done.key == key:
                return done.settlement
        clears = docket_size > 0 and len(self.calls) + 1 >= docket_size
        settlement = settle(
            call, stake, first_verdict, final_verdict, self.streak, clears_docket=clears
        )
        if estimate is not None and estimate.points:
            # Appended rather than folded into `settle`, and only when it paid: a nil
            # estimate line on the chit would read as a penalty for having tried.
            settlement = Settlement(
                settlement.outcome,
                settlement.awards + (Award(estimate.label, estimate.points),),
                settlement.streak_after,
            )
        self.calls.append(
            CaseCall(key, call, stake, final_verdict, settlement, points_before=self.points)
        )
        self.points = max(0, self.points + settlement.points)
        self.streak = settlement.streak_after
        self.best_streak = max(self.best_streak, self.streak)
        return settlement

    @property
    def cases_called(self) -> int:
        return len(self.calls)

    @property
    def calls_scored(self) -> int:
        return sum(1 for c in self.calls if c.settlement.outcome is not Outcome.VOID)

    def share_strip(self) -> str:
        """One line per case, spoiler-free: how sure, and whether it landed. Never which
        claim — Wordle's rule, and the reason its grid could be shared at all."""
        marks = {Outcome.RIGHT: "✓", Outcome.WRONG: "✗", Outcome.VOID: "—"}
        return "\n".join(
            f"{'●' * c.stake.multiplier:<3} {marks[c.settlement.outcome]}" for c in self.calls
        )


@dataclass(frozen=True)
class Rank:
    title: str
    floor: int


# The design's ladder, verbatim.
RANKS: tuple[Rank, ...] = (
    Rank("Rumour Hearer", 0),
    Rank("Evidence Clerk", 500),
    Rank("Field Investigator", 1200),
    Rank("Chief Examiner", 2500),
)


def rank_for(points: int) -> Rank:
    current = RANKS[0]
    for rank in RANKS:
        if points >= rank.floor:
            current = rank
    return current


def next_rank(points: int) -> Rank | None:
    """The rung above, or None at the top. The docket screen shows the ladder and how far
    it is to the next title, which is what makes a score feel like progress."""
    for rank in RANKS:
        if points < rank.floor:
            return rank
    return None


@dataclass(frozen=True)
class CalibrationLine:
    stake: Stake
    made: int
    right: int


def calibration(run: Run) -> list[CalibrationLine]:
    """How often each level of confidence was borne out. The line data-literate judges
    look for, and the honest counterweight to a multiplier: "Certain twice, right twice"
    is a claim about the player that the score alone does not make."""
    lines = []
    for stake in Stake:
        scored = [
            c for c in run.calls if c.stake is stake and c.settlement.outcome is not Outcome.VOID
        ]
        if not scored:
            continue
        right = sum(1 for c in scored if c.settlement.outcome is Outcome.RIGHT)
        lines.append(CalibrationLine(stake, len(scored), right))
    return lines
