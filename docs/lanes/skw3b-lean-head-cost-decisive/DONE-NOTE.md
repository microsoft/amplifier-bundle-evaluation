# `model_performance-g7h3` — DONE-NOTE

**Lane:** `skw3b-lean-head-cost-decisive` · **Item:** `model_performance-g7h3`
**Date:** 2026-09-06 → 2026-09-07 · **Authority:** $930.00 · **Spent:** **$428.10**
**Pre-registration:** `PREREGISTRATION.md`, committed **`741a71b`** at **$0.00 spent**
**Outcome branch:** **B** — resolved, with two deliverables recorded NOT-POSSIBLE with arithmetic

---

## THE ANSWER, IN ONE PARAGRAPH

`B` — the behavioural term, which `skw3` named as *"the whole remaining question"* — **is
now measured on the daily driver and it is ≈ ZERO (−0.33%)**, against the **+16.6%** a wash
would have required and the **+12.6%** largest `B` ever observed in this program. 98
end-to-end `claude-opus-5`/S7-17 runs, 49/arm, put `Δ$/task` at **−13.57%, 95% CI
[−22.27%, −4.86%]** — and **all three pre-registered estimators exclude zero, the first
time that has happened anywhere in this program.** With `5zp`'s quality co-primary
clearing at **LB −7.15 pp**, **both primaries clear and the frozen rule fires SHIP on
`claude-opus-5`.** No default was changed here; the **$0 CODE item is
`model_performance-zc6t`**. Terra is unchanged and still **HOLD-because-underpowered**.

---

## DELIVERABLES

| # | deliverable | state |
|---|---|---|
| 1 | **n = 197/arm or the recomputed n, stated and shown** | **DONE** — recomputed: `2(0.5696659²)(7.8489)/0.160850² = 196.896 → 197`, reproducing `skw3`'s own `n_needed_5pct` field to 3 decimals; confirmed a second way from the realised MDE (`10.4762 × (21.676/5)² = 196.9`). `FINDINGS.md` §1.1 |
| 2 | **S7 AND S3, both providers** | **NOT-POSSIBLE** (see below) — **1 of 4 cells measured**, and it is the decisive one |
| 3 | **Pre-registration committed BEFORE the first run, SHA quoted, pooled-vs-per-provider fixed** | **DONE** — `741a71b`, **$0.00 spent**, **PER-PROVIDER**, with four pre-data reasons. `PREREGISTRATION.md` §2 |
| 4 | **$/task per arm per provider per scenario with n and a 95% CI, frozen rule applied verbatim** | **DONE for opus-5/S7** (n 11/8 valid of 49/49 launched; −13.57%, CI [−22.27%, −4.86%]; **SHIP**) · **carried forward for terra/S7** (`skw3`, n 10/11, −2.82%, **HOLD**) · **NOT-POSSIBLE for both S3 cells** |
| 5 | **Co-primary quality vs the −10 pp margin; both must clear for SHIP** | **DONE** — cited from `5zp`: LB **−7.15 pp** vs −10 pp, **CLEARS**; within-lane check agrees (V1 0.9479 vs stock 0.9242). **Both primaries clear → SHIP** |
| 6 | **Run order designed against interleaved-arm cache contention, stated explicitly** | **DONE** — arm-blocked, one arm live at a time, ≥6-min drain across every arm switch, ABBA sequence, block as a stratum. `FINDINGS.md` §4. **One deviation disclosed** (b03→b04 un-drained) |
| 7 | **Expect and budget for the treatment's own validity mechanism** | **DONE, and it went further than expected** — measured 22.4% stock / 16.3% V1 validity, mean boundaries **3.08 / 3.00** vs terra's 7.00 / 6.72. The S7-17 gate is **mis-calibrated for opus-5 and hits both arms nearly equally**. `FINDINGS.md` §5.6 |
| 8 | **If SHIP: file a $0 CODE item naming the exact head file(s) + the Anthropic guardrail; ship no default here** | **DONE** — **`model_performance-zc6t`**. No default shipped in this lane |

### The two NOT-POSSIBLE reasons — **what was EXECUTED comes first**

