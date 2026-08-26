# Demo video — shot list and script

> **Voice and avatar are out of scope** (Ivan, 2026-08-22). The demo ships as a silent cut
> with a burned-in caption track, condensed from the narration below. The narration is kept
> verbatim rather than deleted: it is the source the captions were written from, and it is
> what a voice pass would record if the decision is revisited. Beat lengths are still sized
> to it, so adding voice later needs a re-cut, not a re-shoot.

> **Rewritten 2026-08-26 for the game rework.** The previous script described a product that
> no longer exists — three prediction buttons, no stake, no score, a spinner where the
> interrogation room now is, and the pre-rework palette. Any existing cut is unshippable
> against the current app.

Target **4:05**. The contest sets no length limit — it asks for "a demo (video or
walkthrough)" — so the ceiling here is attention, not a rule. Short demos get watched to the
end; long ones get scrubbed.

Scoring is 40 points: **20 for "Genie at the Core"**, 10 for track execution, 10 for app
experience. That ratio should decide every cut. The custody segment near the end is the only
part of this video that speaks to the twenty-pointer with *evidence* rather than assertion —
it is the last thing to cut, not the first.

**The centrepiece is Berkeley**, not the synthetic maths case. It is real, published,
checkable against a 1975 paper, and the reversal is genuinely surprising to people who have
never seen it. A demo built on invented data spends its credibility in the first ten seconds.

If a take runs long, cut in this order: the evidence-room half of the case-1 cutaway, down
to the toggle and the 97% line; then the window case, down to the shaded-band chart with no
narration; then the axis aside. Do **not** cut the cold open, the silence on the call
screen, the slam, the surviving case, or the side-by-side conversation ids.

**Record live.** Offline mode puts a banner on screen saying it is a recording, and that
banner sitting next to a chain-of-custody claim undercuts it. Warm the SQL warehouse with a
throwaway query first — a cold warehouse pushed the first call past the client's 180-second
timeout during the 2026-08-22 probe.

**Do not cut the wait to nothing any more.** The old script treated Genie's ~20s turn as
dead air to be edited out. It is now the interrogation room: a case clock counting up and a
board of the phases Genie actually moves through, each light coming on as its real status
arrives. Hold it for about two seconds, then cut — long enough to read as *live machinery*,
short enough not to be a wait.

Browser at 1280×800, zoom 110%, no bookmarks bar. Streamlit's own header is hidden, so the
frame is all app. The SQL has to be readable on a phone.

**Driving the verdict slam.** It is a pure function of elapsed milliseconds and exposes
`window.__seek(t)` (`src/prove_it/ui/verdict_slam.py:306`), so the recorder steps it frame by
frame and gets an identical picture every take. Never film it by waiting for autoplay; the
first seek stops the loop, and a sought frame is reproducible where a captured one is not.

**The interrogation room is not seekable, and cannot easily be.** It has no `__seek`: its
clock reads `Date.now() - startedAt` from an epoch passed in as a prop, because Streamlit
remounts the component on every poll and anything Python drove would restart from zero and
strobe. Capture it live, in real time — which is what the "hold about two seconds, then cut"
instruction below already assumes.

---

## 0:00–0:10 — Cold open. The outcome, with no context at all.

**On screen:** the flip beat, mid-slam. `LOOKS TRUE` on the left. The **Objection** bar
sliding in with the real follow-up on it. The rewritten query's new column lighting up. A
900ms freeze. Then `BUSTED` stamping down at an angle with the overshoot, the panel shaking,
`OVERTURNED` landing on top of it, and the points counting up from 0.

No narration. No title card. No logo.

This is the whole product in ten seconds, and it is real UI rather than a motion graphic —
that is the point of opening with it. A viewer who scrubs away after fifteen seconds has
still seen the thing the app is for.

Cut hard to the docket.

## 0:10–0:24 — The docket

**On screen:** five manila case folders on a dark desk. Navy masthead across the top with
the **CASE FILES** plate.

> "Five things people actually say. Every one of them is sourced, published and checkable.
> This app will not tell you whether any of them is true."

Each card's eyebrow names the **shape of the evidence** — *two averages*, *a pooled rate* —
not the trick. Worth a beat of cursor, because it is a deliberate design decision and a
sharp one:

> "It tells you what kind of number you are about to be shown. Not what is wrong with it."

Hold long enough to read two of the claims. Cursor rests on **"men were more likely than
women to be admitted to Berkeley in 1973"**, then clicks *Open case 3 — The paradox*.

## 0:24–0:52 — The query, the wait, and the seal

**On screen:** the interrogation room. Case clock running, phase lights coming on —
*fetching metadata*, *asking the model*, *writing the query*, *sealed*.

> "That is not a loading spinner. Those are the states Genie is actually reporting, as it
> reports them."

Two seconds, then cut to the arrived query.

**On screen:** Genie's first query on a ruled sheet with a red margin. Let the SQL land
before saying anything. Then the kraft evidence bag below it, torn at the top, with a red
diagonal band reading **SEALED — DO NOT OPEN UNTIL A CALL IS IN**.

