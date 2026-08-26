"""The estimate: scoring, honesty, and where it is allowed to appear.

Written before the UI that uses it, because the rules that matter here are arithmetic —
what a close guess is worth, what a wild one costs, and which cases can be asked at all —
and none of them need a browser to check.
"""

from __future__ import annotations

import pytest

from prove_it.domain.cases import DOCKET, case_for
from prove_it.domain.estimate import (
    CLOSE_POINTS,
    DEAD_ON_POINTS,
    EstimateSpec,
    score_estimate,
    verdict_gap,
)

SPEC = EstimateSpec(prompt="how far apart?", lo=0.0, hi=40.0, lo_label="none", hi_label="huge")


# -- scoring -------------------------------------------------------------------------


def test_an_exact_guess_is_dead_on() -> None:
    result = score_estimate(4.5, 4.5, SPEC)
    assert result.label == "Dead on"
    assert result.points == DEAD_ON_POINTS
    assert result.error == 0


def test_a_guess_just_inside_the_tight_band_is_still_dead_on() -> None:
    """5% of a 40-point scale is 2 points."""
    assert score_estimate(6.4, 4.5, SPEC).label == "Dead on"


def test_a_guess_just_outside_the_tight_band_drops_to_close() -> None:
    assert score_estimate(6.6, 4.5, SPEC).label == "Close read"
    assert score_estimate(6.6, 4.5, SPEC).points == CLOSE_POINTS


def test_a_wild_guess_pays_nothing_and_costs_nothing() -> None:
    """The whole posture of the docket: a wrong player is never shut out or fined.

    The call is the thing with something at stake. This is a second chance to be right,
    not a second way to lose.
    """
    result = score_estimate(38.0, 4.5, SPEC)
    assert result.points == 0, "an estimate must never go negative"
    assert result.label == "Wide of it"
    assert result.landed is False


def test_being_wrong_in_either_direction_scores_the_same() -> None:
    """Over- and under-shooting by the same distance are the same size of error."""
    assert score_estimate(4.5 + 5, 4.5, SPEC).points == score_estimate(4.5 - 5, 4.5, SPEC).points


def test_the_estimate_is_worth_less_than_reading_the_evidence_right() -> None:
    """A player who guesses numbers well but calls every verdict wrong must not out-score
    one who reads the evidence correctly. Guards the balance, not the arithmetic."""
    from prove_it.domain.game import CALL_POINTS, Stake

    assert CALL_POINTS * Stake.CERTAIN.multiplier > DEAD_ON_POINTS


# -- tolerance is a fraction of the ruler, not of the answer --------------------------


def test_tolerance_scales_with_the_ruler_not_the_true_value() -> None:
    """Judging "within 10% of the true value" would make a 4.5-point gap nearly
    unguessable and a 21.8-point gap easy — measuring the case rather than the player.

    Same absolute error, same scale, same verdict, whatever the answer happens to be.
    """
    small = score_estimate(4.5 + 1.6, 4.5, SPEC)
    large = score_estimate(21.8 + 1.6, 21.8, SPEC)
    assert small.label == large.label == "Dead on"


def test_a_degenerate_ruler_does_not_divide_by_zero() -> None:
    flat = EstimateSpec(prompt="", lo=5.0, hi=5.0, lo_label="", hi_label="")
    assert score_estimate(5.0, 5.0, flat).points == DEAD_ON_POINTS


def test_a_real_value_maps_onto_the_ruler_and_clamps_to_it() -> None:
    assert SPEC.fraction_of(20.0) == pytest.approx(0.5)
    assert SPEC.fraction_of(0.0) == 0.0
    assert SPEC.fraction_of(999.0) == 1.0, "a value off the end must not draw off the end"
    assert SPEC.fraction_of(-999.0) == 0.0


# -- the gap the player is asked for --------------------------------------------------


def test_the_gap_is_a_distance_and_carries_no_direction() -> None:
    """`Analysis.delta` is signed — the reading case comes back at −21.8 because girls
    score higher. "How far apart are they" is a question about distance; the direction is
    what the *call* is for, and asking for it twice would be asking the same question."""
    assert verdict_gap(-21.8) == pytest.approx(21.8)
    assert verdict_gap(4.5) == pytest.approx(4.5)


def test_no_gap_to_estimate_when_the_analysis_produced_none() -> None:
    assert verdict_gap(None) is None


# -- where it may appear --------------------------------------------------------------


def test_only_cases_whose_trick_is_a_distance_ask_for_an_estimate() -> None:
    """The window and the denominator produce no `delta` at all — their tricks are a
    chosen span of years and a missing denominator, neither of which is a distance
    between two numbers. Asking there would be asking for a number the app cannot check,
    which is worse than not asking."""
    asked = {c.key for c in DOCKET if c.estimate is not None}
    assert asked == {"spread", "reading", "paradox"}


@pytest.mark.parametrize("key", ["spread", "reading", "paradox"])
def test_every_asked_case_puts_its_real_answer_on_the_ruler(key: str) -> None:
    """A scale the true value falls off is a question with no right answer on it."""
    case = case_for(key)
    assert case is not None and case.estimate is not None
    truth = {"spread": 4.5, "reading": 21.8, "paradox": 14.16}[key]
    spec = case.estimate
    assert spec.lo < truth < spec.hi, f"{key}: {truth} is not inside {spec.lo}..{spec.hi}"
    # And not so close to an end that the band is clipped and the question is trivial.
    assert 0.02 < spec.fraction_of(truth) < 0.98


def test_the_two_score_cases_share_a_ruler_so_the_difference_can_be_felt() -> None:
    """4.5 and 21.8 are the same measurement on the same table. Putting them on one scale
    is what lets a player who has played the maths case *feel* that the reading gap is
    nearly five times bigger, rather than be told so."""
    spread, reading = case_for("spread"), case_for("reading")
    assert spread is not None and reading is not None
    assert spread.estimate is not None and reading.estimate is not None
    assert (spread.estimate.lo, spread.estimate.hi) == (
        reading.estimate.lo,
        reading.estimate.hi,
    )
