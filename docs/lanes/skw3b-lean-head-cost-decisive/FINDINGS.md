# `model_performance-g7h3` — FINDINGS

**Lean head, cost-decisive: the B-term on the daily driver.**
Item: `model_performance-g7h3` · Lane: `skw3b-lean-head-cost-decisive` · Date: 2026-09-06/07
Pre-registration: `PREREGISTRATION.md`, committed at **`741a71b`** with **$0.00 spent**.

> **RESULTS ARE IN §5.** §§1–4 are the three things this lane established before and
> around the measurement, each of which stands on its own and none of which needed the
> measurement to be true.

---

## 1. THE ITEM'S LITERAL DELIVERABLE IS NOT-POSSIBLE AT $930 — arithmetic, before spending

Computed and committed **before the first API call** (`PREREGISTRATION.md` §3, commit
`741a71b`, $0.00 spent).

### 1.1 The n, recomputed — and it reproduces the item's own 197

`GOAL.md` deliverable 1 asks for *"n = 197/arm, or the recomputed n from `skw3`'s own
variance for MDE <= 5% — state which and show the calculation."* **This lane uses the
recomputed n.**

```
K = (z0.975 + z0.80)^2 = (1.959964 + 0.841621)^2      = 7.8489
sd_pooled  (skw3 t1_corpus.json, VALID pool n 10/11)  = $0.5696659
delta      = 5% of the stock mean $3.2170             = $0.160850
n_per_arm  = 2 * sd^2 * K / delta^2
           = 2 * 0.3245191 * 7.8489 / 0.02587272      = 196.896  ->  197
```

