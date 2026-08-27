# Prove It — requirement

Status: shaped, no open clarification markers.
Date shaped: 2026-08-20. Contest closes 2026-08-31.

## 1. Where the idea came from

The starting point was the [Databricks Community Genie-Powered App Challenge][contest] and a
constraint I set myself: build something that had not been built before, rather than another
chat-over-your-warehouse assistant, and point it at something that matters outside a
business dashboard. Education and data literacy were where I wanted it to land.

That constraint is what produced the inversion the whole product rests on. If the obvious
Genie app answers your question, the interesting one refuses to — and shows you the query
instead, so the thing you learn to read is the *method*, not the answer. Everything in this
document follows from that decision.

[contest]: https://community.databricks.com/t5/learning-events/databricks-community-contest-genie-powered-app-challenge/ec-p/165825

## 2. What it is

A Databricks App for ages 10–14 and their teacher — and, on the docket cases, for anyone who
has ever repeated a statistic. A player opens a case, or types a rumour they have heard. The
app does not answer it. It asks a Genie space to write the SQL that would *test* the claim,
shows only that SQL plus Genie's reasoning steps, and makes the player commit — *does this
hold up, or is there a trick?*, and how sure are you — before any number is revealed. The
player then cross-examines through a follow-up turn in plain English, and watches a
decisive-looking gap dissolve.

The call is settled against the verdict *after* the follow-up, never the one at the reveal.
That is what turns the reveal from an answer into a testimony: it looks like it vindicates
one call and sinks the other, and the cross-examination reverses it.

## 3. Contest constraints (verified from Databricks docs, 2026-08-20)

- Must be a Databricks App on Free Edition with a Genie Agent at its core.
- Judged out of 40: **20 Genie centrality**, 10 track execution (Track B — Creative Thinking,
  switched from Track A on 26 Aug: that track's focus word is "usefulness" and its examples
  are internal BI copilots, which this is not; Track B's is "originality" and its words are
  "unconventional, playful, exploratory", which this literally is), 10 app
  experience.
- Free Edition: serverless only; one SQL warehouse at 2X-Small; max 3 apps, each auto-stopping
  after 24h; outbound internet restricted to an allowlist; non-commercial; no SSO/SCIM.
- Deliverables: the app, a Community Articles project story, a demo video.

## 4. Decisions taken by the user

| # | Decision | Chosen | Consequence |
|---|---|---|---|
| D1 | Dataset | Synthetic student-level **plus** three real open published tables | Four tables carrying a five-case docket; three of the five run on real, citable data |
| D2 | Workspace state | Not set up yet | Full zero-to-running setup path is in scope; probe gate is run by the user, not this session |
| D3 | Form factor | Web app, Python + Streamlit on Databricks Apps | Forced by the contest; no mobile build |

D1 rationale worth recording: the core lesson needs **per-student rows**, because it turns on a
~5-point gap between group means hiding a ~90-point spread within each group. Open education data
is country-level aggregate and cannot express that. Synthetic is therefore the honest choice for
table 1, not merely the convenient one. Table 2 is genuinely real so the demo can end on it.

## 4a. Investigated and rejected

**Creating the Genie space programmatically.** `setup_workspace.py` automates every
workspace object except the Genie space itself, which leaves four clicks in the UI. The SDK
does expose `GenieAPI.create_space(warehouse_id, serialized_space, ...)`, so this looked
closeable.

It is not, safely. `serialized_space` is an opaque JSON string with no schema in the SDK —
no dataclass, no field documentation — and both the SDK docstring and the REST reference
say to obtain it by calling Get Genie Space on a space that already exists. The published
example shows a shape (`version`, `config`, `data_sources`, `instructions`, `benchmarks`)
but is explicitly illustrative rather than a contract.

Building that payload from the example would mean guessing at an undocumented internal
format, inside the one script that has to work on a first run against a real workspace, to
save four clicks that are already written down. Rejected. If someone later has a space to
hand, `GET /api/2.0/genie/spaces/{id}` returns a real `serialized_space` and this becomes a
ten-minute job with an actual contract behind it.