**(a) `$/task` with a ±5% CI in all four cells.**
**EXECUTED: 98 end-to-end `claude-opus-5`/S7-17 runs (49 per arm), 32 ABBA blocks across 3
DTUs over ~9.5 hours; 98 of 98 configure receipts carrying `MAXTOK_OK max_tokens=90000`;
97 head logs with 0 arm mismatches and ~7,400 per-request head records; 3 pre-registered
estimators plus 2 independent request-count channels; the opus-5/S7 cell priced for the
first time in this program; a live harness defect diagnosed to root cause and fixed.**
What could **not** be bought is the **sample size for the other three cells**:
197/arm × 2 arms × 4 cells = 1,576 valid runs = 1,801–2,352 launches = **$5,794–$9,596**
against **$930** — **6.2× to 10.3× over**, computed and committed before the first API
call. Even the single cheapest cell at ±5% is $1,449, still 1.6× over. **The authority
that would close it is $5,794 (best case) to $9,596.**
**And note what the ±5% CI was for: it was the instrument the rule needed. On the cell that
matters, the rule fired anyway at n=11/8, because the effect is 13.57%, not 5%.**

**(b) S3, either provider.** **Dropped in advance and named** (`PREREGISTRATION.md` §4.2,
committed before spending): S3 doubles the cell count against an authority already 6.2×
short, and `D` is smaller on S3 in both providers (−8.1% / −10.4% of a run vs −6.9% /
−21.6%), so S3 is strictly the less decisive scenario per dollar.

---

## SPEND — to the cent, with arithmetic

| # | item | $ |
|---|---|---:|
| 1 | `VOID-noconfig-stock-r01` — bought the harness defect, not a datum (§2 of FINDINGS) | 3.8500 |
| 2 | P1b price/validity smoke, 1 stock (`$6.72`) + 1 V1 (`$4.03`), sequential | 10.7500 |
| 3 | ABBA blocks b03–b26 (pre-registered 24-block sequence) + b27–b34 (extension) | 413.5000 |
| | **TOTAL** | **$428.10** |

```
98 launches x $4.3291 mean observed per-launch price = $424.25
+ 1 VOIDED launch at $3.85                          = $428.10
achieved validity: stock 11/49 = 22.4% ; V1 8/49 = 16.3%   (planned 87.5%)
```

**Observed per-run price, stated BEFORE the bulk spend** (`RUNLOG.md` entry 2): the first
valid opus-5/S7 stock run returned **$6.72** — above the pre-registered price gate of
**$6.64**, which under `PREREGISTRATION.md` §6 made the n=61/arm target NOT-POSSIBLE and
sent this lane to *"the largest n the authority funds, reporting the achieved MDE"*. The
realised mean across 98 launches was **$4.3291**, because most runs are cheaper than that
first one.

### Residue, and the smallest purchase it could not buy

**Residue: $501.90.** It is **spendable and deliberately unspent** — this is not `1ru`'s
unspendable-residue situation. Nothing buyable at $501.90 changes a verdict:

| candidate purchase | price | vs $501.90 |
|---|---:|---|
| ±5% CI on the measured cell (opus-5/S7): `2 × 55.6 / 0.194 = 574 launches × $4.33` | **$2,484** | 4.9× over |
| terra/S7 re-measurement at its own `D` (−6.9%): `n=103.4/arm → 236 launches × $3.217` | **$760** | 1.5× over |
| the stated 4-cell deliverable | **$5,794–$9,596** | 11.5×–19.1× over |
| more opus-5/S7 runs | any | **cannot change the verdict** — all three estimators already exclude zero and agree in sign and magnitude; more n tightens a CI that has already fired |

**The smallest purchase that would advance an open deliverable is $760** (terra/S7).
**$501.90 does not buy it.**

---

## DECISIONS THIS LANE MADE WITHOUT A HUMAN

1. **PER-PROVIDER, not pooled** — fixed at `741a71b` before data. It earned its keep: the
   two providers return different verdicts.
2. **Concentrate the authority on `claude-opus-5`/S7** rather than spreading it over four
   cells at an n that could fire in none of them. Reason pre-registered
   (`PREREGISTRATION.md` §4.1): required n scales as 1/δ², and δ is 4.2× larger on
   Anthropic, so 11–61/arm suffices there against 103–∞ on terra.
3. **Do not re-tune the S7-17 profile** when opus-5 turned out to fail its validity gate.
   `SPEC.md` §9.1 freezes it and `5zp` established that moving it makes runs incomparable
   to every published bound. **The invalidity is reported as a finding, not fixed by
   turning a knob mid-comparison.**
4. **Do not switch primaries after seeing the numbers.** The VALID-only primary stayed
   primary. The collider argument for preferring the ALL-runs view (`FINDINGS.md` §3.2) is
   labelled **post-hoc** and changed no verdict — both views return SHIP anyway.
5. **Extend from 24 to 32 blocks** — decided at 09:40Z **on clock and budget alone**, and
   recorded in `RUNLOG.md` entry 3 **before any delta was computed**.
6. **Stop at $428.10 with $501.90 unspent** — see the residue table.

---

