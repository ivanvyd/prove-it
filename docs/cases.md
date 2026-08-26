# The case docket — specifications

Every figure here was verified this session
against the source named beside it; nothing is quoted from memory. Claim framings are
*candidates* — D2's probe decides which survive, and a framing that will not produce a
naive first query gets rewritten or its case gets cut.

## The live gate — PASSED

Two runs, and it matters which one the artifact currently holds.

**2026-08-21, `scripts/probe_cases.py --repeats 3`** over the four cases that existed then:
every case 3/3 on right table, naive first draft, repair landed and full arc; slowest turns
26s / 27s / 20s / 26s; routing 12/12, so the per-case `space_id` fallback I had allowed for
is not needed. Those figures are quoted from that run's console output.

**2026-08-26, `--repeats 1`** over all five cases including `reading`: GATE PASSED, every arc
completed. This is the run `probe-runs/case-probe.json` now contains — it **overwrote** the
three-repeat file, so the 3/3 figures above are no longer re-derivable from it. Re-run with
`--repeats 3` if you want the artifact to support them again.

> `probe-runs/` is in `.gitignore` — it can carry workspace ids — so a fresh clone has no
> raw file to check. README's invitation to "re-derive any summary from it rather than
> taking figures on trust" only applies on a machine that has run the probe itself.

**No case is cut.** The full five-case docket is viable, and the P2 Titanic case stays a
genuine option rather than a rescue.

Two findings the probe produced that reading the SQL by hand would not have:

- The denominator case first returned `SUM(co2_per_capita)` across 270 years — arithmetic
  that means nothing, presented as an answer — and a single row, which cannot show a rank
  flip. Fixed at the instruction layer.
- It then reached 2/3 because the naive answer sometimes volunteered the per-person column,
  pre-empting its own repair — caused by the instruction that fixed the first problem.
  Tightened to "only when they ask"; back to 3/3.

---

## Finding that changes the design: the docket needs a fourth verdict

The original design listed three verdicts, with CANT_TELL celebrated, under *stays*. Two of the
four cases break that, and they break it in the same place.

- **China is the world's biggest polluter.** True by total emissions — China really is
  rank 1, by a factor of 2.4 over the USA. Not true per person, where the ranking is led by
  Qatar and China does not make the top ten at all. Ruling this BUSTED teaches something
  false; ruling it HOLDS throws away the entire lesson.
- **Bulgaria halved its education spending in the 1990s.** True of 1991–96, and the series
  ends *above* where it started. Same shape.

So the docket adds **`Verdict.HALF_TRUE`** — chip text *"Half true"*, in the fact-checker
register a general audience already reads fluently. Its sentence is always the same shape:
**the number is right, the picture it paints is not.**

This is a deliberate contract change, recorded rather than slipped in. Blast radius:
`Verdict` enum, `VERDICT_TEXT`, the chip CSS, any prose or test asserting "three verdicts"
(grep before editing), and the receipt. `CANT_TELL` keeps its celebrated status; HALF_TRUE
is a *fourth* outcome, not a replacement, and no existing case's verdict changes.

Arguably this makes the product better rather than merely bigger: "true but misleading" is
the most common shape real-world statistical misinformation actually takes, and v1 had no
way to express it at all.

---

## Case 1 — The average *(exists, unchanged)*

| | |
|---|---|
| Claim | Boys are better at maths |
| Table | `workspace.prove_it.student_scores` (synthetic, 9,715 rows) |
| Naive | `AVG(maths_score) GROUP BY gender` → boy 492.6, girl 488.1 → **LOOKS TRUE** |
| Follow-up | "show the spread too" |
| Repaired | adds `COUNT(*)`, `STDDEV` → gap 4.5 against spread ~89 → **BUSTED** |
| Trick | An average says where a group sits, not how much people inside it differ. |

Ships as-is. Its arithmetic (`analyse`, effect size vs 0.2) is the reference implementation
the other modes follow.

---

## Case 1b — The gap that stays *(the one that survives)*

Added to the docket after this file was first written, and missing from it until 26 Aug —
which meant a document opening "every figure here was verified" was silent about a fifth of
the live docket. Recorded in `fixtures/case-reading.json` and probed live 2/2.

| | |
|---|---|
| Claim | "girls are better at reading" |
| Table | `workspace.prove_it.student_scores` (`reading_score`) |
| Naive | two averages → boys **496.2**, girls **518.0** → **LOOKS TRUE** |
| Follow-up | "show the spread here too, and how many are in each group" — the same objection that busts case 1 |
| Repaired | boys 496.2 ± **88.4** (4,812), girls 518.0 ± **90.4** (4,903) → **LOOKS TRUE** |
| Trick | The gap that survives. Not every gap dissolves when you look harder. |

