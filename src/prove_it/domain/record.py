"""What a player takes away: the tricks they have met.

The screen calls this the antibody wall, and the name is borrowed on purpose. Adaptive
immunity does not keep a copy of the pathogen,
it keeps the signature — and the thing worth leaving with here is not "boys are not better
at maths" but "an average hides how much people differ", which is worth every rumour
shaped like that one.

So a card names the TRICK, not the answer. The verdict is on it because a player should be
able to see that scrutiny sometimes confirms a claim, but the heading is the trick and the
line underneath is where they will meet it again.

The score lives elsewhere. `domain/game.py` owns chips, streak and rank; this wall owns
what was learned. Keeping them apart is deliberate: a card is minted once per trick, a
call is settled once per case, and the two do not agree on what "once" means.

Session-scoped and in memory, like everything else here. Persistence is ruled out, and a
wall that survived the browser would need somewhere to live and someone to own it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from prove_it.domain.cases import Case
from prove_it.domain.verdict import Verdict


@dataclass(frozen=True)
class Antibody:
    """One trick, met once, with what it did when it was met."""

    trick: str
    lesson: str
    in_the_wild: str
    claim: str
    verdict: Verdict

    @property
    def overturned(self) -> bool:
        """Did checking it properly change the answer?"""
        return self.verdict in (Verdict.BUSTED, Verdict.HALF_TRUE)


@dataclass
class Record:
    """Every case closed this session, in the order they were closed."""

    antibodies: list[Antibody] = field(default_factory=list)

    def add(self, case: Case | None, claim: str, verdict: Verdict) -> None:
        """Record a closed case.

        A typed claim has no `Case` and therefore no named trick, so it is recorded under
        the verdict it reached. Dropping it instead would make the wall a record of the
        docket rather than of the session — and the typed path is a first-class entrance,
        not a lesser one.
        """
        if case is not None:
            trick, lesson, wild = case.trick, case.lesson, case.in_the_wild
        elif verdict is Verdict.CANT_TELL:
            trick = "The question the data cannot answer"
            lesson = (
                "No column in the table speaks to this claim. Noticing that is the harder "
                "skill, and it is the one that stops you being convinced by a number that "
                "was never about your question."
            )
            wild = "Any statistic offered as evidence for a claim it does not actually measure."
        else:
            trick = "Your own claim"
            lesson = "You brought this one, and the data had something to say about it."
            wild = "Wherever you first heard it."

        if any(a.trick == trick for a in self.antibodies):
            # One card per trick. Meeting the same trick twice is not a second lesson, and
            # a wall that repeats itself reads as padding.
            return
        self.antibodies.append(
            Antibody(trick=trick, lesson=lesson, in_the_wild=wild, claim=claim, verdict=verdict)
        )

    @property
    def cases_closed(self) -> int:
        return len(self.antibodies)

    @property
    def overturned(self) -> int:
        """How many claims did not survive a fair query."""
        return sum(1 for a in self.antibodies if a.overturned)

    def summary(self) -> str:
        """One sentence for the top of the wall, or an empty string with nothing to say."""
        if not self.antibodies:
            return ""
        # Singular gets its own wording rather than "every one of them" over one case,
        # which read as a plural about a single item on a live screen.
        if self.cases_closed == 1:
            opening = "One case closed."
            middle = (
                " It changed under a fairer query."
                if self.overturned
                else " It survived a fairer query."
            )
            return opening + middle
        opening = f"{self.cases_closed} cases closed."
        if self.overturned == 0:
            middle = " None of them changed under a fairer query."
        elif self.overturned == self.cases_closed:
            middle = " Every one of them changed under a fairer query."
        else:
            middle = f" {self.overturned} of them changed under a fairer query."
        return opening + middle
