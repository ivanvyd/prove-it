"""Talking to a Genie space.

Every symbol used from `databricks-sdk` here was read out of the installed package
(`databricks/sdk/service/dashboards.py`) rather than recalled:

    GenieAPI.start_conversation(space_id, content)               -> Wait[GenieMessage]
    GenieAPI.create_message(space_id, conversation_id, content)  -> Wait[GenieMessage]
    GenieAPI.get_message(space_id, conversation_id, message_id)  -> GenieMessage
    GenieAPI.get_message_attachment_query_result(space_id, conversation_id,
                                                 message_id, attachment_id)
                                       -> GenieGetMessageQueryResultResponse
    GenieMessage.{status, attachments[].{attachment_id, query, text}}
    MessageStatus.{FETCHING_METADATA, ASKING_AI, EXECUTING_QUERY, COMPLETED, FAILED, ...}

The `_and_wait` helpers exist too, but this client polls `get_message` itself so it can
show Genie's phases as they happen rather than hiding them behind a growing sleep.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from prove_it.domain.verdict import Column, ResultTable
from prove_it.genie.models import ThoughtStep, Turn

if TYPE_CHECKING:  # pragma: no cover - import cost only matters at runtime
    from databricks.sdk.service.dashboards import GenieMessage

# Genie can sit in ASKING_AI or EXECUTING_QUERY for a while on a 2X-Small warehouse. The
# app makes the wait part of the experience, so this is generous — but bounded well under
# the Databricks Apps proxy's hard 120s per-request limit is NOT the goal, because the
# poll loop makes many short requests rather than one long one. It only needs to be long
# enough that a cold start is not mistaken for a failure.
DEFAULT_TIMEOUT_SECONDS = 180.0
POLL_SECONDS = 1.0

# Where the message ends up. Everything else is a phase to show while waiting.
_DONE = "COMPLETED"
_FAILED = ("FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED")

# What the app is told on each poll: (status, seconds since the question was sent).
StatusCallback = Callable[[str, float], None]


class GenieFailed(RuntimeError):
    """Genie reported FAILED or CANCELLED. The session turns this into CAN'T TELL."""


class GenieClient(Protocol):
    """What the app needs from Genie. Narrow on purpose, so it can be faked exactly."""

    def ask(self, question: str, on_status: StatusCallback | None = None) -> Turn:
        """Open a new conversation with a question."""
        ...

    def follow_up(self, turn: Turn, question: str, on_status: StatusCallback | None = None) -> Turn:
        """Continue the conversation the given turn belongs to."""
        ...

    def fetch_result(self, turn: Turn) -> ResultTable:
        """Fetch the rows behind a turn's query. Called only after a prediction."""
        ...


def thought_kind(raw: object) -> str:
    """Normalise a ThoughtType to its bare name.

    The SDK gives an enum whose value is `THOUGHT_TYPE_STEPS`; older payloads and raw
    JSON give the string directly. Both reduce to `STEPS`.
    """
    value = getattr(raw, "value", raw)
    return str(value).removeprefix("THOUGHT_TYPE_").upper()


def turn_from_message(
    message: GenieMessage, question: str, timeline: list[tuple[str, float]] | None = None
) -> Turn:
    """Map an SDK message onto what the app shows.

    Picks the first attachment carrying a query. A message with only a text attachment,
    a clarifying question, or nothing at all maps to a Turn with `has_query` false, which
    the flow routes to CANT_TELL rather than an error.
    """
    attachment_id = sql = description = None
    thoughts: list[ThoughtStep] = []
    text: str | None = None

    for attachment in message.attachments or []:
        if attachment.text and attachment.text.content and text is None:
            text = attachment.text.content
        query = attachment.query
        if query is None or not query.query or attachment_id is not None:
            continue
        attachment_id = attachment.attachment_id
        sql = query.query
        description = query.description
        thoughts = [
            ThoughtStep(thought_kind(t.thought_type), t.content)
            for t in (query.thoughts or [])
            if t.content
        ]

    return Turn(
        conversation_id=message.conversation_id,
        message_id=message.message_id,
        question=question,
        status=getattr(message.status, "value", str(message.status or "COMPLETED")),
        attachment_id=attachment_id,
        sql=sql,
        description=description,
        text=text,
        thoughts=thoughts,
        timeline=timeline or [],
    )