> "Genie wrote this query to test the claim. Not the answer to it — the query. And the
> result is sealed."
>
> "On the right is how Genie got there: how it read the question, which table it went to,
> what it decided to group by. That reasoning is in the API response and almost every
> integration throws it away."

Cursor traces the `GROUP BY gender` line, then the evidence tag on the bag.

> "That tag is real. It is the handle Genie gave us for the rows — the one the app is
> holding and deliberately not spending."

## 0:52–1:12 — Place the number, then call it

**On screen:** *Mark the gap — before you look.* Drag the marker slowly to about **24
points**. Let the number under the cursor climb as it moves.

> "Before it will show a single row, it wants a number. How far apart do you think the two
> admission rates are?"

Place it high, deliberately — that is what someone who believes the claim does, and the demo
is better when the app catches the presenter out. Berkeley's real pooled gap is **14.2
points**, so 24 is a clear overshoot without being absurd.

**On screen:** *Step 3 of 5 — lock your call.* The stake row — **Hunch ×1 · Fairly sure ×2 ·
Certain ×3** — and the line underneath that updates live: *Called right: +200 · called
wrong: −200.*

> "Then the call itself. Does this claim survive a fair check — and how sure are you?"

Click **Fairly sure**, and let the cost line update on screen. That single re-render is the
whole scoring model, visible without explaining it.

> "The stake multiplies the call both ways. Being sure and wrong is the expensive kind of
> wrong."

**Three seconds of silence here.** Let the viewer answer it themselves. This is the one
moment that cannot be rushed.

Click **"It holds up"** — deliberately the losing call, because the demo is better when the
app catches the presenter out.

## 1:12–1:32 — Looks true, and nothing settles

**On screen:** the seal opens, struck through — and **the gap ruler first**, with the
player's ring far to the right of the red mark labelled *the data*.

> "You said twenty-four. It is fourteen."

Hold on the distance between the two marks for a full beat. This is the cheapest and best
moment in the video: the viewer has just watched the presenter be confidently, measurably
wrong about a number, before a single argument was made.

**On screen:** `LOOKS TRUE` arrives with the stamp's overshoot. The table: men 44.5%, women
30.4%.

> "Men, forty-four and a half percent. Women, thirty. Fourteen points. That is not a
> rounding error — that is the table that gets printed."

Cursor on the line beneath the verdict, which reads *Your call: It holds up · staked fairly
sure (×2). The cross-examination decides.*

> "It looks like I just won. Nothing has scored. The call settles after the
> cross-examination, not here — which is exactly the trap the claim itself is setting."

There is **no headline chart on this screen**, and do not cue one: that chart is drawn from
two group averages, and this case returns rates, so `group_means` finds no column and draws
nothing. The axis trick gets its own cutaway later, on the case that actually renders it.

## 1:32–2:08 — The same claim, a fairer query

**On screen:** the cross-examination box, pre-filled with *break that down by department*.
Click into it and **edit a word or two on camera** — make it "now break that down by
department, please" — before submitting.

> "Now one follow-up, in plain English. And it is a box, not a button — this is my question,
> not one the app wrote for me. It is still Genie that writes the SQL."

That edit is worth the three seconds it costs. It is the difference between the app
demonstrating a feature and the presenter using one.

The room again, briefly. Then the slam — this time in full, at speed, having been previewed
in the cold open.

> "Same conversation. Genie rewrote its own query — and the only difference is one column."

**On screen:** `BUSTED`, `OVERTURNED`, and the slopegraph. Both queries side by side,
`department` highlighted green in the second.

> "Four of the six departments admitted **women** at a higher rate than men. The total was
> not lying, and no department was hiding anything."

Cursor follows the two lines that cross.

> "Women applied in far larger numbers to the departments that admitted almost nobody. Add
> them together and the easy departments — the ones full of men — dominate the total."

**On screen:** the payout chit, torn, showing its working: *Missed × fairly sure −200 ·
Verdict overturned +250 · Case closed +150 = +200.*

> "I called it wrong and still came out ahead, because the overturning pays either way. I
> made it happen by asking. The app is not scoring whether I guessed — it is scoring whether
> I checked."

## 2:08–2:30 — The one that survives

**On screen:** *← Back to the docket*, then *Open case 2 — The gap that stays*. Move fast
through the seal; this time call **"It holds up"** on a **Hunch**, and land on the repaired
verdict.

> "Same table as the maths case. Same objection — show me the spread. Opposite answer."

**On screen:** `LOOKS TRUE` on both sides of the flip, no stamp, no shake, no freeze.

> "Girls read at five-eighteen, boys at four-ninety-six. Nearly twenty-two points against a
> spread of about ninety — and that gap does not dissolve. It holds up."

The payout chit reads *Called it × hunch +100 · Case closed +150 = +250*: no overturned
line, because nothing was overturned.

This beat is short and it is not optional. Say why:

> "If every case collapsed, 'will it hold up?' would not be a question, and the lesson would
> be that everything is a trick. That is cynicism, not scepticism. One case has to survive,
> and the app has to be willing to say so."

