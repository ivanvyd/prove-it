"""The session record and the antibody wall.

The wall is what a player leaves with, so the property that matters is that it records
tricks rather than answers — and that it stays honest about a session where nothing was
overturned, which is the case the app most wants to be able to show.

Chips, streak and calibration are not here. They belong to the run (`domain/game.py`),
which settles once per case; the wall mints once per trick, and the two must not be one
object pretending to count both.
"""

from __future__ import annotations

import pytest

from prove_it.domain.cases import DENOMINATOR, PARADOX, READING, SPREAD
from prove_it.domain.record import Record
from prove_it.domain.verdict import Verdict


def test_a_closed_case_becomes_a_card_naming_the_trick() -> None:
    """Not the answer. "Simpson's paradox" transfers; "Berkeley did not favour men" does
    not."""
    record = Record()
    record.add(PARADOX, PARADOX.claim, Verdict.BUSTED)

    (card,) = record.antibodies
    assert card.trick == "Simpson's paradox"
    assert card.lesson == PARADOX.lesson
    assert card.in_the_wild == PARADOX.in_the_wild
    assert card.verdict is Verdict.BUSTED


def test_the_same_trick_is_not_recorded_twice() -> None:
    """Meeting a trick again is not a second lesson, and a repeating wall reads as padding."""
    record = Record()
    record.add(SPREAD, SPREAD.claim, Verdict.BUSTED)
    record.add(SPREAD, "a different claim of the same shape", Verdict.BUSTED)
    assert record.cases_closed == 1


def test_different_tricks_both_land() -> None:
    record = Record()
    record.add(SPREAD, SPREAD.claim, Verdict.BUSTED)
    record.add(PARADOX, PARADOX.claim, Verdict.BUSTED)
    record.add(DENOMINATOR, DENOMINATOR.claim, Verdict.HALF_TRUE)
    assert record.cases_closed == 3
    assert [a.trick for a in record.antibodies] == [
        SPREAD.trick,
        PARADOX.trick,
        DENOMINATOR.trick,
    ]


def test_the_surviving_case_earns_a_card_of_its_own() -> None:
    """The gap that stays is a lesson, not the absence of one. Without a card for it the
    wall would say that only tricks are worth remembering."""
    record = Record()
    record.add(READING, READING.claim, Verdict.HOLDS)

    (card,) = record.antibodies
    assert card.trick == READING.trick
    assert not card.overturned


# -- the typed path is first-class ---------------------------------------------------


def test_a_typed_claim_that_cannot_be_answered_still_earns_a_card() -> None:
    """CANT_TELL is celebrated, so it cannot be the one outcome the wall forgets."""
    record = Record()
    record.add(None, "do kids with phones read worse", Verdict.CANT_TELL)

    (card,) = record.antibodies
    assert "cannot answer" in card.trick
    assert "harder skill" in card.lesson
    assert card.verdict is Verdict.CANT_TELL


def test_a_typed_claim_that_reached_a_verdict_is_recorded_under_its_own_name() -> None:
    record = Record()
    record.add(None, "my own rumour", Verdict.BUSTED)
    assert record.antibodies[0].trick == "Your own claim"


# -- what the wall says --------------------------------------------------------------


def test_nothing_closed_says_nothing() -> None:
    assert Record().summary() == ""


def test_a_single_case_is_not_pluralised() -> None:
    record = Record()
    record.add(PARADOX, PARADOX.claim, Verdict.BUSTED)
    assert record.summary().startswith("One case closed.")


def test_a_session_where_nothing_was_overturned_says_so() -> None:
    """The honest outcome the app must be able to show.

    If the wall could only report overturned claims it would be teaching that everything
    is a trick, which is the failure mode the docket's surviving case exists to prevent.
    """
    record = Record()
    record.add(PARADOX, PARADOX.claim, Verdict.HOLDS)
    record.add(SPREAD, SPREAD.claim, Verdict.HOLDS)
    assert "None of them changed" in record.summary()


def test_one_case_is_never_described_as_a_plural() -> None:
    """ "One case closed. Every one of them changed" reached a live screen."""
    overturned = Record()
    overturned.add(PARADOX, PARADOX.claim, Verdict.BUSTED)
    assert "It changed under a fairer query." in overturned.summary()
    assert "them" not in overturned.summary()

    survived = Record()
    survived.add(PARADOX, PARADOX.claim, Verdict.HOLDS)
    assert "It survived a fairer query." in survived.summary()
    assert "them" not in survived.summary()


def test_a_session_where_everything_was_overturned_says_that_too() -> None:
    record = Record()
    record.add(SPREAD, SPREAD.claim, Verdict.BUSTED)
    record.add(DENOMINATOR, DENOMINATOR.claim, Verdict.HALF_TRUE)
    assert "Every one of them changed" in record.summary()


def test_the_mixed_case_counts_rather_than_generalises() -> None:
    record = Record()
    record.add(SPREAD, SPREAD.claim, Verdict.BUSTED)
    record.add(PARADOX, PARADOX.claim, Verdict.HOLDS)
    assert "1 of them changed" in record.summary()


def test_half_true_counts_as_a_change() -> None:
    """The number was right and the picture was not, which is still the answer moving."""
    record = Record()
    record.add(DENOMINATOR, DENOMINATOR.claim, Verdict.HALF_TRUE)
    assert record.overturned == 1


def test_the_wall_no_longer_claims_to_keep_score() -> None:
    """Calibration moved to the run. A summary that still said "you called N of M right"
    would be a second scoreboard, and the two would disagree on what a case is."""
    record = Record()
    record.add(SPREAD, SPREAD.claim, Verdict.BUSTED)
    assert "called" not in record.summary()
    assert not hasattr(record, "predictions_made")


@pytest.mark.parametrize("verdict", list(Verdict))
def test_every_verdict_can_be_recorded(verdict: Verdict) -> None:
    """A verdict the wall cannot express would crash at the end of a session."""
    record = Record()
    record.add(SPREAD, SPREAD.claim, verdict)
    assert record.cases_closed == 1
    assert record.summary()