def table_from_statement(response: object) -> ResultTable:
    """Map a statement response onto the rows the verdict engine reads.

    Everything is kept as returned. The engine parses numbers itself so that a cell it
    cannot read becomes CANT_TELL rather than a crash.
    """
    statement = getattr(response, "statement_response", None)
    if statement is None:
        return ResultTable([], [])

    manifest = getattr(statement, "manifest", None)
    schema = getattr(manifest, "schema", None) if manifest else None
    columns = [
        Column(col.name or f"col_{i}", str(getattr(col.type_name, "value", col.type_name) or ""))
        for i, col in enumerate(getattr(schema, "columns", None) or [])
    ]

    result = getattr(statement, "result", None)
    rows = [list(r) for r in (getattr(result, "data_array", None) or [])]
    return ResultTable(columns, rows)


class DatabricksGenieClient:
    """The real client. Authenticates as the app's service principal.

    It polls Genie itself rather than using the SDK's `_and_wait` helpers, because those
    sleep for a growing interval that reaches ten seconds between polls — fine for a
    script, and exactly wrong for a screen that wants to show FETCHING_METADATA turn
    into ASKING_AI turn into EXECUTING_QUERY as it happens. One poll a second, and every
    phase seen goes to `on_status` and onto the turn's timeline.

    Each poll is its own short request, which the Databricks Apps proxy's 120-second
    per-request limit would have required anyway.
    """

    def __init__(
        self,
        space_id: str,
        workspace_client: object | None = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        poll_seconds: float = POLL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if workspace_client is None:
            from databricks.sdk import WorkspaceClient

            workspace_client = WorkspaceClient()
        self._w = workspace_client
        self._space_id = space_id
        self._timeout = timeout_seconds
        self._poll = poll_seconds
        self._clock = clock
        self._sleep = sleep

    def ask(self, question: str, on_status: StatusCallback | None = None) -> Turn:
        started = self._clock()
        wait = self._genie.start_conversation(space_id=self._space_id, content=question)
        return self._poll_to_done(wait.response, question, started, on_status)

    def follow_up(self, turn: Turn, question: str, on_status: StatusCallback | None = None) -> Turn:
        started = self._clock()
        wait = self._genie.create_message(
            space_id=self._space_id, conversation_id=turn.conversation_id, content=question
        )
        return self._poll_to_done(wait.response, question, started, on_status)

    @property
    def _genie(self):  # type: ignore[no-untyped-def]
        return self._w.genie  # type: ignore[attr-defined]

    def _poll_to_done(
        self, opened: object, question: str, started: float, on_status: StatusCallback | None
    ) -> Turn:
        """Poll one message to a terminal state, reporting every phase seen on the way.

        The rows are never fetched here — the whole point of the seal is that they are not
        touched until a call is locked — so this returns a Turn carrying the query and the
        timeline, and nothing from the result set.
        """
        conversation_id = opened.conversation_id  # type: ignore[attr-defined]
        message_id = opened.message_id  # type: ignore[attr-defined]
        timeline: list[tuple[str, float]] = []

        while True:
            message = self._genie.get_message(
                space_id=self._space_id,
                conversation_id=conversation_id,
                message_id=message_id,
            )
            status = getattr(message.status, "value", str(message.status or _DONE))
            elapsed = self._clock() - started
            timeline.append((status, elapsed))
            if on_status is not None:
                on_status(status, elapsed)

            if status == _DONE:
                return turn_from_message(message, question, timeline=timeline)
            if status in _FAILED:
                raise GenieFailed(f"Genie reported {status}")
            if elapsed >= self._timeout:
                raise TimeoutError(f"Genie did not finish within {self._timeout:.0f}s")
            self._sleep(self._poll)

    def fetch_result(self, turn: Turn) -> ResultTable:
        if not turn.attachment_id:
            return ResultTable([], [])
        response = self._w.genie.get_message_attachment_query_result(  # type: ignore[attr-defined]
            space_id=self._space_id,
            conversation_id=turn.conversation_id,
            message_id=turn.message_id,
            attachment_id=turn.attachment_id,
        )
        return table_from_statement(response)
