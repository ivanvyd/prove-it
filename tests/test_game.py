"""The game layer: the call, the stake, and what a run is worth.

Everything here is pure. The score is DERIVED from verdicts the arithmetic judges already
produced; nothing in this module looks at data, at Genie, or at an opinion. That is what
keeps the rule — verdicts are arithmetic, never authority — intact under a scoreboard.

The economy under test:
called it +100 × stake, verdict overturned +250, case closed +150, can't-tell called +200,
docket cleared +500, on a ladder at 0 / 500 / 1200 / 2500.
"""

from __future__ import annotations

import pytest

from prove_it.domain.game import (
    CALL_POINTS,
    CANT_TELL_POINTS,
    CASE_CLOSED_POINTS,
    DOCKET_CLEARED_POINTS,
    OVERTURNED_POINTS,
    RANKS,
    Call,
    Outcome,
    Run,
    Stake,
    calibration,
    next_rank,
    rank_for,
    settle,
    winning_call,
)
from prove_it.domain.verdict import Verdict

HOLDS = Verdict.HOLDS
BUSTED = Verdict.BUSTED
HALF = Verdict.HALF_TRUE
CANT = Verdict.CANT_TELL


# -- which call wins -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("verdict", "winner"),
    [
        (HOLDS, Call.HOLDS_UP),
        (BUSTED, Call.TRICK),
        (HALF, Call.TRICK),
        (CANT, Call.CANT_SAY),
    ],
)
def test_each_verdict_has_exactly_one_winning_call(verdict: Verdict, winner: Call) -> None:
    assert winning_call(verdict) is winner


def test_half_true_counts_as_a_trick() -> None:
    """The number was right and the picture was not; the answer moved. That is the trick
    call paying out, and it matches what the antibody wall already counts as overturned."""
    assert winning_call(HALF) is Call.TRICK


# -- the stake is a multiplier, not a currency ---------------------------------------


def test_the_three_stakes_multiply_by_one_two_three() -> None:
    assert [s.multiplier for s in Stake] == [1, 2, 3]
    assert Stake.CERTAIN.multiplier == 3


def test_every_stake_has_a_label_a_player_can_read() -> None:
    for stake in Stake:
        assert stake.label and stake.label[0].isupper()


# -- settling one case -----------------------------------------------------------------


def test_a_right_call_pays_the_stake_and_the_case() -> None:
    s = settle(Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED, streak_before=0)
    assert s.outcome is Outcome.RIGHT
    # 300 called it, 250 overturned, 150 case closed.
    assert s.points == CALL_POINTS * 3 + OVERTURNED_POINTS + CASE_CLOSED_POINTS == 700
    assert s.streak_after == 1


def test_being_sure_and_wrong_is_the_expensive_kind_of_wrong() -> None:
    """The design's line, made arithmetic: the multiplier cuts both ways."""
    hunch = settle(Call.HOLDS_UP, Stake.HUNCH, HOLDS, BUSTED, streak_before=0)
    certain = settle(Call.HOLDS_UP, Stake.CERTAIN, HOLDS, BUSTED, streak_before=0)
    call_of = lambda s: next(a.points for a in s.awards if "Missed" in a.label)  # noqa: E731
    assert call_of(hunch) == -CALL_POINTS
    assert call_of(certain) == -CALL_POINTS * 3
    assert certain.outcome is Outcome.WRONG
    assert certain.streak_after == 0, "a wrong call ends the streak"


def test_overturning_pays_even_when_the_call_was_wrong() -> None:
    """The lesson landed either way: the player cross-examined and the answer moved."""
    s = settle(Call.HOLDS_UP, Stake.HUNCH, HOLDS, BUSTED, streak_before=0)
    assert any(a.label == "Verdict overturned" for a in s.awards)
    # -100 missed, +250 overturned, +150 closed.
    assert s.points == -CALL_POINTS + OVERTURNED_POINTS + CASE_CLOSED_POINTS