**Why it exists.** A gap of **21.8** against a spread near 90 is roughly five times the
maths case's 4.5, and it does not wash out. Without a case like this the docket teaches that
everything is a trick, which is cynicism rather than scepticism — and it makes "there's a
trick" an unloseable call, which is a design fault before it is a pedagogical one.

**Source.** Same synthetic `student_scores` table as case 1, generated from a fixed seed;
contains no real pupils. The effect size is pinned by `tests/test_demo_data.py`.

## Case 2 — The paradox *(new, flagship)*

| | |
|---|---|
| Claim candidates | (a) "Berkeley admitted more men than women in 1973" (b) "Berkeley's 1973 admissions were biased against women" (c) "Men had a better chance of getting in at Berkeley in 1973" |
| Table | `workspace.prove_it.berkeley_admissions` (new) |
| Naive | pooled admit rate by gender → men 44.5%, women 30.4% → **LOOKS TRUE** |
| Follow-up | "break it down by department" |
| Repaired | per-department rates → women admitted at a **higher** rate in 4 of 6 → **BUSTED** |
| Trick | Simpson's paradox. Each group can lean one way and the total lean the other, when the groups differ in size and in difficulty. |

**Source.** Bickel, Hammel & O'Connell (1975), *"Sex Bias in Graduate Admissions: Data from
Berkeley"*, Science 187(4175): 398–404. Cross-checked against R's `datasets::UCBAdmissions`
(4,526 observations, Admit × Gender × Dept).

**Verified figures.** Applicants and admit percentages from the Wikipedia Simpson's-paradox
article's reproduction of the paper's Table; marginal totals independently from the R
manual page. Admitted counts are pinned by both: they reproduce all twelve published
percentages *and* both marginals.

| Dept | M applicants | M admitted | M rate | F applicants | F admitted | F rate | Higher |
|---|---|---|---|---|---|---|---|
| A | 825 | 512 | 62.1% | 108 | 89 | 82.4% | **women** |
| B | 560 | 353 | 63.0% | 25 | 17 | 68.0% | **women** |
| C | 325 | 120 | 36.9% | 593 | 202 | 34.1% | men |
| D | 417 | 138 | 33.1% | 375 | 131 | 34.9% | **women** |
| E | 191 | 53 | 27.7% | 393 | 94 | 23.9% | men |
| F | 373 | 22 | 5.9% | 341 | 24 | 7.0% | **women** |
| **Total** | **2,691** | **1,198** | **44.5%** | **1,835** | **557** | **30.4%** | men |

**The trap that must not reach the article.** The famous "44% of men, 35% of women" figure
is over *all* Berkeley departments — 8,442 men and 4,321 women. The A–F table covers only
the six largest, 2,691 and 1,835, and pools to **44.5% / 30.4%**. Those are different
numbers about different populations. The app shows what Genie computes from the loaded
table; the story, the README and the video must say **"the six largest departments"** and
must never quote 44/35 as if it came from this table. A drift test pins all fourteen
figures above.

**Loading.** Hand-entered from the verified table into the data notebook — 12 aggregate
rows, or 4,526 per-applicant rows expanded *from those aggregates* if row-level queries are
wanted. If expanded, the on-screen label says exactly what it is: reconstructed from the
published 1973 aggregates. No fabricated individuals presented as records.

---

## Case 3 — The window *(new; data already loaded)*

| | |
|---|---|
| Claim candidates | (a) "Bulgaria halved its education spending in the 1990s" (b) "Bulgaria's education spending collapsed after 1991" (c) "Bulgaria stopped funding education after communism" |
| Table | `workspace.prove_it.country_indicators` (real, loaded; 5,205 rows, 206 entities, 1870–2025) |
| Naive | the 1990s window → 1991: 5.43 → 1996: 2.23, a 59% fall → **LOOKS TRUE** |
| Follow-up | "show every year in the data, not just the 1990s" |
| Repaired | full series → recovered to 2022: **4.50**, above 1980's **3.53** → **HALF_TRUE** |
| Trick | A true fact about a chosen window, told as if it were the trend. |

**Verified series** (`combined_expenditure_share_gdp`, % of GDP, annual):

```
1980 3.53                                    (pre-transition baseline)
1990 4.45   1991 5.43   1992 5.26   1993 4.95   1994 4.17   1995 2.37   1996 2.23
1998 2.74   2001 3.38   2003 4.00   2008 4.22   2013 4.06   2019 4.21   2022 4.50
```