Confirmed a second, independent way, from the realised MDE and needing no sd:
`n = n_harmonic x (MDE_obs / 5%)^2 = 10.4762 x (21.676/5)^2 = 196.9`. **Same answer.**
(`skw3`'s own `n_needed_5pct` field: **196.89555814991203**.)

At `3d2`'s older sd of $0.54 the same model returns **183.8 → 184**. The item's
"n~184–197" is exactly this pair of sd estimates; **197 is the conservative member and is
what this lane priced.**

### 1.2 The price of the stated deliverable

Deliverable: `$/task` per arm **per provider per scenario** with a CI able to fire a ±5%
rule — **2 arms × 2 providers × 2 scenarios = 4 cells**.

```
197/arm x 2 arms x 4 cells                          = 1,576 valid runs
/ 0.875 measured S7 validity (skw3, 28 of 32)       = 1,801 launches
/ 0.67  published V1 validity (5zp)                 = 2,352 launches
x $3.217 cheapest observed per-launch price         = $5,794      (best case)
x $4.08  skw3's blended price                       = $9,596      (skw3 basis)
```

**$5,794 – $9,596 against $930 — 6.2× to 10.3× over. NOT-POSSIBLE, and no reallocation
inside $930 closes it: even the single cheapest cell at ±5% is $1,449, still 1.6× over.**

**The authority that WOULD close the stated deliverable is $5,794 (best case) to $9,596.**

### 1.3 The cap's own arithmetic does not close — a goal defect, reported not absorbed

`GOAL.md` Procedure 3's AUTHORING RULE requires a run-buying cap to be stated as
`runs × arms × per-run estimate / validity = cap`, and instructs the lane to report a cap
that fails it **as a finding**. This cap states, in full:

> *"SPEND AUTHORITY for this item: $930 — owner-funded at the decisive number; `skw3`
> priced the B-term at ~$810."*

Three defects, all knowable on first read:

1. **No arithmetic at all** — no run count, no arm count, no validity divisor.
2. **The $810 prices a different, smaller design.** Traced to source: `skw3` §5 quotes
   *"`3d2` §4.4 already priced the dollar test at n ≈ 126/arm ≈ $810"* — **one** cell
   (terra/S7), at **n=126**, sized to `3d2`'s *observed* 6.1% effect, **not** to the ±5%
   threshold. This goal asks for **n=197 across four cells** — 6.25× more valid runs.
   Reusing a price quoted for a smaller set on a larger one is **verbatim the `1ru` defect
   the same paragraph forbids**.
3. **`skw3` had already priced *this* goal's deliverable, in the same document, at $8,964** —
   and that, not $810, is what the cap should have been built from.

---

## 2. A LIVE HARNESS DEFECT: the S7/S5 compaction knob is DEAD on today's `main`

**Found by paying for it.** The first opus-5/S7 run returned `$3.85`, wall 615.3 s, recall
**100/100**, and `context:compaction` **0** against the required ≥5 → **INVALID**.

Diagnosed to root cause for **$0**:

| step | observed |
|---|---|
| `scripted_driver.py` | `configure:` **(empty)** — vs `vbs`/`3d2`: `PRIMARY_OK ... \| MAXTOK_OK max_tokens=90000 budget_cap=inserted` |
| `configure_cell.py` | **exit 5**, stderr `FAIL: 'max_tokens:' line not found in context config` |
| `find_bundle_md()` | hardcodes `<foundation>/bundles/anchors-amp-dev/bundle.md` |
| that file, today | **1,528 bytes, pure `includes:`** — no `context:` block, no `max_tokens:` line |
| where the line lives now | `<foundation>/bundles/anchors/bundle.md:33` → `max_tokens: 300000` |

`anchors-amp-dev` was refactored into a pure include of `anchors` (*"this order reproduces
the previously shipped mount plan byte-for-byte ... the DRY change moves no wire bytes"*).
The wire bytes indeed did not move — **the harness's knob did**, and it was pinned to a
path by name.

**Consequences, all measured:**

1. **Compaction fires at the inherited 300,000 instead of the configured 90,000.** No
   boundary is ever crossed and the run is scored INVALID — *after* being paid for in full.
2. **It is not Anthropic-specific and not this lane's new cell.** `--provider-id terra
   --model gpt-5.6-terra` fails identically in the same container. **Every S7/S5 run
   launched today is affected.**
3. **The failure is loud in `configure_cell.py` and silent in `scripted_driver.py`.**
   `dexec_out()` returns only `stdout`, **drops `stderr`, and the driver never checks the
   exit code.** That one seam is what turns a one-line config break into a full-price
   invalid run. `configure` was already recorded in `driver_record.json` — as an empty
   string — so the evidence was captured and nothing looked at it.

**Fix shipped as a proposed diff, not applied to the shared tree** (`GOAL.md` 0rg hazard):
`skw3b-configure-cell-anchors-fallback.diff` — `find_bundle_md()` selects **by content**
(a candidate is accepted only if it actually contains the line the caller is about to
patch), trying `anchors-amp-dev` first so a container that still carries the value there
behaves exactly as before, then `anchors`.

**Verified before any relaunch**, on `val-g7h3-b`:

```
PRIMARY_OK id=opus model=claude-opus-5 effort=medium priority=0 | MAXTOK_OK max_tokens=90000 budget_cap=inserted cs=...
```

— byte-shape identical to the `configure:` line in every published `vbs`/`3d2` run log.
This lane then ran its own patched copy with `--skip-configure`, and `run_arm.sh`
**refuses to launch** unless configure really printed `MAXTOK_OK max_tokens=90000`. A
second recommendation follows directly and is *not* in the diff because it is the shared
driver's call to make: **`scripted_driver.py` should fail the run when `configure` returns
empty or non-zero**, rather than paying for it and discovering it at grade time.

---

## 3. `claude-opus-5` ON S7 — priced for the first time, and the S7-17 gate does not fit it

**No opus-5 S7 run had ever been costed** (`skw3` §6.2 flags exactly this). This lane
built the cell (`opus5-medium`: `provider_id: opus`, `claude-opus-5`, `effort: medium`) in
its **own capture root**, never in the shared `scenarios/` tree.

**The V1 head cut was verified on the Anthropic wire before any bulk spend**, from the
shim's own per-request log:

| | instructions | tools | total | vs published |
|---|---:|---:|---:|---|
| stock (`bji` census) | 44,516 ch | 40,149 ch | 84,665 ch | — |
| V1 (this lane, measured) | 21,654 ch | 26,595 ch | **48,249 ch** | cut **43.0%** vs `bji`/`skw3`'s **44.0% of bytes / 44.4% of tokens** |

with `wire: anthropic`, `variant: v1`, `system_blocks_rewritten: 1`, `tools_rewritten: 13`
on every request. **The treatment is on the wire, on the right provider.**

### 3.1 The finding that governs everything below: **S7-17's validity gate is calibrated for terra, and opus-5 fails it in BOTH arms**

S7-17 freezes `--max-turns 17` and requires **≥5 compaction boundaries**. On terra that is
comfortable — `skw3`'s 32-run extraction gives stock **7.00 mean boundaries (1 of 14 below
the gate)** and V1 **6.72 (3 of 18 below)**. On `claude-opus-5` the same 17 turns produce
far less context, and the gate rejects most runs **of both arms**.

That is not the lean-head treatment failing. `5zp`'s asymmetry — the lean head fills the
window ~31% slower and so crosses the cap fewer times — is real and is visible here too,
but it is now **second-order next to a cell-level mismatch that hits the control arm just
as hard**. Measured rates are in §5.

**Consequence, and it is the load-bearing one:** the pre-registered VALID-only primary
cannot reach a useful n on this cell at this authority. The arithmetic is in §5.3.

### 3.2 Why the ALL-runs view is the meaningful one for a COST endpoint (post-hoc, labelled)

The ≥5-boundary gate exists for the **retention** endpoint: you cannot measure what
compaction destroyed if compaction never happened. For a **cost** endpoint it is
different — boundary count is a **post-treatment outcome**, and conditioning an estimate on
a post-treatment variable is a collider. Every run compared here does **the same 17 turns
against the same byte-identical seed**; how often the harness compacted is a *consequence*
of the arm, not a covariate of it.

`skw3` §7 reached the same place from the data side (*"the excluded V1 runs are the cheap
ones ... the primary is therefore conservative, and the ALL-runs sensitivity is the
unfiltered view"*). **This lane pre-registered the ALL-runs analysis as a secondary and did
not switch primaries after seeing the numbers.** The argument above is stated as
**post-hoc**, and both analyses are reported in §5 with their verdicts and their achieved
MDEs.

---

## 4. RUN ORDER — what was designed, and the one place it was violated

Designed against `skw3` §4's contention hazard (two chains with **different heads** back to
back contend for the Anthropic conversation cache; a miss costs ~$0.065/request):

1. **Arm-blocked in time** — one arm live at a time across all three DTUs; a block is three
   concurrent runs of a single arm; the next block does not start until the current one
   fully drains.
2. **≥6-minute drain across an arm switch**, longer than Anthropic's 5-minute cache TTL.
3. **ABBA block sequence** so the calendar-time trend is balanced — required, not
   cosmetic: `skw3` §1.1 measured cohort deltas of **+3.99% / −20.37%**, roughly **6× the
   effect the ±5% rule is trying to detect**.
4. **Block index recorded as a stratum**, with a block-paired estimator as a pre-specified
   secondary.
5. `3d2`'s concurrent-arms design was **considered and rejected**: it is the best
   time-trend control and the worst contention control, because it puts two different heads
   live at once by construction.

**DEVIATION, disclosed:** the block runner died once (killed with its launching shell) and
was restarted at block 04 with no memory of the previous arm, so **the block 03 (V1) →
block 04 (stock) transition ran with NO drain**. Every other arm switch in the lane drained
for 360 s. Block 04 is flagged in the raw data; the block-paired secondary is the estimator
that is robust to it.

---

## 5. RESULTS — **B is settled on the daily driver, and it is not the blocker**

**98 end-to-end `claude-opus-5`/S7-17 runs, 49 per arm, $428.10 of the $930 authority.**
One analysis, run once, at the end, on the pre-registered plan. No interim look at any
delta: the extension from 24 to 32 blocks was decided at 09:40Z on clock and budget alone
and recorded in `RUNLOG.md` before the numbers existed.

### 5.1 The instrument, verified before the numbers are read

| check | result |
|---|---|
| configure receipts carrying `MAXTOK_OK max_tokens=90000` | **98 / 98** |
| head-log arm integrity (every request's `variant` == the run's arm) | **97 / 97 with a head log, 0 mismatches** (1 run predates head-log capture) |
| stock head, every run | `instr 45,842 ch + tools 38,477 ch` = **84,319 ch**, a single value across all 49 |
| V1 head, every run | `instr 21,654 ch + tools 26,595 ch` = **48,249 ch**, a single value across all 49 |
| head cut | **36,070 ch = 42.8%** — against `bji`/`skw3`'s published **44.0% of bytes** |
| stock head vs `bji`'s published census (84,665 ch) | **0.4% apart** |

**The treatment is on the wire, on the right provider, byte-identical run to run, in every
one of the 98 runs.**

### 5.2 `$/task` — the frozen rule applied verbatim, PER PROVIDER

> SHIP if $/task improves >=5% with the 95% CI excluding zero; HOLD if within +/-5%;
> REJECT if it worsens >=5% with CI excluding zero.

| estimator | n stock / V1 | stock | V1 | **Δ** | 95% CI | CI excl. 0 | MDE | **verdict** |
|---|---|---:|---:|---:|---|---|---:|---|
| **PRIMARY — VALID only (pre-registered)** | **11 / 8** | $5.7573 | $4.9763 | **−$0.7810 (−13.57%)** | **[−22.27%, −4.86%]** | **YES** | 12.25% | **SHIP** |
| sensitivity — ALL runs (pre-specified) | 49 / 49 | $4.7163 | $3.9418 | **−$0.7745 (−16.42%)** | **[−23.29%, −9.56%]** | **YES** | 9.68% | **SHIP** |
| secondary — block-paired (time-trend robust) | 7 pairs | — | — | **−$0.8314 (−14.44%)** | **[−26.83%, −2.06%]** | **YES** | — | **SHIP** |

> ### **Three estimators, three different selections, one sign, one magnitude — and, for the first time anywhere in this program, ALL THREE 95% CIs EXCLUDE ZERO.**

This is the thing `skw3` could not buy and said so: *"at any affordable n only HOLD is
reachable."* That was true **on terra**, where the effect is −6.9% and n=197/arm is needed.
It is **not** true on `claude-opus-5`, where the effect is **2× the size of the CI** at
n=11/8 — exactly the mechanism pre-registered in `PREREGISTRATION.md` §4.1: *required n is
not a constant, it scales as 1/δ², and δ is 4.2× larger on Anthropic.*

**And the HOLD/SHIP distinction here is not an artefact of low power.** The point estimate
clears the ±5% threshold by a factor of 2.7 and the CI's near bound (−4.86%) sits at the
threshold, not near zero.

### 5.3 **`B`, THE WHOLE REMAINING QUESTION — measured, and it is ~ZERO**

`B = Δtotal − D`, with `D = −$0.762/run` taken from `skw3` §3.4 (measured on the wire to 8
significant figures, not re-estimated here):

```
Delta_total (primary)  = -$0.7810
D           (skw3)     = -$0.7620
B                      = -$0.0190     =  -0.33% of the stock mean
```

| what `skw3` bounded | value | what this lane measured |
|---|---:|---|
| `B` needed for a **wash** on opus-5 | **+16.6%** | **−0.33%** |
| `B` needed to **cancel `D`** outright | **+21.6%** | **−0.33%** |
| largest `B` ever observed in this program | **+12.6%** | **−0.33%** |

> ### **`B` is not merely below the wash threshold — it is below ZERO. The lean head does not buy back its head saving with extra work on the daily driver. It does marginally LESS work.**

**Independently corroborated by the pre-registered request-count channel**, which is a
different measurement of the same quantity and does not pass through dollars at all:

| population | n stock / V1 | stock reqs | V1 reqs | Δ | 95% CI | excl. 0 |
|---|---|---:|---:|---:|---|---|
| ALL runs | 48 / 49 | 75.90 | 67.76 | **−8.14 (−10.73%)** | [−15.27%, −6.18%] | **YES** |
| VALID only | 10 / 8 | 81.60 | 71.88 | **−9.72 (−11.92%)** | [−20.01%, −3.82%] | **YES** |

**This reverses the direction `3d2` observed on terra** (+21.17 requests, **+24.5%**, n=2/3)
— and that reversal is the entire reason `B` had to be *measured* on Anthropic rather than
argued across from OpenAI. A `B` extrapolated from terra would have been wrong in sign.

*(The request channel is reported as a **PROXY** and deliberately **not** converted to
dollars — that conversion is the weakness `skw3` §5 named. The dollar answer is the
subtraction above, and the two agree in sign and rough magnitude without being the same
measurement.)*

### 5.4 Co-primary quality — clears, and the within-lane check agrees

**Cited, not re-measured** (`PREREGISTRATION.md` §7): `5zp`'s one-sided 95%
**LB −7.15 pp** against the frozen **−10 pp** margin (n 11 stock / 12 V1, power 0.82).
**CLEARS.**

This lane's own S7 recall, as a within-lane consistency check only — **not** a
re-derivation of the LB:

| arm | n (valid) | mean overall survival |
|---|---:|---:|
| stock | 11 | 0.9242 |
| **V1** | 8 | **0.9479** |

**The treated arm scores higher, not lower.** No sign of a quality regression at this cell.

> ## **BOTH PRIMARIES CLEAR ON `claude-opus-5`. THE RULE FIRES: SHIP.**

### 5.5 The per-provider verdict table — the choice fixed before the data

`PREREGISTRATION.md` §2 fixed **PER-PROVIDER** before any number existed, and it earned its
keep: the two providers do not return the same verdict, and a pooled statistic would have
described neither.

| provider | scenario | source | Δ `$/task` | CI excl. 0 | MDE | **verdict** |
|---|---|---|---:|---|---:|---|
| **anthropic `claude-opus-5`** | **S7** | **this lane, 98 runs** | **−13.57%** | **YES** | 12.25% | **SHIP** |
| openai `gpt-5.6-terra` | S7 | `skw3`, free corpus n 10/11 | −2.82% | no | 21.7% | **HOLD — underpowered, not a measured wash** |
| anthropic `claude-opus-5` | S3 | — | — | — | — | **NOT-POSSIBLE at $930** (§6) |
| openai `gpt-5.6-terra` | S3 | — | — | — | — | **NOT-POSSIBLE at $930** (§6) |

**Terra was deliberately not re-bought**, and the reason was pre-registered: its own `D` is
−6.9%, so firing the rule there needs **n = 103.4/arm ≈ 236 launches ≈ $760** — more than
the residue this lane finished with ($501.90). A partial terra purchase buys a tighter
HOLD, never a verdict, and `skw3` §1.1 showed that pooling terra runs across calendar
cohorts is confounded (cohort deltas +3.99% / −20.37%).

### 5.6 Validity, boundaries, and the cell-mismatch finding — measured

| arm | launched | valid | rate | mean boundaries |
|---|---:|---:|---:|---:|
| stock | 49 | 11 | **22.4%** | **3.08** |
| V1 | 49 | 8 | **16.3%** | **3.00** |

Against terra's published S7 figures (`skw3` §7): stock **7.00** boundaries, 1 of 14 below
the gate; V1 **6.72**, 3 of 18 below.

Two things follow, and the second is the one that matters:

1. **The S7-17 validity gate is calibrated for terra and does not fit `claude-opus-5`.**
   The same 17 turns produce less than half the boundaries, so ≥5 rejects ~80% of runs.
   **Falsifier #4 from `PREREGISTRATION.md` §8 fired**, and it is recorded as fired.
2. **On this cell the gate is very nearly ARM-NEUTRAL — 3.08 vs 3.00 mean boundaries.**
   That is *not* the terra picture, where the arms differed and the filter demonstrably
   discarded the cheap V1 runs. Here the filter removes runs from both arms at a similar
   rate and for the same cell-level reason, which is exactly why the VALID-only primary and
   the ALL-runs sensitivity land within **2.9 percentage points of each other** (−13.57% vs
   −16.42%) instead of diverging the way they did on terra (−2.82% vs −7.13%).
   **The pre-registered primary is not being carried by the filter.**

### 5.7 Cold starts and the contention hazard

No miss-mode signature appeared. Every run's head is byte-identical within its arm across
all 49 runs, per-run request counts are tight (stock sd 9.51, V1 sd 7.44 on means of 75.9 /
67.8), and the three estimators — including the **block-paired** one, which is immune both
to a monotone time trend and to the one un-drained arm switch disclosed in §4 — agree in
sign and magnitude. **`skw3`'s hazard was designed around rather than measured against**,
and this lane offers no new evidence on the open eviction-under-contention question
(`skw3` §6.1 item 1); it remains open and cheap (~$12).

---

## 6. WHAT IS **NOT-POSSIBLE** AT $930, AND WHAT WOULD CLOSE IT

| deliverable | state | why, with the arithmetic |
|---|---|---|
| `$/task` with a ±5% CI in **all four cells** | **NOT-POSSIBLE** | **$5,794–$9,596** vs $930 (§1.2). **6.2–10.3× over.** |
| ±5% CI on the **measured** cell (opus-5/S7) | **NOT-POSSIBLE** | at this cell's own realised sd, n = **55.6/arm** → `2×55.6 / 0.194 validity = 574 launches × $4.33` = **$2,484**. *(Note: **4× cheaper than `skw3`'s blended estimate implies**, because opus-5's realised cv is 0.106 against terra's 0.177 — a useful correction to the program's own cost model.)* |
| S3, either provider | **NOT-POSSIBLE — dropped in advance, named in `PREREGISTRATION.md` §4.2** | doubles the cell count against an authority already 6.2× short, and `D` is smaller on S3 in both providers |
| terra/S7 re-measurement | **NOT-POSSIBLE** | n = **103.4/arm → 236 launches × $3.217 = $760** > the **$501.90** residue |

**But note what the ±5% CI was FOR.** It was the instrument the rule needed to fire. **On
this cell the rule fired anyway**, at n=11/8, because the effect is 13.57% and not 5%. The
±5% deliverable is NOT-POSSIBLE **and the decision it existed to support has been made.**

---

## 7. WHAT THIS CHANGES

**Changes:**

1. **`B` is measured on Anthropic for the first time and it is ≈ 0 (−0.33%), not the
   +16.6% a wash would have required.** `00-what-we-know.md` §2l's open question — *"`B`
   remains unresolved, and remains the reason `Δtotal` cannot be settled at this budget"* —
   **is closed for `claude-opus-5`/S7.**
2. **`Δtotal` on the daily driver is −13.57%, CI [−22.27%, −4.86%], and the frozen rule
   returns SHIP** with the co-primary quality gate cleared (`5zp` LB −7.15 pp).
3. **The behavioural term has the opposite SIGN on the two providers** (−10.7% requests on
   opus-5 vs `3d2`'s +24.5% on terra). Extrapolating `B` across providers is not safe, and
   that is now measured rather than suspected.
4. **A live harness defect** (§2) that silently invalidates every S7/S5 run launched today,
   with a fix and a second recommendation for the driver's swallowed exit code.
5. **`claude-opus-5`/S7 is priced**: **$4.33/launch mean**, 22.4% / 16.3% arm validity,
   realised cv **0.106** — against `skw3`'s $3.53 estimate and terra's cv 0.177.
6. **The S7-17 validity gate does not fit `claude-opus-5`** (3.08/3.00 boundaries vs
   terra's 7.00/6.72) — a calibration item for whoever next runs S7 on Anthropic.

**Does NOT change:**

1. **The terra verdict.** `skw3`'s HOLD at −2.82% stands, still underpowered (MDE 21.7%),
   still **not** a measured wash. This lane bought no terra runs.
2. **The shipped default.** `PREREGISTRATION.md` §7 forbids it and `GOAL.md` forbids it.
   A **$0 CODE item** is filed instead, naming the head files and requiring the Anthropic
   non-regression guardrail.
3. **`D`.** Taken from `skw3` unchanged; this lane re-measured `Δtotal`, not `D`.
