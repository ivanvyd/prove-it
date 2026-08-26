"""Offline mode must serve each case its own conversation.

This file exists because of a specific defect. Offline mode held ONE recorded
conversation and replayed it for whatever was asked, so opening the Berkeley case with
no workspace showed

    men were more likely than women to be admitted to Berkeley in 1973
    SELECT `gender`, AVG(`maths_score`) FROM `workspace`.`prove_it`.`student_scores` …

Three of the four cases were wrong that way. For an app whose entire argument is "read
the query, not the answer", a query belonging to a different question is the worst thing
it can put on screen — it teaches the opposite lesson, convincingly.

Offline is not a developer convenience here either. The deployed app sits behind a
Databricks login that a contest judge has no account for, so a local clone is the only way
most people will ever play the docket.
"""

from __future__ import annotations

import pytest

from prove_it.config import Settings
from prove_it.domain.cases import DOCKET, PARADOX, Case
from prove_it.domain.game import Call, Stake
from prove_it.genie.fake import case_fixture
from prove_it.session import Investigation

OFFLINE = Settings(space_id=None, offline=True, free_text=True, fixture_path=None)


def opened(case: Case) -> Investigation:
    return Investigation.open_case(case, OFFLINE.build_client(case.key))


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_every_case_has_a_recorded_conversation(case: Case) -> None:
    """Recorded by `scripts/probe_cases.py --space-id <id> --record`."""
    assert case_fixture(case.key).is_file(), (
        f"no offline recording for {case.key!r}; run probe_cases.py --record"
    )


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_the_offline_query_is_about_the_case_that_was_opened(case: Case) -> None:
    """The defect, asserted directly: the SQL must name the case's own table."""
    turn = opened(case).ask_genie()

    assert turn.sql, f"{case.key}: offline recording has no query"
    assert case.table in turn.sql.lower(), (
        f"{case.key}: offline query reads {turn.sql[:70]!r}, which is not {case.table}"
    )


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_the_recorded_arc_reaches_the_verdicts_the_case_promises(case: Case) -> None:
    """A recording that does not overturn is a recording of a broken lesson.

    The docket card names the trick before the case is opened, so a case that quietly
    stopped reversing offline would advertise a reversal it cannot deliver.
    """
    investigation = opened(case)
    investigation.ask_genie()

    naive = investigation.commit_call(Call.TRICK, Stake.CERTAIN)
    assert naive.verdict is case.expect[0], (
        f"{case.key}: offline naive verdict {naive.verdict.name}, expected {case.expect[0].name}"
    )

    repaired = investigation.repair()
    assert repaired.verdict is case.expect[1], (
        f"{case.key}: offline repaired verdict {repaired.verdict.name}, "
        f"expected {case.expect[1].name}"
    )


@pytest.mark.parametrize("case", DOCKET, ids=lambda c: c.key)
def test_no_rows_are_read_before_the_prediction(case: Case) -> None:
    """The product's first rule, checked against the recordings rather than the live path.

    The scripted client records what was asked of it, so this is an observation rather
    than an assumption.
    """
    investigation = opened(case)
    client = investigation.client
    investigation.ask_genie()

    assert client.fetched == [], f"{case.key}: rows were fetched while the result was sealed"

    investigation.commit_call(Call.TRICK, Stake.CERTAIN)
    assert client.fetched, f"{case.key}: prediction committed but no rows were ever fetched"


def test_the_conversation_continues_rather_than_restarting() -> None:
    """Both turns must carry one conversation id.

    The receipt shows these side by side as the app's own evidence that the follow-up
    continued Genie's exchange instead of opening a fresh one. A recording that lost that
    would make the app's central provenance claim false while it kept displaying it.
    """
    investigation = opened(PARADOX)
    first = investigation.ask_genie()
    investigation.commit_call(Call.TRICK, Stake.CERTAIN)
    investigation.repair()
    second = investigation.second

    assert first.conversation_id
    assert second is not None
    assert first.conversation_id == second.conversation_id
    assert first.message_id != second.message_id
