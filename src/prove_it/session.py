"""The investigation: one claim, from typed rumour to printed receipt.

This module owns the rule the whole product rests on — the result rows are not fetched
until the child has committed to a prediction. Holding Genie's attachment id without
using it is what makes the sealed panel real rather than a UI trick.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from prove_it.domain.cases import Case
from prove_it.domain.claim import clean_claim, opening_question, repair_question
from prove_it.domain.game import Call, Stake, winning_call
from prove_it.domain.verdict import Analysis, ResultTable, Verdict, analyse
from prove_it.genie.client import GenieClient, StatusCallback
from prove_it.genie.models import Turn


class Stage(Enum):
    CLAIM = auto()
    """Waiting for the child to type a rumour."""

    INSTRUMENT = auto()
    """Genie's query and reasoning are on screen. The result is sealed."""

    REVEALED = auto()
    """The prediction is in, the rows are fetched, the naive verdict is showing."""

    REPAIRED = auto()
    """The follow-up ran. Two queries, two verdicts, one diff."""


class StageError(RuntimeError):
    """An action was attempted out of order."""


def cant_tell(reason: str) -> Analysis:
    return Analysis(Verdict.CANT_TELL, reason)


NO_QUERY_REASON = (
    "Genie did not write a query for this one, so there is nothing to check. "
    "That usually means the data cannot answer it."
)

GENIE_UNREACHABLE = (
    "Genie could not be reached just now, so we could not check that one. "
    "It may be busy waking up — try again in a moment."
)


def _unreachable_turn(question: str) -> Turn:
    """Stand in for a turn that never happened.

    A failed call and a refusal are the same thing to a child: no query, nothing to
    reveal. Modelling the failure as a query-less Turn routes it down the CANT_TELL path
    that already exists rather than adding a second, parallel failure path through the
    whole flow.
    """
    return Turn(
        conversation_id="",
        message_id="",
        question=question,
        status="ERROR",
        text=GENIE_UNREACHABLE,
    )