def test_a_case_that_survives_pays_no_overturn() -> None:
    s = settle(Call.HOLDS_UP, Stake.FAIRLY_SURE, HOLDS, HOLDS, streak_before=0)
    assert not any(a.label == "Verdict overturned" for a in s.awards)
    assert s.points == CALL_POINTS * 2 + CASE_CLOSED_POINTS


def test_the_data_not_ruling_scores_nothing_and_keeps_the_streak() -> None:
    """Genie unreachable, or a query that could not be read: nobody is punished for that."""
    s = settle(Call.TRICK, Stake.CERTAIN, CANT, CANT, streak_before=2)
    assert s.outcome is Outcome.VOID
    assert s.points == 0
    assert s.awards == ()
    assert s.streak_after == 2


def test_calling_cant_say_correctly_pays_the_hardest_skill_bonus() -> None:
    """Case zero as a move: the player who saw the refusal coming is paid for it."""
    s = settle(Call.CANT_SAY, Stake.FAIRLY_SURE, CANT, CANT, streak_before=0)
    assert s.outcome is Outcome.RIGHT
    assert any(a.label == "Can't-tell called" for a in s.awards)
    assert s.points == CALL_POINTS * 2 + CANT_TELL_POINTS + CASE_CLOSED_POINTS


def test_calling_cant_say_when_the_data_could_rule_is_wrong() -> None:
    s = settle(Call.CANT_SAY, Stake.HUNCH, HOLDS, HOLDS, streak_before=0)
    assert s.outcome is Outcome.WRONG
    assert not any(a.label == "Can't-tell called" for a in s.awards)


def test_clearing_the_docket_pays_once_at_the_end() -> None:
    without = settle(Call.TRICK, Stake.HUNCH, HOLDS, BUSTED, 0, clears_docket=False)
    with_it = settle(Call.TRICK, Stake.HUNCH, HOLDS, BUSTED, 0, clears_docket=True)
    assert with_it.points - without.points == DOCKET_CLEARED_POINTS


def test_every_award_is_named_so_the_chit_can_show_its_working() -> None:
    """The design's payout chit reads "+100 CALLED IT × 3 CERTAIN = +300", so the awards
    must arrive as labelled lines rather than one opaque number."""
    s = settle(Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED, streak_before=0)
    assert [a.label for a in s.awards] == [
        "Called it × certain",
        "Verdict overturned",
        "Case closed",
    ]
    assert s.points == sum(a.points for a in s.awards)


# -- the run -----------------------------------------------------------------------------


def test_a_run_starts_with_nothing() -> None:
    run = Run()
    assert (run.points, run.streak, run.best_streak, run.cases_called) == (0, 0, 0, 0)


def test_points_never_go_below_zero() -> None:
    """Losing what you do not have is not a debt."""
    run = Run()
    # A certain miss on a case that did not overturn: -300 + 150 = -150.
    run.close("reading", Call.TRICK, Stake.CERTAIN, HOLDS, HOLDS)
    assert run.points == 0


def test_a_run_accumulates_across_cases() -> None:
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)  # +700, streak 1
    run.close("reading", Call.HOLDS_UP, Stake.FAIRLY_SURE, HOLDS, HOLDS)  # +350, streak 2
    assert run.points == 1050
    assert run.streak == 2
    assert run.cases_called == 2


def test_closing_the_same_case_twice_settles_it_once() -> None:
    """Streamlit reruns the receipt on every interaction; the payout must not stack."""
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    assert run.points == 700
    assert run.cases_called == 1


def test_a_void_case_is_recorded_but_not_scored() -> None:
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    run.close("zero", Call.TRICK, Stake.CERTAIN, CANT, CANT)
    assert run.points == 700
    assert run.streak == 1
    assert run.cases_called == 2
    assert run.calls_scored == 1


