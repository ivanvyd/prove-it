# Prove It: the query is the lesson

*Databricks Community Genie-Powered App Challenge. Track B: Creative Thinking.*

A docket of claims on real, published data. Genie writes the SQL that would test each one.
You see the query and the reasoning, the result stays sealed until you commit a call and a
stake, and then one follow-up in plain English makes Genie rewrite its own query. The verdict
often flips.

**At a glance**

| | |
|---|---|
| The problem | People repeat numbers they cannot interrogate, and a chatbot that answers teaches deference. [More](#the-problem) |
| Who it is for | Children aged 10 to 14 in a classroom, one screen, no pupil accounts. [More](#who-it-is-for) |
| Architecture | Streamlit on Databricks Apps, the Genie Conversation API, one Genie space over four Unity Catalog tables. [More](#architecture) |
| What Genie does | Writes every query, explains its reasoning, holds the rows behind a handle, and rewrites the query mid-conversation. [More](#what-genie-does-here) |
| What you can ask | A docket claim, any rumour you type, and a cross-examination in your own words. [More](#what-you-can-ask-it) |
| How you can check | The build fails on any SQL literal in app code, and both turns of a case carry the same Genie conversation id. [More](#how-genie-powers-it-and-how-you-can-check) |
| Reading the query | Every part of Genie's SQL explains itself on hover or focus, and refuses to summarise what it cannot read honestly. [More](#making-the-query-readable) |
| Accessibility | Measured against WCAG 2.2 AA in a browser: contrast, keyboard, screen reader, target size, reduced motion. [More](#built-to-be-used-by-everyone) |
| Lessons learned | The `thoughts` field beat the answer; making Genie naive was harder than making it correct; verify against what renders. [More](#lessons-learned) |

**Links.** Code: [github.com/ivanvyd/prove-it](https://github.com/ivanvyd/prove-it). Play it
with no account: [prove-it.streamlit.app](https://prove-it.streamlit.app). Demo video:
**<https://www.youtube.com/watch?v=Q47GrG9Gihk>**. The Databricks App itself
runs at [prove-it-7474649736342788.aws.databricksapps.com](https://prove-it-7474649736342788.aws.databricksapps.com)
and needs a workspace identity to open.

## The problem

People repeat things they have heard. Men were more likely to get into Berkeley. Bulgaria
halved its education spending. China is the world's biggest polluter. Each of those is
sourced, published and checkable, and each one falls apart, or changes meaning, the moment
you ask the data a fairer question.

The usual response is a chatbot that answers. Someone who learns to ask a machine and
believe the reply has not learned to think about evidence. They have found a new authority
to defer to.

So Prove It does not answer. It hands you a docket of claims and, for each one, shows you
the query Genie wrote to test it, with the result sealed. Before any number appears you call
it (does this hold up, or is there a trick?) and say how sure you are. Only then do the rows
arrive.

Then the part that teaches. Genie's first query is honest and naive: it answers the question
it was asked, at the level it was asked. You type one follow-up in plain English, "break
that down by department", and Genie rewrites its own query in the same conversation. The
verdict often changes.

Your call is settled against that second verdict. The reveal is the witness's testimony. It
appears to vindicate "it holds up" and to sink "there's a trick", and the cross-examination
decides. That ordering cost nothing to build. The beats already existed; I laid a bet across
them, and that is the difference between watching a lesson and being caught by one.

## Who it is for

Children aged 10 to 14, in a classroom, with a teacher running it from one screen. The app
assumes no statistics background and asks no arithmetic of a pupil. A whole docket fits in a
25-minute lesson, pupils need no accounts, and nobody enters or stores anything personal.
`docs/teacher-one-pager.md` is the lesson plan. The second audience is anyone who has been
handed a confident chart with no way to interrogate it.

## The docket

Five cases, in teaching order. Three run on real, published, citable data. Two share one
synthetic table, for a reason given below.

| Case | The claim | The trick | Verdict before → after |
|---|---|---|---|
| The average | "boys are better at maths" | The hidden spread | Looks true → **Busted** |
| The gap that stays | "girls are better at reading" | The gap that survives | Looks true → **Looks true** |
| The paradox | "men were more likely than women to be admitted to Berkeley in 1973" | Simpson's paradox | Looks true → **Busted** |
| The window | "Bulgaria halved its education spending between 1991 and 1996" | The chosen window | Looks true → **Half true** |
| The denominator | "China is the world's biggest polluter" | The missing denominator | Looks true → **Half true** |

One case has to survive, and the second one does. *The gap that stays* asks the same
objection that busts the case before it (show me the spread) of a claim that answers it. An
earlier docket had no such case, and it taught the opposite of what I intended: when every
claim collapses, "will it hold up?" stops being a question and the takeaway is that
everything is a trick. That is cynicism, and it is cheaper than scepticism. It also made the
call unloseable in one direction, which is a design smell before it is a pedagogical one.

Each card names the shape of the evidence ("two averages", "a pooled rate") and not the
trick. Cards used to name the trick, and that was fine while nothing was at stake in
guessing. Once a call can be lost, a card reading "Simpson's paradox" is a bet that cannot
lose. You are told what kind of number you are about to see, and you still have to decide
whether to trust it, which is the situation every headline puts you in.

## What one case looks like

Take Berkeley, 1973: the most famous worked example in statistics, and real data you can
check against the original paper.

Genie's first query:

```sql
SELECT gender,
       SUM(applicants)          AS applicants,
       SUM(admitted)            AS admitted,
       SUM(admitted) / SUM(applicants) AS admit_rate
FROM workspace.prove_it.berkeley_admissions
GROUP BY gender
```

![The archive after hours: a dark room with a hanging lamp over a wooden desk, and the five
case files lying on it as manila folders, each with its number, its trick and its trap
rating.](screenshots/01-the-archive.png)

Men 44.5%, women 30.4%. Verdict: **looks true**, by a wide margin. Fourteen points is no
rounding error, and this is the table that gets printed.

You call it and stake it, and only then do those rows arrive. **Looks true** appears to have
settled it against anyone who called a trick. Nothing has scored yet, and the screen says
so. Then you cross-examine, in one English sentence with no SQL, and Genie rewrites its own
query in the same conversation:

```sql
SELECT department, gender,
       SUM(applicants) AS applicants,
       SUM(admitted)   AS admitted,
       SUM(admitted) / SUM(applicants) AS admit_rate
FROM workspace.prove_it.berkeley_admissions
GROUP BY department, gender
```

![The sealed board: the case pinned to a corkboard — the claim clipping, Genie's reasoning
on index cards, the SEARCH WARRANT carrying its query, and the result held in a kraft
evidence bag banded SEALED, DO NOT OPEN, carrying Genie's real attachment
handle.](screenshots/02-sealed.png)

Twelve rows instead of two. **Four of the six departments admitted women at a higher rate
than men**: A, B, D and F. Verdict: **busted**.

The total was not lying, and no department was hiding anything. Women applied in far larger
numbers to the departments that admitted almost nobody. Department F took 6% of men and 7%
of women, and 341 women applied to it against 373 men. Department A took 62% of men and 82%
of women, and only 108 women applied, against 825 men. Add the departments together and the
easy ones are dominated by men, so the pooled rate follows them.

That is Simpson's paradox, and it is the shape of most arguments about hospital survival
rates, drug trials and pay gaps.

## The gentlest case, and the one that shows its working

The docket opens on something easier, because you have to learn the mechanic before the
tricks get subtle. "Boys are better at maths", against ~9,700 synthetic pupil records.
Genie's first query groups by gender and takes an average: boys **492.6**, girls **488.1**.
A gap of **4.5**, and it looks decisive.

The follow-up asks for the spread and the group sizes. Boys 492.6 with a spread of **91.7**
across 4,812 pupils; girls 488.1 with a spread of **87.2** across 4,903. Verdict: **busted**.

A 4.5-point gap against a spread near 90 is a standardised difference of **0.05**. The two
distributions sit almost on top of each other, and the average hid it.

That last sentence is the kind of claim this app exists to distrust, so the app draws it
instead of asserting it. After the retrial, both groups appear on one shared axis with a
toggle between where the averages put everyone and where they are: two tidy stacks 4.5
points apart spread into one indistinguishable crowd. The caption reads *about **97%** of
the two groups sit on top of each other*, and the app computes that figure by integrating
the overlap of the two distributions Genie described. Nobody chose it as an adjective.

The drawing says what it is. Those dots are reconstructed from the three numbers Genie
returned (count, average and spread). They are not individual pupil rows, which the app
never requested, and the screen says so underneath. An app that teaches you to distrust a
confident summary cannot pass off invented individuals as a class.

## Four verdicts, and the two that matter most

**Looks true** and **busted** are the obvious pair. The other two earn the product its keep.

**Half true** exists because two of the five cases are not lies. Bulgaria's education
spending did fall by 59% between 1991 and 1996, from 5.43% of GDP to 2.23%. Anyone quoting
that is quoting a fact. It is also 1996. The series runs from 1980 to 2022, and spending
today is **higher than where the story starts**: 3.53% in 1980 against 4.50% in 2022.
Calling that "busted" would be its own dishonesty. The claim is true about the years someone
chose, and told as though it were the direction of travel.

The same goes for China. Ask for the biggest emitters and Genie returns a ranking led by
China at **11,902 Mt**, 2.4 times the United States, the next one down. Ask the follow-up
(*now show it per person instead of the total*) and Genie rewrites the ranking. The new top
ten is **Qatar at 38.84 tonnes**, then Bahrain, then Trinidad and Tobago.

China is not in it. That is the whole case: the country that leads the total by a factor of
two and a half is absent from the ten highest per person, and both rankings are true of the
same table in the same year. The app's own verdict says so, in words the arithmetic produced
rather than any I wrote: *"By the total, China was top. Per person it is Qatar, at 38.84.
Both are true: a total measures how big a place is as much as what it does."*

Quoting one of those rankings and not the other is the entire trick. Answering "busted"
would teach a child to dismiss a fact.

An earlier draft of this article said something more convenient:

> China is 19th per person, below the United States at 14.30.

Those numbers are real and they are in the table, but they are not what the app shows you.
Genie answers "per person" with a top ten, and China is nowhere in it. I had written the
comparison from the data instead of from the product. An app whose entire argument is *check
the claim against what the evidence says* cannot describe itself from memory, so the
correction stays in.

One note on vintage, since the figures above are checkable. They are what
`workspace.prove_it.emissions` holds, loaded from Our World in Data in **August 2026**. OWID
tracks the Global Carbon Project, which revises past years as inventories are restated, and
the source today returns 12,172 Mt for the same year. The case is unaffected, because a
total that measures size stays a total either way. A project about checking figures should
still say which vintage of the source it quotes.

**Can't tell from this data** is the fourth verdict, and the app scores it as a win. Ask
whether children with phones read worse and Genie says there is nothing about phones in the
table, and names the column it would need. Recognising that a claim cannot be tested with
what you have is the harder skill, and the one that transfers furthest.

It is also the honest engineering answer. Genie sometimes returns prose instead of a query,
asks a clarifying question, or cannot answer. Each of those routes to "can't tell" rather
than an error screen, so the product's failure mode is a teaching moment instead of a crash
in front of a class.

## Showing it, rather than asserting it

Writing "the fall was real but was not the trend" and expecting you to take it on faith
would be the move the app spends its runtime arguing against. So the app draws its
arguments, and each drawing is built to be read against the verdict beside it.

Beside the first result, the one that appears to confirm the claim, sits the bar chart a
headline would print, with the axis starting just under the lower value so a small gap
becomes a landslide. Its own label reads `axis starts at 487, not 0`. The trick is performed
in the open, with the caption admitting to it.

![The flip: OVERTURNED struck across the first warrant in red, WARRANT Nº 2 marked BUSTED
beside it with the added department column highlighted, red strings connecting the pinned
exhibits, and the desk below counting up the payout.](screenshots/03-the-flip.png)

After the retrial, the Berkeley case draws a **slopegraph**: six departments, two points
each, men's rate to women's rate. Four of the six lines slope the way the pooled total says
they should not. The picture carries the argument, and the sentence beside it is a caption.

The window case draws the whole series with the chosen years **shaded**. The line runs the
full width, the band sits on 1991–1996, and the line ends above where it started. Both
halves are on screen at once, because a chart of the full series alone would win the
argument by leaving the window out, which is the same trick pointed the other way. The
caption names the real low point, 2.23 in 1996, because the collapse happened.

That chart's axis starts at zero, unlike the headline chart two beats earlier. This one
argues about a trend, and a truncated axis here would be the app playing the trick it had
just finished teaching.

## Making the query readable

The product asks a child to bet on a query before seeing its answer. That is only fair if
they can read the query, and printing it is not the same as making it readable. `AVG` is
close to English. `STDDEV` is not, and it is the function the maths case turns on.

So every part the app can name is a target. Point at it, or tab to it, and a strip beneath
the query says what that part does:

```
STDDEV(`maths_score`)         This works out how spread out maths score is.
`year` IN (1991, 1996)        Keeps only year 1991 and 1996, and nothing in between.
```

The second one is the chosen-window trick, in plain English, before the player sees a
number.

The module that does this reads SQL and never writes any. It matches clauses inside a
string Genie already returned, and the fragments it produces concatenate back to Genie's
query character for character. It also refuses what it cannot read honestly: a CTE or a
window function gets the table name and a plain "read the query itself for this one". An
earlier version described the innermost part of a two-CTE query with total confidence and
got the case backwards, announcing "asks for the biggest year" about a per-person ranking.
A wrong explanation is worse than none here, because the explanation is what the bet gets
placed on.

Every panel also has a Copy button, so a query can go into a notebook or a lesson plan.

## Built to be used by everyone

The audience is ten-year-olds, often on a classroom projector, sometimes on a tablet. That
makes accessibility a design constraint rather than a compliance exercise, and it was
measured in a real browser across all five screens rather than assumed.

Eight colour pairs sat below the WCAG AA floor. The caption telling a visitor the demo is a
recording measured 2.97:1. The sealed evidence bag's own labels measured 3.32:1. Streamlit's
stock info box measured 2.05:1, and it carried the sentence this whole product exists to
deliver. All are above the floor now, and a test computes all fifty-five pairs so a future
repaint cannot undo it unnoticed.

The rest followed the same rule of measuring first. Every explainable part of a query is
reachable by keyboard and announces its note through a polite live region. The redacted
digits on the sealed bag are hidden from assistive technology, because a listener gains
nothing from "black-square black-square" and the label beside them already says the result
is sealed. The page has a real top-level heading, which it did not before. The stake
control's own dot was thirteen pixels; the stakes are 66-pixel coins now, because a child
choosing a stake on a tablet should not be able to mis-tap their own bet. Every animation stops under
`prefers-reduced-motion`.

## Making you place the number

A call is a real decision and it is still one bit of input. So on the cases whose trick is a
*distance*, the sealed screen asks for something harder first: drag to say how far apart you
think the two numbers are. At the reveal, your mark is drawn against the real one on the
same ruler.

I borrowed that from a published result. Kim, Reinecke & Hullman's *Explaining the Gap:
Visualizing One's Predictions Improves Recall and Comprehension of Data* (CHI 2017, Best
Paper) found that committing to where you think the data lands, then seeing your line
against it, improves what you remember and understand, because the surprise belongs to you
rather than to whoever wrote the caption. The technique needs one thing most products cannot
offer, and this one already had it: a moment where the query is on screen and the answer is
not.

![The antibody card, minted when the case closes: ANTIBODY Nº 03, Simpson's paradox, with
the trick, what it does and where it turns up next — the one thing that leaves the room,
over the board it was won on.](screenshots/04-the-antibody.png)

It lands the lesson before anyone argues for it. Someone who believes *boys are better at
maths* puts the gap around 18 points and reads back: **you said 18.0 points, it is 4.5.**
That is the same intuition the truncated axis exploits two beats later, caught in your own
hand first.

Three rules keep it honest. It appears only where an answer can exist: the window and the
denominator produce no gap at all, and a guess the app cannot check is worse than no guess.
It can only earn: a wide mark pays nothing, costs nothing, and prints no line on the payout,
because a nil line reads as a fine for having tried. And the tolerance is a fraction of the
ruler rather than of the answer, or the same skill would score differently depending on
which case you opened.

The follow-up changed for the same reason. It used to be a button the app had already
written. It is now a text box, pre-filled with that wording and editable. Pressing a button
is watching a cross-examination; typing the question is conducting one, and the flip that
follows belongs to you. It costs no extra Genie call, and the app still writes no SQL: your
words are the question, and Genie writes the query.

## Making it cost something

The first version of this app scored your prediction with a function that never read the
data. You picked one of three shapes the result might take, and "correct" meant "you picked
a shape that would falsify the claim", a property of your own answer, checkable without
asking Genie anything. Two of the three buttons always won. It passed its tests and met its
written requirement, and it was a comprehension check wearing a game's clothes.

Nothing in the code looked wrong. There was a prediction, it was scored, a number went up.
Nothing could be lost, and a prediction nobody can lose is a quiz question.

So the call is now settled against the world. You pick one of two calls (three on a claim
you typed yourself) and a stake, and the stake is a **multiplier** rather than a currency
you spend:

| | |
|---|---|
| Called it | **+100 × stake** (Hunch ×1 · Fairly sure ×2 · Certain ×3) |
| Verdict overturned | **+250** |
| Case closed | **+150** |
| Called "the data can't say", and it couldn't | **+200** |
| Docket cleared | **+500** |

Being sure and wrong costs the multiple it would have paid. The stake prices your
confidence. The streak sits on the masthead and the ending leads with your calibration
rather than your score, because Kahoot's own playtesting found the streak a stronger
incentive than the points ([their write-up](https://medium.com/inside-kahoot/experimenting-with-answer-streaks-to-help-make-learning-awesome-3b3357e42595)),
and nothing about this app's players suggests they differ.

Three asymmetries are deliberate. **Overturning pays even when the call was wrong**, because
the overturning still happened and you made it happen by cross-examining. The lesson landed
either way, and charging for a wrong guess about it would punish the behaviour the app is
trying to teach. **A verdict the data cannot reach scores nothing rather than costing
anything**, so a cold warehouse never reads as a punishment. And **nothing is gated**:
points floor at zero, no case locks, and a player who calls every case wrong can still play
every case. The stakes are reputational, what the ending calls you, from Rumour Hearer to
Chief Examiner.

The receipt closes on **calibration** rather than score. *Certain twice, right twice* is a
claim about you that a point total cannot make, and it is the counterweight to a multiplier
that rewards confidence. The shareable strip follows Wordle's rule (how sure you were and
whether it landed, never which claim) so you can post it without spoiling the docket for the
next person.

## What you take away

The app never scores you on whether the claim was true. It scores the call you made about
it, and it ends on a wall of the **tricks** you have met.

> **Simpson's paradox.** Every group inside can lean one way while the total leans the
> other. It happens when the groups differ in size and in difficulty.
> *In the wild: hospital survival rates, drug trials, pay gaps. Anywhere a total is quoted
> across groups that are not alike.*

"Berkeley did not favour men" is a fact worth roughly nothing. "Check whether the total is
pooled across groups that are not alike" is a tool. The wall collects the tools.

## Architecture

```
Prove It (Streamlit on Databricks Apps)
      |  the claim, verbatim, as a question in English
      v
Genie Conversation API   (stateful, multi-turn)
      |
      v
Genie space  ->  SQL warehouse  ->  Unity Catalog
                                     berkeley_admissions  (real, published 1975)
                                     country_indicators   (real, Our World in Data)
                                     emissions            (real, Our World in Data)
                                     student_scores       (synthetic, per-pupil)
```

The app declares the Genie space as a resource in `app.yaml` and runs as its own service
principal. There are no accounts and no persistence beyond the browser session.

One decision shapes everything. A Genie response carries the SQL, the reasoning steps and a
*handle* for the result rows, and the rows come from a **separate** call. So the app takes
the query and the reasoning, puts them on screen, and declines to make the second call until
a call and a stake are in. The sealed panel is the app choosing not to know the answer yet,
and the test suite asserts that no rows are fetched before `commit_call`, down every path,
including refusals and repairs.

You should not have to trust that the seal is real rather than a `display:none` over a
number already in the page. So the sealed screen prints the evidence tag: Genie's attachment
handle, the thing the app is holding and declining to spend. It is a picture of a fact.

## What you can ask it

Two things, both in plain English, and both reach Genie word for word.

**A claim.** Each docket case sends its rumour to Genie as a question — *are boys better at
maths?* — and case Nº 0 takes yours: type any rumour you have heard and the app asks Genie
whether the four tables can test it. Most typed claims end in "can't tell from this data",
which the app scores as a win, with Genie naming the column it would have needed.

**The cross-examination.** After the reveal, the follow-up box comes pre-filled with the
wording that lands the trick — *break that down by department*, *show the spread too, and
how many are in each group* — and it is editable. Your words go into the same Genie
conversation, and Genie rewrites its own query from them. The app turns neither ask into
SQL at any point; Genie writes every query from your words.

## What Genie does here

Each of these is a Genie capability the app depends on, and the app would not work without
it.

- **Writes every query.** The claim goes to the Conversation API as a question in English,
  and the SQL on screen is what Genie returned. The app contains no SQL.
- **Explains its reasoning.** The query attachment carries a `thoughts` array of typed steps
  (understanding, data sourcing, instructions) and a one-line description. The app renders
  them beside the query as "how it got there".
- **Keeps the rows behind a handle.** Genie returns an attachment id, and the rows come from
  a separate `get_message_attachment_query_result` call. The seal is that gap.
- **Holds a conversation.** The follow-up goes to the same conversation, and Genie rewrites
  its own query with the first turn as context. That is the flip.
- **Follows the space's instructions.** The naive first draft every lesson depends on comes
  from the Genie space's instruction text, which the repo keeps in
  `src/prove_it/genie/space.py` and pushes with `scripts/update_space.py`.
- **Reports its phases.** The Conversation API's message statuses (fetching metadata, asking
  the AI, executing the query) light the board in the interrogation room while you wait.
- **Declares its tables.** The app reads the space's table list through the
  `serialized_space` API and builds a docket only out of tables Genie can answer about.

## How Genie powers it, and how you can check

The app contains **no SQL**. Not one statement. Every query on screen was written by Genie,
and `tests/test_no_sql_in_app_code.py` walks the abstract syntax tree of every application
module and fails the build if a SQL literal ever appears.

But an app asserting its own honesty is the move this product exists to argue against.
"Queries written by this app: 0" is a number the app computes about itself, and someone who
has just learned to distrust a confident summary should not be asked to accept one from me.

So the app shows Genie's own identifiers instead. The sealed screen carries the evidence
tag: the attachment handle Genie returned, the one the app holds and does not spend until a
call is in. Each query card carries the conversation and message it came from. The receipt
opens onto the full ids, which you can read against the Genie space's own message history:
the app's record on one side, Genie's on the other.

The best of them costs nothing to produce and settles the question on its own:

```
query v1   conversation 01f19cef42f81e17996b65ef60c957d0
query v2   conversation 01f19cef42f81e17996b65ef60c957d0
```

The same conversation. The follow-up did not open a fresh exchange and re-ask. It continued
the one Genie was already in. That is the difference between a stateful agent and a template
run twice, and it is why Genie is load-bearing here rather than swappable.

The no-SQL rule does real work. The naive first draft that makes every lesson land comes
from the Genie space's instructions rather than from application code, and getting it to
stay naive was most of the engineering. The repair loop exists because Genie is stateful and
multi-turn over governed tables. And the artefact you study, the thing you compare and argue
with, is Genie's generated SQL.

Take Genie out and there is no product left, only a quiz with pre-written questions.

## The data

Three of the five cases are real and citable. `berkeley_admissions` is the six-department
table from Bickel, Hammel & O'Connell, *Science* 187(4175), 1975. `country_indicators` and
`emissions` come from Our World in Data (CC BY 4.0).

One figure had to be checked rather than trusted. The famous version of the Berkeley story
quotes "44% of men and 35% of women", computed over *all* departments: 8,442 men and 4,321
women. The six-department table everyone reproduces pools to **44.5% and 30.4%**. They are
different populations, and a drift test pins all twelve published cells so the article and
the app cannot disagree with the source.

`student_scores` is synthetic, generated from a fixed seed, and contains no real pupils. It
carries two cases, the maths gap that dissolves and the reading gap that does not, and that
pairing is why it has to be per-pupil: both lessons turn on the relationship between a gap
in group means and the spread *within* each group, and open education data is published as
country-level aggregates that cannot express it. Real children's data does not belong in a
Free Edition workspace with no SSO and no support agreement, and designing around that
constraint made the product better.

## Lessons learned

**The `thoughts` field beat the answer.** A Genie query attachment carries a `thoughts`
array of typed reasoning steps (understanding, data sourcing, instructions) alongside the
SQL. Almost every integration prints the answer and throws the rest away. Those steps turned
out to be the most teachable thing in the payload, because they show a beginner what
"interpreting a question" consists of.

**Withholding is a feature.** The instinct is to render everything you receive. Splitting
one response and holding half of it back turned a query tool into a lesson.

**Making Genie naive was harder than making it correct.** The denominator case first came
back with `SUM(co2_per_capita)` summed across 270 years, arithmetic that means nothing. The
fix went into the space instructions, and then over-corrected: Genie started volunteering
per-capita figures in the *first* answer, which destroys the case, because the whole lesson
is that you had to ask. Adding "only when they ask" took it back to a clean naive draft in
three runs out of three. A space's instructions are product surface.

**Verify against the thing that will run.** More than once, a check that did not match
reality passed. A generator that produced the same data in a different order made published
numbers wrong in a quiet second way. A healthy server was read as a working app, when a
browser would have shown the page dying on import in under a second. Offline mode once
replayed *one* recorded conversation for whatever was asked, so opening the Berkeley case
with no workspace showed the admissions claim above `AVG(maths_score) FROM student_scores`.
Three of four cases were wrong that way and every test passed, because nothing asserted that
the query on screen was about the question asked. It does now.

**The sharpest version of that lesson was a colour.** Every visual in this app is mounted
with `st.iframe`, which renders it into a sandboxed iframe. An iframe is a separate
document, so it cannot read the host page's CSS custom properties: inside one,
`var(--rule, #E3E4DE)` resolves to the fallback every time. Each component therefore carried
its own copy of the colours, code that looked palette-aware and was not. When I repainted
the app, the copies stayed behind, and six visuals, including the verdict flip and the
Berkeley slopegraph, went on drawing themselves in the old near-white paper-and-ink while
the page around them was manila and serif. The suite was green, the linter was clean, and
the responsive sweep measured overflow and console errors rather than whether two documents
agreed about what colour they were. The fix deleted a mechanism: the `var()` indirection is
gone from the frames, the palette lives in Python and crosses into each frame by import, and
a test asserts every colour a frame emits is one the palette declares.

**A tiny effect size is worth engineering around.** The maths case only works while the gap
stays negligible. The test suite asserts it: if a change to the generator ever pushes the
standardised difference above 0.2, the tests fail, because at that point the repaired query
would *confirm* the claim and the lesson would invert.

## Try it

Play it in the browser with no account: [prove-it.streamlit.app](https://prove-it.streamlit.app).

Or run it yourself. Every case ships with its real Genie conversation recorded, so the whole
docket runs with no Databricks account:

```
uv venv --python 3.12
uv pip install -e ".[dev]"

PROVE_IT_OFFLINE=1 streamlit run src/prove_it/ui/app.py         # macOS / Linux
$env:PROVE_IT_OFFLINE=1; streamlit run src/prove_it/ui/app.py   # Windows PowerShell
```

Those recordings are two-turn conversations captured against a live Free Edition space by
`scripts/probe_cases.py --record`, using the exact wording the app sends. Setup for a real
workspace, including the notebook that builds the tables and the Genie space instructions,
is in `docs/setup.md`, and the code is at
[github.com/ivanvyd/prove-it](https://github.com/ivanvyd/prove-it).