Note for the edit: the slam deliberately plays *flat* here — the hitstop is zero and the
stamp does not shake when nothing flipped. That restraint is worth the two seconds. The
theatre never outruns the arithmetic.

## 2:30–2:52 — Not everything is a lie

**On screen:** *← Back to the docket*, then *Open case 4 — The window*. Fast-forward through
the seal and the call; land on the repaired verdict.

> "The app has a third verdict, and it matters more than the other two."

**On screen:** `HALF TRUE`, and the window chart with the shaded band.

> "Bulgaria's education spending really did fall by more than half between 1991 and 1996.
> That is a fact. It is also six years out of forty — and spending today is higher than
> where the story starts."

Hold on the band and the line ending above its start.

> "Calling that 'busted' would be its own kind of dishonesty. The number is right. The
> picture it paints is not."

## 2:52–3:16 — The two pictures only case 1 draws

**On screen:** *← Back to the docket*, *Open case 1 — The average*. Move fast — the mechanic
is established, so this segment exists for two visuals the other cases do not produce.

Land on the first verdict, where the headline chart sits below the table.

> "This is the chart a newspaper would run off that first query. Look at the bottom of the
> axis."

Cursor on the chart's own label, which reads `axis starts at 487, not 0`.

> "It starts at 487, not zero — so a four-point gap fills the frame. The app is doing the
> trick on purpose and captioning it while it does."

Skip ahead to the repaired verdict and the evidence room. Hit the toggle.

> "And here is what the averages were hiding. Same two groups — once where the averages put
> them, once where they actually are."

Hold on the dots spreading into one crowd.

> "About 97% of the two groups sit on top of each other. That number is computed from the
> count, the average and the spread Genie returned — and the caption underneath says so,
> because those dots are reconstructed, not real pupils. An app teaching you to distrust a
> confident summary does not get to invent people."

## 3:16–3:36 — What you take away

**On screen:** *Print my receipt*. The manila plinth: rank, points, the gap to the next
rung, and the calibration lines.

> "It never scored me on whether the claim was true. It scored the calls I made about them."

Cursor on the calibration line rather than the score.

> "And it ends on this, not the number. 'Fairly sure: nought of one right.' That is a claim
> about me that the points cannot make."

Scroll to the antibody wall. Read one card aloud, at reading speed.

> "'Every group inside can lean one way while the total leans the other.' That is the thing
> that transfers. 'Berkeley did not favour men' is worth nothing by comparison."

## 3:36–3:56 — The evidence, not the claim

**On screen:** expand *Where these queries came from* on the receipt — it is collapsed by
default, so this needs a real click. Both ids visible.

> "One last thing, and it is the reason this is a Genie app rather than an app with a Genie
> in it. This app contains no SQL. Not one statement — there is a build gate that walks the
> syntax tree and fails if a query literal ever appears."
>
> "But you should not take our word for that. An app marking its own homework is exactly
> what this thing spends four minutes arguing against."

Cursor on the two conversation ids, side by side.

```
query v1   conversation 01f19cef42f81e17996b65ef60c957d0
query v2   conversation 01f19cef42f81e17996b65ef60c957d0
```

> "So here are Genie's identifiers instead. Same conversation, both queries. The follow-up
> continued the exchange Genie was already in — it did not start a new one and re-ask.
> That is a stateful agent, and you can read these ids against the space's own message
> history."

## 3:56–4:05 — Close

**On screen:** back to the docket, all five cases, with the masthead HUD carrying the run —
docket count, points, rank.

> "Take Genie out and there is no product here. Not a worse one — a different one: a quiz
> with pre-written questions."

Cut on the docket. No outro card, no music sting, no "thanks for watching".

---

## Optional insert — the fourth verdict

If there is room, or as a B-roll cutaway during the wall segment: type *"kids with phones
read worse"* into **Case zero**, take the third call — *"The data can't say"* — and land on
`CAN'T TELL`.

> "Ask it something the data cannot answer and it says so, and names the column it would
> need. That call pays more than any other on the board. Knowing you cannot answer is the
> harder skill."

Fifteen seconds, and it covers both the verdict and the call the main run never reaches —
that third button is offered only on a claim you typed, because every docket case has been
probed to a verdict and it would otherwise be a button that can only lose.

## Notes for the edit

- **Cut the waits down, not out.** ~20s per Genie turn on a warm warehouse. Hold the
  interrogation room about two seconds — enough to read the phase lights as live machinery —
  then cut. The old instruction to hold half a second on a spinner is obsolete; there is no
  spinner.
- **Do not speed-ramp the SQL.** It is the artifact the whole demo is about. It gets read at
  reading speed or it is not on screen at all.
- **The three-second silence on the call screen is not dead air** — resist the urge to fill
  it.
- **Let the slam play at its own speed.** The hitstop is 900ms on a bust and zero when
  nothing flipped, and both of those are carrying meaning. Trimming the freeze removes the
  beat it exists to create.
- Numbers on screen must match the narration exactly: 44.5, 30.4, four of six, 1991–1996.
  `tests/test_published_numbers.py` reads this file and fails if the prose drifts from the
  data, so change figures here only by changing them in the data.