def test_each_call_remembers_the_score_it_started_from() -> None:
    """The slam counts from before to after; it must not re-derive the floor at zero."""
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    run.close("reading", Call.HOLDS_UP, Stake.HUNCH, HOLDS, HOLDS)
    assert [c.points_before for c in run.calls] == [0, 700]


def test_the_last_case_of_the_docket_clears_it() -> None:
    run = Run()
    for i in range(4):
        run.close(f"c{i}", Call.TRICK, Stake.HUNCH, HOLDS, BUSTED, docket_size=5)
    assert not any(a.label == "Docket cleared" for c in run.calls for a in c.settlement.awards)
    last = run.close("c4", Call.TRICK, Stake.HUNCH, HOLDS, BUSTED, docket_size=5)
    assert any(a.label == "Docket cleared" for a in last.awards)


def test_a_perfect_docket_reaches_the_top_rank() -> None:
    """Five cases, certain and right every time, is what Chief Examiner is for."""
    run = Run()
    for i, (call, first, final) in enumerate(
        [
            (Call.TRICK, HOLDS, BUSTED),
            (Call.HOLDS_UP, HOLDS, HOLDS),
            (Call.TRICK, HOLDS, BUSTED),
            (Call.TRICK, HOLDS, HALF),
            (Call.TRICK, HOLDS, HALF),
        ]
    ):
        run.close(f"c{i}", call, Stake.CERTAIN, first, final, docket_size=5)
    assert run.best_streak == 5
    assert rank_for(run.points).title == RANKS[-1].title


# -- rank ---------------------------------------------------------------------------------


def test_the_ladder_is_the_designs() -> None:
    assert [(r.title, r.floor) for r in RANKS] == [
        ("Rumour Hearer", 0),
        ("Evidence Clerk", 500),
        ("Field Investigator", 1200),
        ("Chief Examiner", 2500),
    ]


def test_ranks_cover_every_score_without_a_gap_and_never_go_down() -> None:
    titles = [rank_for(p).title for p in range(0, 3000, 50)]
    order = [r.title for r in RANKS]
    assert titles[0] == "Rumour Hearer"
    assert titles[-1] == "Chief Examiner"
    assert [order.index(t) for t in titles] == sorted(order.index(t) for t in titles)


def test_the_next_rung_is_named_until_the_top() -> None:
    assert next_rank(0).title == "Evidence Clerk"
    assert next_rank(700).title == "Field Investigator"
    assert next_rank(2500) is None


# -- calibration ------------------------------------------------------------------------


def test_calibration_counts_made_and_right_per_stake() -> None:
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    run.close("reading", Call.TRICK, Stake.CERTAIN, HOLDS, HOLDS)
    run.close("paradox", Call.TRICK, Stake.HUNCH, HOLDS, BUSTED)
    lines = {line.stake: line for line in calibration(run)}
    assert (lines[Stake.CERTAIN].made, lines[Stake.CERTAIN].right) == (2, 1)
    assert (lines[Stake.HUNCH].made, lines[Stake.HUNCH].right) == (1, 1)
    assert Stake.FAIRLY_SURE not in lines, "a stake never used is not a line"


def test_a_void_call_is_not_a_calibration_event() -> None:
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, CANT, CANT)
    assert calibration(run) == []


def test_the_share_strip_is_spoiler_free() -> None:
    """Wordle's rule: the strip says how you did, never which claim was which."""
    run = Run()
    run.close("spread", Call.TRICK, Stake.CERTAIN, HOLDS, BUSTED)
    run.close("reading", Call.HOLDS_UP, Stake.HUNCH, HOLDS, HOLDS)
    run.close("paradox", Call.HOLDS_UP, Stake.FAIRLY_SURE, HOLDS, BUSTED)
    strip = run.share_strip()
    assert "boys" not in strip and "Berkeley" not in strip and "reading" not in strip
    assert strip.count("\n") == 2, "one line per case"
    assert "✓" in strip and "✗" in strip