**Update, 2026-08-21 — the reason for rejecting this no longer holds.** A space now exists,
so the schema was read back rather than guessed. Recording it here because the paragraph
above would otherwise send the next person down a road that is no longer blocked:

```jsonc
{
  "version": 2,
  "data_sources": { "tables": [ /* sorted by identifier — the API rejects other orders */ ] },
  "instructions": {
    "text_instructions": [ { "id": …, "content": [ /* one string per line */ ] } ]
  }
}
```

Two things that cost time and are not written down anywhere: the `tables` array **must** be
sorted by identifier, and `content` is a list of lines rather than one string with newlines.
Instructions set through the UI and read back through the API is the reliable way to
confirm any further field.

**This is still not automated**, and that is a choice rather than a blocker now: the four
clicks are documented in `docs/setup.md` §3, they happen once per workspace, and a script
that writes space instructions is a thing that can silently drift from
`docs/genie-space-instructions.md` — which is the file that actually decides whether the
lesson works. Anyone who wants it has the contract above.

## 5. Functional requirements

| ID | Requirement | Testable as |
|---|---|---|
| R1 | A player opens one of the docket's cases, or submits a free-text claim; either way the app sends it to a Genie space as a question that asks Genie to *test* the claim | Claim compiler unit test; probe run |
| R2 | The app renders the SQL Genie emitted, verbatim, without modification | Unit test asserts rendered SQL is byte-identical to the attachment |
| R3 | The app renders Genie's `thoughts` as ordered, typed reasoning steps | Unit test over a recorded fixture with ≥2 thought types |
| R4 | The result rows are NOT fetched until the player commits a call | Unit test asserts the client's result method is not called before `commit_call` |
| R5 | The player locks one **call** and one **stake** before any row is fetched, and it is settled against the *final* verdict | `tests/test_game.py`; `tests/test_session.py` |
| R6 | A follow-up turn on the same conversation produces a v2 query, diffed against v1 | Diff unit test; conversation id reused |
| R7 | Every claim resolves to exactly one of four verdicts: HOLDS, BUSTED, HALF_TRUE, CANT_TELL | Verdict engine table test over all branches |
| R8 | A Genie response with no query attachment, a refusal, or a non-numeric result routes to CANT_TELL, never to an error screen | Unit test per degenerate fixture |
| R9 | A finished investigation renders a receipt: claim, both queries, verdict, the call and its stake, and what it paid | Snapshot test |
| R10 | The app writes no SQL of its own, at any point | Repo-wide grep gate in tests |
| R11 | A curated rumour deck is available as a fallback path if free text proves unreliable | Config flag toggles input mode |
| R12 | Setup is reproducible from zero: notebook creates tables, docs give Genie space instructions | A second person can follow `docs/setup.md` |
| R13 | The two non-code contest deliverables exist: a Community Articles project story and a demo | `docs/project-story.md`; the demo shot list is local-only production scaffolding, gitignored |
| R14 | Every query on screen carries Genie's own identifiers, unmodified, so the app's authorship claim is checkable against the Genie space's message history rather than self-asserted | `tests/test_custody.py`, `tests/test_custody_ui.py` |
| R15 | The retrial visibly reports that it continued the first query's conversation, and never claims continuity it cannot show | `test_the_recorded_demo_really_is_one_conversation`, `test_a_missing_turn_never_claims_continuity` |
| R16 | A run of the docket is scored: a call pays `100 × stake`, an overturned verdict `+250`, a closed case `+150`, a called can't-tell `+200`, a cleared docket `+500`; points floor at zero and a settled case never pays twice | `tests/test_game.py` |
| R17 | The score reads as progress, not a tally: a rank ladder (Rumour Hearer 0 / Evidence Clerk 500 / Field Investigator 1200 / Chief Examiner 2500), a streak, and per-stake calibration on the receipt | `tests/test_game.py`; `tests/test_app_flow.py` |
| R18 | A wrong call is never punitive and never gates content: nothing is locked, and a verdict the data cannot reach scores nothing rather than costing the player | `tests/test_game.py` (VOID keeps the streak) |
| R19 | Every inline visual paints in the page's own palette and type stacks, across the iframe boundary `st.iframe` puts it behind | `tests/test_frame_palette.py` |
| R20 | On a case whose trick is a distance, the player may place an estimate of that distance before any row is fetched, and is shown their mark against the real value at the reveal | `tests/test_estimate.py`; `tests/test_app_flow.py` |
| R21 | The estimate can only earn: a wide mark scores zero, never negative, and prints no line on the payout | `test_a_wild_guess_pays_nothing_and_costs_nothing` |
| R22 | The estimate is locked by the same commit as the call — there is no path that records one after the rows are on screen | `test_the_estimate_is_locked_by_the_same_commit_as_the_call` |
| R23 | The follow-up question is editable by the player, defaulting to the probed wording, and an emptied box falls back rather than asking Genie nothing | `tests/test_session.py` (cross-examination group) |

