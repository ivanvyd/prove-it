# Prove It

A docket of claims on real, published data — tested by reading the query, not the answer.

Built for the [Databricks Community Genie-Powered App Challenge][contest], Track B —
Creative Thinking.

You pick a claim. The app does not answer it. It asks a Genie space to write the SQL that
would *test* the claim, shows only that query and Genie's reasoning, and makes you call it —
*does this hold up, or is there a trick?* — and say how sure you are, before any number
appears. Then one follow-up in plain English — *"break that down by department"* — Genie
rewrites its own query in the same conversation, and the verdict often changes.

![The sealed screen: Genie's query on a ruled sheet, its reasoning beside it, and the result
in a kraft evidence bag banded SEALED — DO NOT OPEN UNTIL A CALL IS
IN.](docs/screenshots/01-sealed.png)

*Genie has written the query and returned a handle for the rows. The app is holding that
handle and declining to spend it — the tag on the bag is the real attachment id.*

Your call is settled against the **second** verdict, not the first. So the reveal is the
witness's testimony rather than the answer: it appears to vindicate "it holds up" and
appears to sink "there's a trick", and the cross-examination is what decides.

**Genie wrote every query in this app, and the build fails if it ever stops.**
`tests/test_no_sql_in_app_code.py` walks the syntax tree of every application module and
rejects a SQL literal. You do not have to take the app's word for it either: each query
carries Genie's own conversation and message ids, and both turns of a case share the **same
conversation id**.

```
query v1   conversation 01f19cef42f81e17996b65ef60c957d0
query v2   conversation 01f19cef42f81e17996b65ef60c957d0
```