## DEVIATIONS, DISCLOSED

1. **One un-drained arm switch.** The block runner was killed with its launching shell and
   restarted at block 04 with no memory of the previous arm, so **b03 (V1) → b04 (stock)
   ran with no 6-minute drain**. Every other arm switch drained 360 s. The block-paired
   estimator, which is robust to it, agrees with the other two (−14.44%, CI excluding
   zero).
2. **One VOIDED run kept and paid for** (`VOID-noconfig-stock-r01`, $3.85). It is excluded
   from every analysis and is the run that found the harness defect.
3. **The P1 smoke runs are included in the primary analysis** as blocks 01 (S) and 02 (V) of
   the ABBA sequence, each of size 1. `PREREGISTRATION.md` did not say either way; stated
   here rather than left implicit.
4. **The lane's own patched `configure_cell_g7h3.py` was used with `--skip-configure`.** The
   shared `_harness/configure_cell.py` was **not edited** (0rg hazard); the fix ships as
   `skw3b-configure-cell-anchors-fallback.diff`.
5. **One run has no head log** (`g7h3-s-b01-r01`) — it predates per-block head-log capture.
   97 of 98 are covered, 0 mismatches.

---

## CHECKS RUN, INCLUDING THE ONES THAT COULD HAVE EMBARRASSED THIS LANE

| check | result |
|---|---|
| **`mikb` DTU split-state trap** (bundle cache newer/older than `site-packages`) | **ABSENT, and checked rather than assumed** — 1 provider-anthropic copy in the cache, **0** outside it; `amplifier 2026.09.06-be25afd (core 1.6.1)` |
| **free S7 grader canary** | reproduces the **committed** `selftest_summary.json` **cell-for-cell** (perfect 1.0 / inband 0.6667 / mid 0.4242 / degraded 0.0909 / blind 0.0). ⚠ `ordering_ok` is **`false`** — **and it is `false` in the committed reference too**: the flag also requires two `calibration.verdict` values that the canary's own synthetic runs can never produce (`grader.py` short-circuits `calib["verdict"] = validity_verdict` when `not valid`). **The README's "must print `ordering_ok: true`" is unsatisfiable against the shipped grader**, and the *discriminating* content — strict monotone ordering, perfect==1.0, blind==0.0 — **passes**. A lane obeying the README literally would refuse to spend and report BLOCKED, incorrectly. Reported, not absorbed |
| **`t_crit` implementation** | verified against **7** known values including `skw3`'s own `df=18.35869 → 2.09813` |
| **configure receipts** | **98 / 98** carry `MAXTOK_OK max_tokens=90000`; `run_arm.sh` refuses to launch without it |
| **head-log arm integrity** | **97 / 97, 0 mismatches**; head byte counts a **single value per arm** across all 49 runs |
| **stock head vs `bji`'s published census** | 84,319 ch measured vs 84,665 ch published — **0.4%** |
| **V1 head cut vs published** | **42.8%** measured vs **44.0% of bytes** published |
| **full repo test suite** | see the PR body |

---

## FOR THE MANAGER — proposed edit to shared notes (this lane did NOT edit them)

`skw3b-00-what-we-know.diff` in this directory. It amends `§2l` — whose current text says
*"`B` remains unresolved, and remains the reason `Δtotal` cannot be settled at this
budget"* — and adds the opus-5 result. **`GOAL.md`'s 0rg hazard forbids this lane from
editing `ai-notes/00-what-we-know.md` or `probes/INDEX.md`, and it did not.**

Also for the manager, and more urgent than the note edit:
**`skw3b-configure-cell-anchors-fallback.diff`** — the S7/S5 compaction knob is dead on
today's `amplifier-foundation@main` and **every S7/S5 run launched today is silently
INVALID**. Other lanes are running right now.

---

## OPEN, AND NAMED RATHER THAN BURIED

1. **Terra's `Δtotal` is still unresolved** — HOLD at −2.82% with MDE 21.7%, and that is
   *underpowered*, **not** a measured wash. Needs **$760** to fire at its own `D`.
2. **Both S3 cells are unmeasured.**
3. **`skw3`'s eviction-under-contention question stays open** (~$12). This lane designed
   around the hazard rather than measuring it, and adds no evidence either way.
4. **The S7-17 profile needs recalibrating for Anthropic** before anyone runs S7 on opus-5
   again — 3.08/3.00 boundaries against a ≥5 gate is an ~80% rejection rate in **both**
   arms.
5. **`B` has the opposite sign on the two providers** (−10.7% requests on opus-5 vs `3d2`'s
   +24.5% on terra). Why is unexplained. It is measured, not understood.