R14 and R15 were added on 2026-08-21, after the MVP shipped. The reasoning is recorded here
rather than only in the commit: R10 makes the no-SQL rule true, but a build gate is
invisible to anyone using the app, and the receipt's "Queries written by this app: 0" is the
app marking its own homework. R14 replaces that with identifiers issued by a system the app
does not control. R15 exists separately because continuity is the strongest single claim
available — the same `conversation_id` across v1 and v2 is what distinguishes a stateful
agent from a template run twice — and because a false continuity claim would be worse than
none, it is stated as a requirement that it degrade to silence.

R16–R19 were added on 2026-08-22 with the game rework, and R5 was rewritten at the same
time. The reasoning is worth recording, because the requirement it replaced was satisfied
by code that did not do the job. The old R5 said the child "picks one of three outcome
shapes as a prediction, and it is scored" — and it was scored, by a function that never
read the data. "Correct" meant "you picked a shape that would falsify the claim", so two of
the three answers always won and nothing was ever at stake. A requirement can be met
exactly and still describe a comprehension check rather than a game. R5 now names the thing
that can actually be lost.

R19 is a rule about *rendering*, in a requirements table, for the same reason: it was
learned from a defect no other requirement could catch. See §6.

R20–R23 were added on 2026-08-26, against a complaint rather than a defect: the player
"mostly READS and then CLICKS ONE OF TWO BUTTONS". Both mechanics are answers to that, and
both were chosen for reasons stronger than taste. The estimate implements Kim, Reinecke &
Hullman, *Explaining the Gap* (CHI 2017), whose measured result is that predicting data and
then seeing your prediction against it improves recall and comprehension. The editable
follow-up came out of a structured ideation pass as the highest viability × fit option, and
it strengthens R10 rather than threatening it: the player's words are the *question*, and
Genie still writes every query.

R21 and R22 are constraints on the estimate rather than features of it, and they exist
because both are easy to get wrong in the direction that would damage the product. A
mechanic that could lose points would make the docket punitive, which §2 says it is not; a
mark that could be placed after the reveal would make the seal a lie, which is the one
thing this app cannot afford.

R10 is the twenty-point criterion expressed as a test. It is a **non-negotiable**: any SQL literal
in application code that targets the demo tables fails the build.

## 6. Non-functional

- A Genie turn takes seconds. That wait is a beat, not a spinner: the interrogation room
  runs a case clock and lights each phase as its real status arrives. No hard timeout
  below 120s.
- Single-session, single-player. No accounts, no persistence beyond `st.session_state`.
- Responsive down to 375px. The score and the rank are the last things to be shed: the HUD
  drops the docket counter, then the streak, and keeps points and rank at every width.
- The app must degrade to CANT_TELL rather than raising, for any Genie response shape.
- Every visual mounted with `st.iframe` renders inside an iframe, which is a separate
  document that cannot read the page's CSS custom properties. Colours and type stacks cross
  that boundary by import from `ui/style.py` — never by a `var(--x, fallback)`, which
  inside a frame silently means "the fallback, always".

