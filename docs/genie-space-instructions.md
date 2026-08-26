# Genie space setup

The Genie space is the single most load-bearing piece of configuration in this product,
and it is invisible from the code that depends on it. Every case in the docket rests on
Genie answering the *first* question naively — plainly, exactly as asked, volunteering
nothing — so that there is something left for the follow-up to overturn. That behaviour
comes from the space's instructions, not from any Python in this repo.

## The instructions live in the repo, not in this document

> **Do not paste instructions from a document into the Genie UI.** The authoritative
> table list and instruction text are
> [`src/prove_it/genie/space.py`](../src/prove_it/genie/space.py). Push them with
> [`scripts/update_space.py`](../scripts/update_space.py).

```bash
python scripts/update_space.py --space-id <id> --dry-run   # see the diff first
python scripts/update_space.py --space-id <id>
```

This arrangement exists because the earlier version of this file *was* the instructions,
copied out by hand — and it drifted. It sat here describing a two-table space and four
paragraphs of rules long after the docket had grown to five cases across four tables and
the rules had grown to cover rates, breakdowns, time series, rankings and per-person
figures. Following it would not merely have left a space incomplete; it would have
overwritten a working one with a version that could not answer the Berkeley case.

So the text is in Python, `update_space.py` pushes it, and
[`tests/test_space.py`](../tests/test_space.py) asserts it still says the things the cases
depend on — that answering exactly what was asked is stated and prioritised, that a rate is
never summed, that "biggest" returns a ranking rather than a winner, that every case's
table is declared and described, and that the column aliases the verdict engine matches on
are named.

## The four tables

Declared in `space.py` as `TABLES`, sorted by identifier — the `serialized_space` API
rejects any other order, with a validation error that never mentions sorting.

| Table | Built by | Cases it answers |
|---|---|---|
| `workspace.prove_it.student_scores` | `scripts/setup_workspace.py` | The average, The gap that stays |
| `workspace.prove_it.berkeley_admissions` | `scripts/load_cases.py` | The paradox |
| `workspace.prove_it.country_indicators` | `scripts/setup_workspace.py --indicators-csv` | The window |
| `workspace.prove_it.emissions` | `scripts/load_cases.py --emissions-csv` | The denominator |

Warehouse: the one 2X-Small serverless warehouse Free Edition gives you. Title: *Prove It —
classroom data*.

## Why the instructions are written the way they are

**Answer exactly what was asked** is first, and it is first on purpose — it overrides the
model's instinct to be thorough. Every case is built on the gap between a plain first
answer and a fairer second one, so an instruction that makes Genie *helpful* — volunteering
the spread, the breakdown, the caveat — does not improve the app. It deletes the lesson.
This is the paragraph to check first if a case stops flipping.

**The naming paragraphs** exist because the verdict engine finds columns by name:
`avg_score`, `spread`, `students`, `admit_rate`, `year`, `co2`, `co2_per_capita`. It
degrades safely — an unrecognised shape becomes "can't tell" rather than a crash — but a
stable naming convention is what keeps that path rare. `tests/test_space.py` pins each
alias.

**Never add up a figure that is already per person** was written against a real wrong
answer. `co2_per_capita` is tonnes per person in one year; summing it across years or
countries produces a number that means nothing, and the model will do it unless told not
to.

**Claims about groups of people** is the paragraph to watch in the probe. A claim like
*boys are better at maths* is loaded, and a refusal is a legitimate model behaviour that
would break free-text input. If the probe shows refusals, switch the app to the curated
rumour deck (`PROVE_IT_FREE_TEXT=0`).

## Checking it still works

```bash
python scripts/probe_cases.py --space-id <id>
python scripts/probe_cases.py --space-id <id> --repeats 3 --only paradox
```

`probe_cases.py` asks the question the docket actually depends on: for each case, does the
first answer come back naive, and does the curated follow-up produce the fairer query that
overturns it? A case that fails here has no lesson. That is worth knowing before any UI is
built around it, not after.

## Trusted assets

None required. If the probe shows the first draft is unstable across repetitions, add one
certified example query per case — the documented lever for making Genie's SQL more
deterministic, and it costs nothing but time.
