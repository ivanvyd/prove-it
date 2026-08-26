"""The live client's wait, made visible.

`start_conversation_and_wait` hid Genie's phases behind a sleep that grows to ten seconds
between polls. The app wants to show them — FETCHING_METADATA, ASKING_AI, EXECUTING_QUERY
— so the client polls itself, once a second, and reports every phase it sees. Nothing
about the seal changes: the rows are still never touched here.

The SDK is faked at the boundary the real client uses: `start_conversation`,
`create_message`, `get_message`, all read out of the installed package.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from prove_it.genie.client import DatabricksGenieClient, GenieFailed

PHASES = ["FETCHING_METADATA", "ASKING_AI", "EXECUTING_QUERY", "COMPLETED"]


def message(status: str, *, with_query: bool = False, message_id: str = "m1") -> SimpleNamespace:
    attachments = []
    if with_query:
        attachments = [
            SimpleNamespace(
                attachment_id="a1",
                text=None,
                query=SimpleNamespace(
                    query="SELECT gender, AVG(maths_score) FROM t GROUP BY gender",
                    description="averages",
                    thoughts=[],
                ),
            )
        ]
    return SimpleNamespace(
        conversation_id="c1",
        message_id=message_id,
        status=SimpleNamespace(value=status),
        attachments=attachments,
    )


class FakeGenieAPI:
    """Hands out one status per poll, then the finished message."""

    def __init__(self, statuses: list[str]) -> None:
        self.statuses = list(statuses)
        self.polls = 0
        self.rows_fetched = 0
        self.started: list[str] = []
        self.continued: list[tuple[str, str]] = []

    def start_conversation(self, space_id: str, content: str, **_: object) -> SimpleNamespace:
        self.started.append(content)
        return SimpleNamespace(response=SimpleNamespace(conversation_id="c1", message_id="m1"))

    def create_message(
        self, space_id: str, conversation_id: str, content: str, **_: object
    ) -> SimpleNamespace:
        self.continued.append((conversation_id, content))
        return SimpleNamespace(response=SimpleNamespace(conversation_id="c1", message_id="m2"))

    def get_message(self, space_id: str, conversation_id: str, message_id: str) -> SimpleNamespace:
        self.polls += 1
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return message(status, with_query=status == "COMPLETED", message_id=message_id)

    def get_message_attachment_query_result(self, **_: object) -> None:
        self.rows_fetched += 1
        raise AssertionError("rows must never be fetched while polling")


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def client(statuses: list[str], **kwargs) -> tuple[DatabricksGenieClient, FakeGenieAPI, FakeClock]:
    api = FakeGenieAPI(statuses)
    clock = FakeClock()
    c = DatabricksGenieClient(
        space_id="space",
        workspace_client=SimpleNamespace(genie=api),
        clock=clock,
        sleep=clock.sleep,
        **kwargs,
    )
    return c, api, clock


def test_every_phase_is_reported_with_the_time_it_was_seen() -> None:
    seen: list[tuple[str, float]] = []
    c, api, _ = client(PHASES)

    turn = c.ask("boys are better at maths", on_status=lambda s, e: seen.append((s, e)))

    assert [s for s, _ in seen] == PHASES
    assert [round(t) for _, t in seen] == [0, 1, 2, 3], "one poll a second, from zero"
    assert turn.timeline == seen, "the turn keeps what the app was shown"
    assert turn.has_query
    assert api.polls == 4


def test_the_rows_are_never_touched_while_waiting() -> None:
    c, api, _ = client(PHASES)
    c.ask("anything")
    assert api.rows_fetched == 0


def test_a_follow_up_polls_the_same_conversation() -> None:
    c, api, _ = client(PHASES + PHASES)
    first = c.ask("claim")
    second = c.follow_up(first, "break it down")
    assert api.continued == [("c1", "break it down")]
    assert second.conversation_id == first.conversation_id
    assert second.message_id != first.message_id


def test_failed_is_an_error_not_a_hang() -> None:
    """The session turns any exception into CAN'T TELL; a FAILED that kept polling
    would hang for the whole timeout instead."""
    c, api, _ = client(["ASKING_AI", "FAILED"])
    with pytest.raises(GenieFailed):
        c.ask("claim")
    assert api.polls == 2


def test_cancelled_is_an_error_too() -> None:
    c, _, _ = client(["CANCELLED"])
    with pytest.raises(GenieFailed):
        c.ask("claim")


def test_the_wait_gives_up_at_the_timeout() -> None:
    """A cold warehouse pushed a real call past five minutes once. The app must come
    back with CAN'T TELL, not sit on a spinner for the proxy's 120s limit to kill it."""
    c, _, clock = client(["PENDING_WAREHOUSE"], timeout_seconds=5)
    with pytest.raises(TimeoutError):
        c.ask("claim")
    assert clock.now - 100.0 >= 5


def test_no_callback_is_fine() -> None:
    c, _, _ = client(PHASES)
    assert c.ask("claim").has_query