## 7. Explicitly out of scope

- Real pupil data of any kind. Synthetic or open public only.
- Pupil or teacher accounts, SSO, persistence across sessions.
- Live moderation of children's free text.
- A mobile build.
- The class rumour board, cross-examination round, Guess-the-Query round, teacher summary — these
  are the documented stretch set and ship only if the MVP is finished and stable.

## 8. Assumptions (defaults taken without asking)

| # | Assumption | Why it is safe |
|---|---|---|
| A1 | Auth is the app's **service principal**, via a declared Genie space resource with Can Run, not on-behalf-of-user | The documented Apps pattern; OBO adds user-consent scope work that buys nothing for a single-session classroom demo |
| A2 | English only, en-GB copy | No locale requirement stated |
| A3 | Catalog/schema default to `workspace.prove_it`, overridable by `PROVE_IT_CATALOG` / `PROVE_IT_SCHEMA`. **The env vars alone are not enough to move the app to other data**: discovery is narrowed to the tables the Genie space declares, and that list is `TABLES` in `genie/space.py`, which `update_space.py` pushes without reading either variable. Reuse means editing that tuple too — see README, "Pointing it at your own data" | Free Edition gives one metastore; `workspace` is its default catalog |
| A4 | Table 2 (real open data) is uploaded by hand as a CSV | Free Edition restricts outbound internet, so a download at runtime cannot be relied on |
| A5 | The verdict is arithmetic, dispatched on the *shape* of the columns Genie returned — two means, two rates, subgroups, a series, a ranking, a per-unit figure — and never a model judging a model | Determinism; also avoids putting unverified LLM output in front of a child as authority. A shape nothing recognises degrades to CANT_TELL |
| A6 | The demo rumour is "boys are better at maths" and resolves to BUSTED | It is a real, well-documented small-gap/large-spread effect, so the lesson is true as well as pedagogically clean |
| A7 | The call is a 3-way choice and the stake a 3-way choice, neither free text | Scoreable without a model; avoids moderating children's free text. "The data can't say" is offered only on a typed claim — on the docket, every case has been probed to a verdict, so it would be a button that can only lose |
| A8 | No telemetry, no analytics, no external calls of any kind | Free Edition allowlist; also the right default for a children's app |

A8 turned out to need enforcing rather than assuming, and both breaches were found in
review rather than by design. Streamlit's `browser.gatherUsageStats` defaults to **true**,
so the app shipped telemetry on until `.streamlit/config.toml` turned it off; and the CSS
carried a Google Fonts `@import`, which is a request from the child's browser to a third
party on every render regardless of what the server-side allowlist permits. Both are now
closed — the fonts are system stacks. Anything added later that reaches the network needs
checking against this row, because "we did not add an API call" is not the same as "the
page makes no requests".

## 9. Risks carried into the build

| Risk | Severity | Gate |
|---|---|---|
| Genie's first draft is too good — volunteers the caveat, so the reveal has no gap | Kill | Day-1 probe + day-2 instruction tuning |
| A loaded question ("are boys better at maths?") is refused | Kill | Day-1 probe; mitigation R11 already in scope |
| `thoughts` is not populated at runtime on Free Edition | Degrade | Day-1 probe; beat 2 falls back to SQL + description |
| Parallel Genie calls throttle on one 2X-Small warehouse | Watch | Stretch features cut first |

`thoughts` is confirmed to exist as a typed field in `databricks-sdk` 0.68
(`GenieQueryAttachment.thoughts: Optional[List[Thought]]`, `Thought.thought_type: ThoughtType`
with DESCRIPTION / UNDERSTANDING / DATA_SOURCING / INSTRUCTIONS / STEPS). Confirmed by reading the
installed package, not from memory. Whether it is **populated** for a given query on Free Edition
is a runtime question the probe answers.

## 10. Done means

All of R1–R12 traced to code and to a test or a probe artifact, the app runs locally against the
recorded-fixture client with no credentials, and `docs/setup.md` takes a stranger from a fresh Free
Edition account to a running app.
