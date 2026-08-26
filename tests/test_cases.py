"""The docket, and a session driven by one of its cases.

`cases.py` is content, so most of what can go wrong with it is content going stale: a
claim rewritten in the file but never re-probed, an arc that no longer matches what the
engine produces, a case whose data nobody says is real. Those are what these check.

The one structural property worth holding is that a Case never reaches a judge. The
verdict engine dispatches on the shape of the rows and has no idea which case is playing,
which is what lets a claim someone typed themselves be judged by the same arithmetic.
"""

from __future__ import annotations

import pytest

from prove_it.domain.cases import DOCKET, Case, case_for
from prove_it.domain.game import Call, Stake
from prove_it.domain.verdict import Verdict
from prove_it.genie.fake import ScriptedGenieClient
from prove_it.genie.models import Turn
from prove_it.session import Investigation, Stage


def test_the_docket_is_not_empty_and_keys_are_unique() -> None:
    assert len(DOCKET) >= 4
    assert len({c.key for c in DOCKET}) == len(DOCKET)


def test_every_case_can_be_looked_up_by_key() -> None:
    for case in DOCKET:
        assert case_for(case.key) is case
    assert case_for("no such case") is None


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_every_case_is_completely_specified(case: Case) -> None:
    """A half-written case renders a blank card rather than failing loudly."""
    for field_name in ("title", "claim", "follow_up", "table", "trick", "lesson", "in_the_wild"):
        value = getattr(case, field_name)
        assert value and value.strip(), f"{case.key}.{field_name} is empty"
    assert len(case.expect) == 2


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_real_data_is_always_sourced(case: Case) -> None:
    """Every case says where its numbers came from, and synthetic data says so too.

    The docket mixes generated pupils with published research. Which is which must never
    be something a viewer has to infer.
    """
    assert case.source.strip(), f"{case.key} has no source line"
    if not case.real_data:
        # The card prints "Synthetic data ·" ahead of this, so the source itself says how
        # the numbers were made rather than repeating the word — on screen the two ran
        # together as "Synthetic data · Synthetic. Generated from a fixed seed".
        assert "seed" in case.source.lower(), "generated data must say how it was generated"
        assert not case.source.lower().startswith("synthetic"), "the card already says that"


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_the_naive_turn_is_never_the_final_word(case: Case) -> None:
    """Every case must have somewhere to go after the first answer.

    A case whose first query already gives the fair answer has no second beat, and the
    whole app is the second beat.
    """
    assert case.expect[0] is Verdict.HOLDS, (
        f"{case.key} does not appear to confirm its claim first, so there is nothing to overturn"
    )


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_each_case_argues_for_its_own_repair(case: Case) -> None:
    """The reveal screen has to make the case for the follow-up it is about to run.

    Both the argument and the button were hardcoded to the first case's wording, so the
    app asked "an average tells you where a group sits" over a table of admission rates
    and offered a button reading "show the spread too" that would actually have run a
    department split.
    """
    assert case.nudge.strip() and case.repair_label.strip()
    assert case.repair_label.lower().startswith("ask genie")


def test_no_two_cases_share_a_repair_button() -> None:
    """Identical labels would mean at least one case is arguing someone else's point."""
    assert len({c.repair_label for c in DOCKET}) == len(DOCKET)
    assert len({c.nudge for c in DOCKET}) == len(DOCKET)


def test_the_docket_teaches_more_than_one_trick() -> None:
    """Four cases with the same lesson is one case shown four times."""
    assert len({c.trick for c in DOCKET}) == len(DOCKET)


def test_most_cases_turn_but_the_docket_is_not_all_gotcha() -> None:
    """Recorded as a property rather than left to whoever edits the docket next.

    If every case flips, the lesson stops being "check it" and becomes "everything is a
    lie", which the project's own docs warn against. HALF_TRUE cases carry some of that
    weight already: they confirm the number and correct the picture.
    """
    turning = [c for c in DOCKET if c.turns_the_verdict]
    assert turning, "no case changes its verdict, so nothing is being taught"
    half_true = [c for c in DOCKET if c.expect[1] is Verdict.HALF_TRUE]
    assert half_true, "every case is a straight bust; nothing shows a true-but-misleading claim"


# -- a case driving a real session ---------------------------------------------------


def _client(first: Turn, second: Turn, results=None) -> ScriptedGenieClient:
    return ScriptedGenieClient(turns=[first, second], results=results or {})


def _turn(message: str, sql: str) -> Turn:
    return Turn(
        conversation_id="c1",
        message_id=message,
        question="q",
        attachment_id=f"a-{message}",
        sql=sql,
    )


def test_a_case_sends_its_claim_verbatim() -> None:
    """Not through the opening-question wrapper.

    That wrapper asks for "the average for each group", which is right for the case it
    was written for and wrong for a rate, a series and a ranking. The exact wording here
    is also what the probe measured, so rephrasing it in flight ships something untested.
    """
    case = case_for("paradox")
    assert case is not None
    client = _client(_turn("m1", "SELECT 1"), _turn("m2", "SELECT 2"))
    inv = Investigation.open_case(case, client)
    inv.ask_genie()

    assert client.asked == [case.claim]
    assert "average for each group" not in client.asked[0]


def test_a_case_sends_its_own_follow_up() -> None:
    case = case_for("denominator")
    assert case is not None
    client = _client(_turn("m1", "SELECT 1"), _turn("m2", "SELECT 2"))
    inv = Investigation.open_case(case, client)
    inv.ask_genie()
    inv.commit_call(Call.TRICK, Stake.HUNCH)
    inv.repair()

    assert client.asked[-1] == case.follow_up


def test_free_text_still_uses_the_wrapper() -> None:
    """The typed path is unchanged, and its wording was measured too."""
    client = _client(_turn("m1", "SELECT 1"), _turn("m2", "SELECT 2"))
    inv = Investigation.open("boys are better at maths", client)
    inv.ask_genie()

    assert inv.case is None
    assert client.asked[0] != "boys are better at maths"
    assert "average for each group" in client.asked[0]


def test_a_case_investigation_still_seals_the_rows() -> None:
    """The rule the whole product rests on does not get a case-shaped exception."""
    case = case_for("paradox")
    assert case is not None
    client = _client(_turn("m1", "SELECT 1"), _turn("m2", "SELECT 2"))
    inv = Investigation.open_case(case, client)
    inv.ask_genie()

    assert inv.stage is Stage.INSTRUMENT
    assert client.fetched == [], "rows were fetched before a prediction was committed"