@dataclass
class Investigation:
    """One rumour being checked, start to finish."""

    claim: str
    client: GenieClient
    # Which case from the docket this is, if any. None means someone typed their own
    # rumour, which is a first-class path and not a lesser one.
    case: Case | None = None
    stage: Stage = Stage.CLAIM
    first: Turn | None = None
    second: Turn | None = None
    first_result: ResultTable | None = None
    second_result: ResultTable | None = None
    first_analysis: Analysis | None = None
    second_analysis: Analysis | None = None
    # The call and the stake, locked before any row is fetched. Scored against the FINAL
    # verdict, never the first: the naive reveal is the witness's testimony, and the
    # cross-examination is what settles it.
    call: Call | None = None
    stake: Stake | None = None
    # Where the player put the gap, on the cases that ask. Locked by the same commit as
    # the call, and for the same reason: a number placed after the seal opens is not a
    # prediction. None where the case asked for none, or the player did not mark one.
    guess: float | None = None
    # Did the player rewrite the cross-examination rather than accept the suggested one?
    # Recorded so the receipt can say so — it is the one place the app can tell a player
    # that the flip was their doing, and it should only say it when it is true.
    asked_in_own_words: bool = False
    transcript: list[str] = field(default_factory=list)

    @classmethod
    def open(cls, raw_claim: str, client: GenieClient) -> Investigation:
        return cls(claim=clean_claim(raw_claim), client=client)

    @classmethod
    def open_case(cls, case: Case, client: GenieClient) -> Investigation:
        """Open one of the docket's cases.

        The case's claim is used verbatim rather than passed through `clean_claim` and the
        opening-question wrapper. That wrapper asks for "the average for each group",
        which is right for the case it was written for and wrong for three of the four —
        a rate, a series and a ranking are not averages. More importantly, the exact
        wording here is what `scripts/probe_cases.py` measured three times against live
        Genie, so rephrasing it in flight would be shipping something unmeasured.
        """
        return cls(claim=case.claim, client=client, case=case)

    # -- beat 2 -------------------------------------------------------------

    def ask_genie(self, on_status: StatusCallback | None = None) -> Turn:
        """Send the claim and keep only the query and the reasoning.

        Deliberately does not touch the rows. `first.attachment_id` is held back until
        `commit_call`. `on_status(status, elapsed)` fires on each poll so the app can show
        the interrogation room; the rows are still never fetched here.
        """
        if self.stage is not Stage.CLAIM:
            raise StageError("The claim has already been sent.")
        question = self.case.claim if self.case else opening_question(self.claim)
        self.transcript.append(question)
        try:
            turn = self.client.ask(question, on_status)
        except Exception:  # noqa: BLE001 - every way Genie can fail ends the same way
            # Deliberately broad. A timeout, a missing grant, a cold warehouse and a
            # network blip are all the same event to a child, and none of them may ever
            # reach the screen as a traceback.
            turn = _unreachable_turn(question)
        self.first = turn
        self.stage = Stage.INSTRUMENT
        if not turn.has_query:
            # No query means nothing to seal and nothing to reveal. Go straight to the
            # honest outcome rather than showing an empty panel.
            self.first_analysis = cant_tell(turn.refusal_text or NO_QUERY_REASON)
            self.stage = Stage.REVEALED
        return turn

    # -- beat 3 and 4a ------------------------------------------------------

    def commit_call(self, call: Call, stake: Stake, guess: float | None = None) -> Analysis:
        """Lock the call, the stake and the estimate, then — and only then — fetch rows.

        The rows are the only thing that can settle any of the three, and they are not
        fetched until all of them are locked. That ordering is the product's first rule,
        unchanged from the version where the player predicted a shape instead of an
        outcome.

        `guess` is the mark the player placed on the gap, where the case asked for one.
        It rides in on this call rather than being set separately for exactly the reason
        the call does: a number committed *after* the seal opens is not a prediction, and
        an app that allowed it would be lying about the one thing it teaches.
        """
        if self.stage is not Stage.INSTRUMENT:
            raise StageError("A call can only be made while the result is sealed.")
        if self.first is None:
            raise StageError("Nothing has been asked yet.")
        if call is Call.CANT_SAY and self.case is not None:
            # Every docket case was probed to reach a verdict, so this call could never
            # win there. It is offered on typed claims only, where a refusal is a live
            # possibility and seeing it coming is the skill being rewarded.
            raise StageError(
                "On the docket the data always rules; that call is for your own claim."
            )

        self.call = call
        self.stake = stake
        self.guess = guess
        try:
            result = self.client.fetch_result(self.first)
        except Exception:  # noqa: BLE001 - unreachable rows are a verdict, not a crash
            self.first_analysis = cant_tell(GENIE_UNREACHABLE)
            self.stage = Stage.REVEALED
            return self.first_analysis
        self.first_result = result
        analysis = analyse(result)
        self.first_analysis = analysis
        self.stage = Stage.REVEALED
        return analysis

    # -- beat 4b ------------------------------------------------------------

    @property
    def can_repair(self) -> bool:
        """A repair only makes sense when there is a query to improve on."""
        return self.stage is Stage.REVEALED and self.first is not None and self.first.has_query

    def repair(self, on_status: StatusCallback | None = None, asked: str | None = None) -> Analysis:
        """Ask the same conversation a fairer question and judge the new rows.

        `asked` is the player's own wording, when they changed it. The default — and what
        the box is pre-filled with — is the case's curated follow-up, for the same reason
        its claim is used verbatim: that exact phrasing is what `scripts/probe_cases.py`
        measured three times against live Genie producing the repaired query.

        Letting it be edited is the point, though. The flip is the moment the product
        exists for, and a flip caused by a button the app labelled is the app's move; a
        flip caused by a sentence the player wrote is theirs. It costs no extra Genie
        call, changes no SQL — the app still writes none — and it is the difference
        between watching a cross-examination and conducting one.

        The risk is real and accepted: an edited question may not surface the trick, and
        then the case genuinely does not flip. That is a true outcome rather than a bug,
        and the app already has an honest verdict for it.
        """
        if not self.can_repair:
            raise StageError("There is no query to repair.")
        assert self.first is not None  # guarded by can_repair

        default = self.case.follow_up if self.case else repair_question()
        question = (asked or "").strip() or default
        self.asked_in_own_words = bool(asked and asked.strip() and asked.strip() != default)
        self.transcript.append(question)
        try:
            turn = self.client.follow_up(self.first, question, on_status)
        except Exception:  # noqa: BLE001 - same as the opening turn: degrade, never raise
            turn = _unreachable_turn(question)
        self.second = turn
        if not turn.has_query:
            analysis = cant_tell(turn.refusal_text or NO_QUERY_REASON)
        else:
            try:
                result = self.client.fetch_result(turn)
            except Exception:  # noqa: BLE001 - no rows means CANT_TELL, handled just below
                result = None
            if result is None:
                analysis = cant_tell(GENIE_UNREACHABLE)
            else:
                self.second_result = result
                # The repaired turn is judged against the naive one it is meant to
                # overturn. Only the per-unit judge reads it — a ranking by emissions per
                # person cannot know it has changed anything unless it can see what the
                # ranking by total said — but passing it always keeps the two turns
                # symmetrical rather than making the caller decide which judge will run.
                analysis = analyse(result, previous=self.first_result)
        self.second_analysis = analysis
        self.stage = Stage.REPAIRED
        return analysis

    # -- beat 5 -------------------------------------------------------------

    @property
    def final_analysis(self) -> Analysis | None:
        return self.second_analysis or self.first_analysis

    @property
    def verdict(self) -> Verdict:
        final = self.final_analysis
        return final.verdict if final else Verdict.CANT_TELL

    @property
    def lesson_landed(self) -> bool:
        """True when the repaired query overturned the naive one.

        This is the moment the app exists for, and it is worth naming so the UI can
        make something of it rather than rendering two verdicts side by side and
        leaving the child to notice.
        """
        return (
            self.first_analysis is not None
            and self.second_analysis is not None
            and self.first_analysis.verdict is Verdict.HOLDS
            and self.second_analysis.verdict is Verdict.BUSTED
        )

    @property
    def call_won(self) -> bool | None:
        """Did the call land? None while the case is open, or when the data could not
        rule on a call that did not predict that — nobody is scored on a cold warehouse.

        The chips themselves are settled by `Run.close`, which also knows the streak; this
        is the one-bit answer the screens need before the run is consulted.
        """
        if self.call is None or self.stage is Stage.INSTRUMENT:
            return None
        verdict = self.verdict
        if verdict is Verdict.CANT_TELL and self.call is not Call.CANT_SAY:
            return None
        return self.call is winning_call(verdict)

    @property
    def run_key(self) -> str:
        """What the run settles this case under. A docket case by its key; a typed claim
        by its text — so two different typed claims are two cases and the same one twice
        is one."""
        return self.case.key if self.case else f"claim:{self.claim}"

    @property
    def queries_written_by_genie(self) -> int:
        return sum(1 for t in (self.first, self.second) if t is not None and t.has_query)