Chosen over Burkina Faso (−58.3%) and Niger (−49.5%), whose falls are isolated spikes with
six- and nine-year gaps either side — sparse data, not a policy story. Bulgaria's decline is
dense, monotonic and historically real, which is what makes the case honest: **the collapse
genuinely happened.** The lie is only in what the window implies about today.

---

## Case 4 — The denominator *(new)*

| | |
|---|---|
| Claim candidates | (a) "China is the world's biggest polluter" (b) "China pollutes more than anyone else" |
| Table | `workspace.prove_it.emissions` (new, from OWID) |
| Naive | total CO2 by country, 2023 → China 11,902.5 Mt, rank 1 → **LOOKS TRUE** |
| Follow-up | "show it per person instead" |
| Repaired | per capita top ten → **Qatar 38.84 t**, then Bahrain, Trinidad and Tobago. **China does not appear** → **HALF_TRUE** |

> **Corrected 26 Aug 2026, and the correction is the point.** This row previously read
> "China 8.37 t, rank 19; USA 14.30 t". Those figures are genuinely in the table — but they
> are **not what the case produces**, because Genie answers "show it per person" with a top
> ten, and China is not in it. The row described the data instead of the product, which is
> the exact failure this project exists to argue against.
>
> Checked against `fixtures/case-denominator.json`, the recorded conversation the offline app
> replays: turn two returns Qatar, Bahrain, Trinidad and Tobago, Saudi Arabia, UAE, Kuwait,
> Oman, Australia, United States, Canada. The verdict engine's own sentence, generated from
> those rows, is: *"By the total, China was top. Per person it is Qatar, at 38.84. Both are
> true: a total measures how big a place is as much as what it does."*
>
> **Data vintage.** The totals are what `workspace.prove_it.emissions` holds, loaded from
> OWID in August 2026. OWID has since revised the same year to 12,172 Mt; the Global Carbon
> Project restates past years as inventories are updated. The case is unaffected. Reload with
> `scripts/load_cases.py --emissions-csv` if you want the table and a live OWID check to
> match to the decimal.
| Trick | A total measures how big a country is as much as what it does. Per person asks a different question, and both answers are true. |

**Source.** Our World in Data CO2 and Greenhouse Gas Emissions (CC BY 4.0 — attribute
in-app). Downloaded this session; verified 2023 figures above over 159 countries with
population > 1M.

**Aggregate rows must be filtered at load.** OWID puts `World`, `Asia`, `High-income
countries` in the same `country` column as real countries. Keep only rows with a non-empty
`iso_code` that does not start with `OWID_`, or the ranking is meaningless. This filter
belongs in the loader, not in a Genie instruction — Genie must not be relied on to exclude
the World row from a "biggest emitter" query.

**Honesty requirement.** This case must not read as "China is off the hook". The exhibit
states both numbers plainly and names the question each one answers.

---

## Case 5 — The one that holds *(P2, cut first)*

Titanic survival by sex → HOLDS; split by class → still HOLDS. Without a case that survives
scrutiny the docket teaches cynicism rather than scepticism, which v1's own docs warn
against. If it is cut, Case 1's `CANT_TELL` path carries that weight alone — acceptable but
weaker.

---

## Case 0 — Bring your own rumour

Free text, unchanged from v1 (`PROVE_IT_FREE_TEXT`, default on). Whatever Genie returns is
dispatched by *shape*, so a typed claim reaches the new verdict modes for free. Most such
claims land on CANT_TELL, which stays a win.

---

## What the verdict engine must compute

Each mode is a pure function over `ResultTable`, selected by **which columns came back** —
never by case id, so Case 0 gets every mode for free. This is how `analyse` already picks
spread-mode.

| Mode | Fires when | Computes | Verdict |
|---|---|---|---|
| spread *(exists)* | mean + spread + count | effect size vs 0.2 | HOLDS / BUSTED |
| subgroup | a group column + a rate or count pair, > 2 rows | direction per subgroup vs pooled direction; how many subgroups reverse; which is the majority | BUSTED when pooled direction reverses in most subgroups |
| series | a year/time column + one value column | window delta vs full-series first/last and range | HALF_TRUE when the window's direction is real but the series ends the other way |
| rate | a total column + a per-unit column | ordering under each | HALF_TRUE when rank 1 differs between them |

All four obey the existing rules without exception: arithmetic only, never a model judging;
every degenerate shape falls through to CANT_TELL; every displayed number is rounded before
it is compared or quoted.