The follow-up continued the exchange rather than re-asking it — a stateful agent, evidenced
from a system this app does not own. [How that is enforced, and what else is on
screen](#the-app-writes-no-sql-ever).

## The docket

| Case | The claim | The trick | Verdict before → after |
|---|---|---|---|
| The average | "boys are better at maths" | The hidden spread | Looks true → **Busted** |
| The gap that stays | "girls are better at reading" | The gap that survives | Looks true → **Looks true** |
| The paradox | "men were more likely than women to be admitted to Berkeley in 1973" | Simpson's paradox | Looks true → **Busted** |
| The window | "Bulgaria halved its education spending between 1991 and 1996" | The chosen window | Looks true → **Half true** |
| The denominator | "China is the world's biggest polluter" | The missing denominator | Looks true → **Half true** |

**One case survives, and it has to.** *The gap that stays* is the same objection as *the
average* — show me the spread — asked of a claim that answers it. If every case flipped,
"will it hold up?" would not be a question, and the lesson taught would be the one this
product warns against: that everything is a trick. A docket where nothing survives scrutiny
teaches cynicism, not scepticism.

Three of the five run on real, citable data: the Berkeley table from Bickel, Hammel &
O'Connell (*Science*, 1975), and two Our World in Data series. The other two share one
synthetic table, because their lesson needs per-pupil rows and no open education dataset
publishes those — see [`docs/cases.md`](docs/cases.md) for every figure and its source.

Each card names the **shape of the evidence** — "two averages", "a pooled rate" — not the
trick. It used to name the trick, and that was right when there was nothing to lose; once a
call can be lost, a card reading "Simpson's paradox" is a bet that cannot lose. The trick is
named at the flip, and again on the wall of tricks you have met.

## Four verdicts

**Looks true** and **busted** are the obvious pair. The other two carry the product.

**Half true** exists because two of the five cases are not lies. Bulgaria's spending really did
fall 59% between 1991 and 1996 — and the series runs 1980 to 2022, and spending today is
*higher* than where the story starts. China really is the largest emitter by total CO₂ — and
ask for it per person and the top ten that comes back is led by Qatar, with China nowhere in
it. Both framings are true; quoting one of them is the whole trick, and answering "busted"
would teach people to dismiss a fact.

**Can't tell from this data** is the fourth, and the app scores it as a win. Ask whether kids
with phones read worse and Genie will say there is no column for that. It is also the honest
engineering answer: any Genie response that is prose, a clarifying question, or a refusal
degrades to this rather than to an error screen.

## You place the number before you see it

Picking one of two buttons is a decision, but it is one bit of input, and one bit does not
feel like playing. So on the cases whose trick is a *distance*, the seal asks for something
harder first: drag to say how far apart you think the two numbers are. At the reveal your
mark is drawn against the real one, on the same ruler.

This is borrowed rather than invented. [*Explaining the Gap: Visualizing One's Predictions
Improves Recall and Comprehension of Data*][gap] (Kim, Reinecke & Hullman, CHI 2017, Best
Paper) found that committing to where you think data lands, and then seeing your line
against it, measurably improves what you remember and understand — because the surprise is
yours instead of the author's. This app already had the one thing the technique needs and
almost nothing else offers: a moment where the query is on screen and the answer genuinely
is not.

It lands the lesson before anyone argues for it. A player who believes *boys are better at
maths* puts the gap around 18 points and reads back:

> You said **18.0 points** · it is **4.5 points** — Wide of it

![The estimate ruler at the reveal: a red mark labelled "the data" near the left, the
player's ring far to the right of it, and the line "You said 18.0 points · it is 4.5 points —
Wide of it".](docs/screenshots/04-explaining-the-gap.png)

That is the same intuition the truncated-axis chart exploits two beats later, caught in the
player's own hand first.

Three rules keep it honest. It appears **only where an answer can exist** — the window and
the denominator produce no gap at all, and a guess the app cannot check is worse than no
guess. It **can only earn**: a wide mark pays nothing, costs nothing, and prints no line on
the payout, because a nil line reads as a fine for having tried. And **tolerance is a
fraction of the ruler, not of the answer**, or the same skill would score differently on a
4.5-point gap and a 21.8-point one.

## The query explains itself

Asking a ten-year-old to bet on a query is only fair if they can read it. `AVG(maths_score)`
is close to English; `STDDEV(maths_score)` is not, and it is the function the whole maths
case turns on. So every part the app can name is a target: point at it, or tab to it, and a
strip under the query says what that part does.

```
STDDEV(`maths_score`)   →  This works out how spread out maths score is.
`entity` ILIKE '%Bulgaria%'  →  Keeps only rows where entity is Bulgaria.
`year` IN (1991, 1996)  →  Keeps only year 1991 and 1996 — and nothing in between.
```

That last one is the chosen-window trick, visible in plain English before the player looks
at a single number.

`domain/explain.py` reads the SQL and never writes any: it matches clauses inside a string
Genie already returned, and the fragments it produces concatenate back to Genie's query
character for character. It also **refuses** what it cannot read honestly — a CTE or a
window function gets the table name and a plain "read the query itself for this one", after
an earlier version confidently described the innermost `SELECT` of a two-CTE query and got
the case backwards. A wrong explanation is worse than none, because the explanation is what
the bet gets placed on.

Each panel has a **Copy** button, so the query can be pasted into a notebook, a lesson plan,
or a message to a colleague.

## Built to be used by everyone

Measured against WCAG 2.2 AA in a real browser across all five screens, not asserted:

- **Contrast.** Eight pairs were below the floor and are now above it, including the
  "offline demo" caption at 2.97:1, the sealed bag's own labels at 3.32:1, and Streamlit's
  stock info box at 2.05:1 — that last one on the sentence the product exists to deliver.
  `tests/test_contrast.py` computes all 21 pairs and fails the build if a token drifts.
- **Keyboard.** Every explainable part of a query is focusable and announces its note; the
  estimate ruler takes arrows, Home and End as well as a drag.
- **Screen readers.** The explanation strip is a polite live region, the redacted digits on
  the sealed bag are `aria-hidden` (a listener gains nothing from "black-square
  black-square"), and the page now has a real `h1` and an `h2` per case.
- **Targets.** The stake control's own dot was 13px. The row is now 34px, because a child
  choosing a stake on a tablet should not be able to mis-tap their own bet.
- **Motion.** Every animation — the folder opening, the verdict slam, the query highlight —
  is off under `prefers-reduced-motion`.

## You write the cross-examination

The follow-up used to be a button the app had already written for you. It is now a text box,
pre-filled with that wording and editable. Pressing a button is watching a cross-examination;
typing the question is conducting one, and the flip that follows is yours.

It costs no extra Genie call and the app still writes no SQL — your words are the *question*,
Genie writes the query. Pre-filled rather than blank because that exact phrasing is what
`scripts/probe_cases.py` measured producing the repaired query against live Genie; a blank
box would make every case a coin-flip on wording. Change it and your version may not land the
trick, and if it does not, the verdict honestly will not move.

[gap]: https://dl.acm.org/doi/10.1145/3025453.3025592

## What is at stake

A prediction nobody can lose is a comprehension check. The first version of this app scored
whether you had picked a shape that *would* falsify the claim — a property of your answer,
never of the data — so two of its three buttons always won and nothing was ever at risk.

Now you lock a **call** and a **stake**, and the stake is a multiplier rather than a
currency you spend. Being sure and wrong costs exactly the multiple it would have paid.

| | |
|---|---|
| Called it | **+100 × stake** (Hunch ×1 · Fairly sure ×2 · Certain ×3) |
| Verdict overturned | **+250** — paid whether or not your call was right |
| Case closed | **+150** |
| Called "the data can't say", and it couldn't | **+200** — the hardest skill on the docket |
| Docket cleared | **+500** |

Rumour Hearer → Evidence Clerk (500) → Field Investigator (1200) → Chief Examiner (2500).

Three deliberate asymmetries. **Overturning pays even when you called it wrong**, because
the overturning still happened and you are the one who made it happen — the lesson landed
either way. **A verdict the data cannot reach scores nothing rather than costing you**, so a
cold warehouse never reads as a punishment. And **nothing is ever gated**: points floor at
zero, no case is locked, and a wrong child is never shut out. The stakes are reputational —
what the ending calls you — not punitive.

The receipt closes on calibration rather than score alone: *Certain: 2 of 2 right* is a
claim about the player that the points cannot make, and it is the honest counterweight to a
multiplier. The share strip is Wordle's rule — how sure you were and whether it landed,
never which claim — so it can be pasted anywhere without spoiling the docket.

## The app writes no SQL, ever

Every query on screen came from Genie. That is enforced by a build gate
(`tests/test_no_sql_in_app_code.py`) that walks the AST of every application module and
fails if a SQL literal appears — because it is also the judging criterion worth half the
contest score: remove Genie and there is no product left, only a quiz with pre-written
questions.

**And you don't have to take the app's word for it.** A build gate is invisible to anyone
using the app, and a receipt reading "queries written by this app: 0" is the app marking its
own homework — the exact move this product spends its runtime arguing against. So the app
shows Genie's own identifiers: an evidence tag on the sealed panel (the real attachment
handle it is holding and declining to spend), the conversation and message behind each
query, and full ids on the receipt that read against the Genie space's message history.

The one that settles it costs nothing to produce:

```
query v1   conversation 01f19cef42f81e17996b65ef60c957d0
query v2   conversation 01f19cef42f81e17996b65ef60c957d0
```

Same conversation. The follow-up continued the exchange Genie was already in rather than
opening a new one — a stateful agent, not a template run twice.

## Try it without a Databricks account

This is the path that needs nothing from you but Python — no workspace, no credentials, no
sign-in. It is also how most people will see this running, because a Databricks App has no
anonymous access: the deployed link asks for a workspace identity, and Free Edition provides
no way to grant one to anybody else. The public link in the contest submission is this same
offline build hosted on Streamlit Community Cloud at <https://prove-it.streamlit.app>;
[`docs/setup.md`](docs/setup.md) §7 has the steps.

Needs Python 3.11 or 3.12 and [uv](https://docs.astral.sh/uv/). Without `uv`, substitute
`python -m venv .venv` and `pip install -e .` — `requirements.txt` is there for that too.

```bash
uv venv --python 3.12
uv pip install -e .

# macOS / Linux
PROVE_IT_OFFLINE=1 .venv/bin/python -m streamlit run src/prove_it/ui/app.py

# Windows, PowerShell (what Windows 11 opens by default)
$env:PROVE_IT_OFFLINE=1; .venv\Scripts\python -m streamlit run src/prove_it/ui/app.py

# Windows, cmd.exe
set PROVE_IT_OFFLINE=1 && .venv\Scripts\python -m streamlit run src/prove_it/ui/app.py
```

Add `".[dev]"` instead of `.` if you also want to run the tests.

Every case replays **its own** real two-turn Genie conversation, captured against a live
Free Edition space by `scripts/probe_cases.py --record` using the exact wording the app
sends. `tests/test_offline_fixtures.py` holds that to the standard that matters: the query
shown offline must be about the case that was opened, and the arc must still reach the
verdicts the docket card advertises.

To run it against a real workspace, follow [`docs/setup.md`](docs/setup.md).

## Pointing it at your own data

The docket is not a list someone typed. Point the app at another schema and it builds cases
out of whatever it finds there:

```bash
PROVE_IT_CATALOG=my_catalog     # default: workspace
PROVE_IT_SCHEMA=my_schema       # default: prove_it
PROVE_IT_DISCOVER=1             # default; 0 plays only the five checked cases
```

`domain/discovery.py` matches each table against the four tricks by column *role* — a
measure, a label, a year, a tried/succeeded pair, a per-unit column — reading only the names,
types and comments Unity Catalog reports. It looks inside no column, which is what keeps the
no-SQL gate intact. The docket screen's "Where these cases came from" panel shows the mapping
it chose, which tables it passed over and why, and which cases it dropped to the cap.

**One step the environment variables do not cover.** Genie answers only about the tables its
space declares, so `Settings.readable_tables()` narrows discovery to that list — a case built
on a table outside the space comes back refused. That list is `TABLES` in
[`src/prove_it/genie/space.py`](src/prove_it/genie/space.py), hardcoded to this project's four
tables, and `scripts/update_space.py` pushes it into the space **without reading either
environment variable**. So reusing this on other data means editing `TABLES` (and usually the
`INSTRUCTIONS` beside it, which teach the space to answer a first question plainly), then
running `update_space.py`.

Skip that step and the narrowing filters discovery down to nothing, the docket falls back to
the five curated cases, and every one of them names a table you do not have.

## The argument, in one screen

![The flip: LOOKS TRUE stamped in green, OVERTURNED stamped across it in red at an angle,
BUSTED beside it, and both queries side by side with the added `department` column
highlighted.](docs/screenshots/02-the-flip.png)

*The same claim, a fairer query, and the verdict turning over. Both queries carry the same
conversation id — the follow-up continued the exchange rather than starting a new one.*

Berkeley, pooled and then broken down:

| | Query v1 | Query v2 |
|---|---|---|
| Genie returns | men 44.5%, women 30.4% | the same rates per department |
| Rows | 2 | 12 |
| Verdict | **Looks true** | **Busted** |

Four of the six departments admitted women at a *higher* rate than men. The total was not
lying and no department hid anything — women applied in far larger numbers to the
departments that admitted almost nobody.

And the gentlest case, which opens the docket:

| | Query v1 | Query v2 |
|---|---|---|
| Genie returns | boys 492.6, girls 488.1 | plus counts and spreads near 90 |
| Verdict | **Looks true** | **Busted** |

A **4.5**-point gap against a ~90-point spread is an effect size of **0.05**. Nearly every
pupil in the table scored in the same range, and the average hid it.

Those figures are checked, not asserted. `tests/test_case_data.py` pins all twelve
published cells against the source, and `tests/test_published_numbers.py` reads this file,
the project story and the demo script and fails if the prose stops matching the data. Both
are needed: the first guards the code, and only the second guards what a reader is told.

## Layout

```
docs/requirement.md                what is being built, and every assumption behind it
docs/cases.md                      every case figure, verified, with its source
docs/setup.md                      fresh account -> running app
docs/genie-space-instructions.md   what the space is told, and why it is written that way
notebooks/01_generate_data.py      builds the synthetic table, checks the effect size
scripts/setup_workspace.py         schema, volume, student_scores, country_indicators
scripts/load_cases.py              berkeley_admissions and emissions
scripts/update_space.py            pushes the repo's tables + instructions into the space
scripts/probe_cases.py             the gate: does each case's arc happen against live Genie?
src/prove_it/domain/               verdict engine, cases, the game, the antibody wall,
                                   custody, claims, distributions, SQL diff, and the
                                   plain-English reading of Genie's SQL. Pure, tested.
src/prove_it/genie/                the Conversation API client, a fake that replays it,
                                   and the space's tables + instructions
src/prove_it/session.py            the flow, and the rule that rows stay sealed
src/prove_it/ui/                   the beats, the stylesheet, the shared renderers, and
                                   seven inline visuals mounted into iframes
```

`src/prove_it/genie/space.py` is worth knowing about: it holds the Genie space's table list
and instruction text, because that configuration decides whether every case works and it is
invisible from the code that depends on it. `tests/test_space.py` asserts it still says the
things the cases need.

The interesting rules live in `session.py` and `domain/`, not in the view, so tests can
reach them. `tests/test_app_flow.py` drives the real Streamlit script end to end.

## Development

Activate the venv first — `source .venv/bin/activate` on macOS/Linux,
`.venv\Scripts\activate` on Windows — then:

```bash
python -m ruff check .
python -m ruff format --check .
python -m pytest
```

## Status

Built, tested, and deployed as a Databricks App on Free Edition:
<https://prove-it-7474649736342788.aws.databricksapps.com>. Run `pytest` for the test count
rather than trusting a number written here.

> Free Edition stops an app after 24 hours of idleness, and a Databricks App has no
> anonymous access — a visitor needs a workspace identity. If the link is being shared for
> judging, restart the app first and open one case yourself to absorb the cold-warehouse
> wait. The offline mode above is the path that needs no account at all.

**Every case has been probed against a live Genie space**, which is the gate this project
refuses to build UI past — most recently on 26 Aug 2026, all five cases, GATE PASSED.
Running it writes `probe-runs/case-probe.json`, which is **gitignored** because it can carry
workspace ids: a fresh clone has no raw file, so re-derive the figures by running
`scripts/probe_cases.py` yourself rather than taking them on trust from here. The gate asks
the harder question:
not "did Genie return a query" but "did the first answer come back *naive*, and did the
curated follow-up produce the fairer query that overturns it" — judged by running the real
verdict engine over the real returned rows.

The app has been driven through every beat in a real browser at 375, 768 and 1280; see
`docs/screenshots/` for the captures. That sweep found the masthead
silently eating the rank plate at 375 — document overflow was zero, nothing scrolled, the
reward was simply off-screen — which is why the HUD now sheds the docket counter, then the
streak, and keeps points and rank at every width.

What the sweep could *not* see is worth recording next to it. Every visual is mounted with
`components.html`, which renders it into a sandboxed iframe — a separate document that
cannot read the page's CSS variables. Six of them therefore kept their own copy of the
colours and stayed on the pre-rework palette while the page around them was repainted: the
flip beat, the Berkeley reversal, the window chart, the evidence room, the headline chart
and the interrogation room, all near-white and sans-serif on a manila, serif page. Nothing
caught it — the suite was green and the sweep measured overflow, not whether two documents
agreed what colour they were. `tests/test_frame_palette.py` now asserts every colour a
frame emits is one the palette declares.

**Known limits, stated rather than buried:**

- The deployed app sits behind a Databricks login. There is no anonymous access mode for
  Databricks Apps — only `CAN_USE`/`CAN_MANAGE`, and the viewer must be a user in the same
  account. Anyone without an account should run it offline, which is why the recordings
  above exist.
- The deployed UI has not been re-driven in a browser since the latest deploy; that needs a
  signed-in session. The deployment reports `SUCCEEDED / App started successfully`, which
  confirms the server came up, not that the journey through it still works.
- A cold SQL warehouse can push Genie's first call past the client's 180-second timeout
  (`DEFAULT_TIMEOUT_SECONDS` in `src/prove_it/genie/client.py`). It is a
  first-call-of-the-day effect and every subsequent turn lands in ~20s.

[contest]: https://community.databricks.com/t5/learning-events/databricks-community-contest-genie-powered-app-challenge/ec-p/165825
