# Prove It — a 25-minute lesson

**What it is.** A docket of five claims, three of them real and published. For each one, the
app shows the query an AI wrote to test it, keeps the result hidden until the class commits
to a call, then asks one follow-up question in plain English — and the verdict often
changes.

**What it teaches.** Not five facts. Five *tricks* — the ways a true number is used to
support a false picture. Pupils leave with the tricks, not the answers.

**Ages.** 10–14. No statistics background needed; no arithmetic is required of pupils.

---

## Before the lesson

You need a laptop or tablet and a way to show the screen. **You do not need accounts for
pupils, and pupils do not enter any personal information.** The app stores nothing beyond
the browser session.

The app runs with no Databricks account at all — every case replays a real recorded AI
conversation:

```bash
PROVE_IT_OFFLINE=1 streamlit run src/prove_it/ui/app.py
```

Full setup is in `docs/setup.md`. Run it once before the lesson so the first screen is up
when pupils arrive.

---

## The shape of the lesson

Roughly four minutes per case, plus a wrap. Run it from the front with the class calling
together — **the call is the part that does the work**, so do not skip it to save time.

| Time | Beat | What you do |
|---|---|---|
| 0–2 min | The docket | Read the five claims aloud. Ask: which do you think is true? |
| 2–6 min | Case 1 — the average | The gentlest. Establishes the mechanic. |
| 6–10 min | Case 2 — the gap that stays | The one that survives. Do not skip it — see below. |
| 10–15 min | Case 3 — the paradox | The strongest reversal. Berkeley, 1973. |
| 15–19 min | Case 4 — the window | Introduces "half true". |
| 19–23 min | Case 5 — the denominator | Two true answers at once. |
| 23–25 min | The wall | Read back the tricks the class collected. |

**If you only have ten minutes, run cases 2 and 3** — in that order. Case 3 alone is the
strongest single case in the docket, and running it alone teaches the wrong lesson: that
everything is a trick. Case 2 is the claim that *survives* being cross-examined. A class
that has seen one of each has learned scepticism; a class that has only seen things
collapse has learned cynicism, which is easier and worth much less.

---

## What to say at each beat

**When the query appears.** *"This is the question the computer decided to ask. Before we
look at the answer — is that a fair way to check the claim?"* Let them read the query. They
do not need to understand SQL; they need to see that a choice was made.

**Before the reveal.** The app will not fetch the result until the class commits. Two
things to take: *does this hold up, or is there a trick?*, and *how sure are we?* Take a
show of hands for each. A call nobody voiced is a call nobody owns.

Say out loud what the stake means, because it is the part that makes the call cost
something: **being sure and wrong loses three times what a hunch loses.** Confidence is
being priced, not just recorded.

**At the first verdict.** It will usually say **looks true**. Sit with that. *"So we're
done? That's it?"* Nothing has been scored yet, and the app says so — the call settles after
the cross-examination, not here.

**At the follow-up.** The app asks one more question in ordinary English — "break that down
by department". *"We didn't get new data. We asked the same data a fairer question."*

**At the second verdict.** This is the moment. Ask *why* it changed, before explaining. The
app draws a picture for each case; let them read the picture first.

---

## The four verdicts

- **Looks true** — the data supports it, as asked. One case ends here *after* being
  cross-examined, and that is not a failure of the docket.
- **Busted** — the fairer question overturns it.
- **Half true** — the number is right and the picture is wrong. **This is the important
  one.** Two of the five cases land here, and they are the honest cases: Bulgaria's spending
  really did fall, and China really is the biggest total emitter. Being half true is not a
  softer "busted" — it is a different thing, and the lesson is that a true fact can carry a
  false story.
- **Can't tell from this data** — the app treats this as a **win**, not a failure. The AI is
  instructed to say plainly when the data cannot answer, and to name the column it would
  need. Recognising that you cannot answer is the skill that transfers furthest — it is also
  the best-paying call in the game, and deliberately so.

---

## Being warned is not the same as spotting it

Most classes call case 3 wrong. That is designed, and it is worth naming to them
afterwards.

The docket card tells you the *shape of the evidence* — "a pooled rate", "two averages" —
and not the trick. It used to name the trick, back when there was nothing to lose by
knowing; a card reading "Simpson's paradox" makes the call a bet that cannot lose. Now you
are told exactly what kind of number you are about to be shown and still have to decide
whether it can be trusted, which is the situation every real headline puts you in.

The app scores the call, never the knowledge, and it never scores whether the claim was
true. Nothing is locked, nothing is taken away, and a pupil who calls every case wrong can
still play every case. The stakes are what the ending calls you, not what it stops you
doing.

---

## The tricks they take home

The final screen is a wall of cards, one per trick met:

- **The hidden spread** — an average says where a group sits, not how much people inside it
  differ. *In the wild: any headline comparing two groups by their average.*
- **The gap that survives** — the same objection, asked of a claim that answers it. Not
  every gap dissolves when you look harder. *In the wild: any real effect dismissed as
  "just statistics".*
- **Simpson's paradox** — every group inside can lean one way while the total leans the
  other. *In the wild: hospital survival rates, drug trials, pay gaps.*
- **The chosen window** — a true fact about the years someone picked, told as the trend.
  *In the wild: crime figures, share prices, temperature records.*
- **The missing denominator** — a total measures how big a place is as much as what it does.
  *In the wild: crime counts by city, case numbers by country.*

**Ask them to bring one back next lesson.** A headline, an advert, something someone said.
The transfer is the whole objective.

---

## The score, if you want it

The app keeps one: a call pays 100 points times how sure you were, overturning a verdict
pays 250, closing a case 150, and clearing the docket 500. The titles run Rumour Hearer →
Evidence Clerk → Field Investigator → Chief Examiner.

Two things about it are worth a sentence to the class. **Overturning pays even when the call
was wrong** — the point is that the class made the reversal happen, not that it guessed.
And the receipt ends on *calibration* rather than the score: "certain twice, right twice"
is a different claim from "1,050 points", and it is the one worth being proud of.

You can also ignore all of it and run the lesson on the calls alone. Nothing gates on
points.

---

## Bring your own claim

"Case zero" lets a pupil type something they have heard. Expect most typed claims to come
back **can't tell** — the tables cover admissions, emissions, education spending and a set
of test scores, and nothing else. That is the honest outcome and worth showing at least
once, so the class sees the app decline rather than invent. It is also the only place the
third call, *"the data can't say"*, is offered: on the docket every case has been checked
to a verdict, so it would be a button that could only lose.

---

## Curriculum links

- **Mathematics / statistics** — averages and spread, rates versus counts, weighted
  aggregates, reading a time series.
- **Citizenship / media literacy** — evaluating sources, recognising selective quotation.
- **Computing** — what a database query is; what an AI system does and does not decide.

---

## Two things worth telling the class

**The app never answers the question.** It shows the working and makes you commit first.
That is a deliberate design choice, and it is worth naming: a machine that hands you answers
trains you to trust machines.

**One dataset is invented, and the app says so.** The pupil scores are generated, contain no
real children, and are labelled as synthetic on the card — two of the five cases use them,
because their lesson needs per-pupil rows and no open education dataset publishes those. The
other three cases are real, published and cited: Berkeley's 1973 admissions figures and two
Our World in Data series. Sources are on every card.
