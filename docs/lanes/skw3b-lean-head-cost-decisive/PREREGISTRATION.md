# `model_performance-g7h3` — PRE-REGISTRATION

**Written and committed with $0.00 spent. No API call precedes this file's commit.**

Item: `model_performance-g7h3` · Lane: `skw3b-lean-head-cost-decisive` · Date: 2026-09-06
Authority: **$930.00** · Repo: `amplifier-bundle-evaluation`

This document fixes, before any data is seen: the sign convention; the decision rule quoted
verbatim; **the pooled-vs-per-provider choice the item demands be fixed before the numbers
exist**; the affordability arithmetic that decides which deliverables are buyable at all; the
run-order design against the Anthropic cache-contention hazard; the analysis plan; and the
stopping rule. Nothing below is written after a number.

---

## 0. SIGN CONVENTION

**Negative = the lean head SAVES money.** Carried unchanged from `skw3` `PREREGISTRATION.md` §0
so the two lanes' numbers compose.

- `D` — the **direct / head** term: the cost difference at **byte-identical work**.
- `B` — the **behavioural** term: the cost difference caused by the treatment changing what the
  agent *does* (requests, tool calls, delegations, re-reads).
- `Δtotal = D + B`. `$/task` is `$/run` on S7-17 (one task per run, `n_sessions == 1`).

---

## 1. THE DECISION RULE — quoted verbatim from the work item

> **PRIMARY:** SHIP if $/task improves >=5% with the 95% CI excluding zero; HOLD if within
> +/-5% (a wash is not a reason to change a default); REJECT if it worsens >=5% with CI
> excluding zero.
> **CO-PRIMARY (carried from `5zp`):** quality non-inferiority, success LB >= -10 pp.
> **Both primaries must clear for SHIP.**

Applied verbatim to whatever numbers this lane ends with. Not re-worded, re-thresholded or
re-scoped after the fact.

**Gap-filling rule, carried verbatim from `skw3` §1.2 so the two lanes cannot disagree:** if the
point estimate lies outside ±5% but the 95% CI includes zero, the verdict is **HOLD** — neither
conjunction is satisfied and the item's own gloss ("a wash is not a reason to change a default")
is the conservative reading.

**Mechanical property, recorded now:** SHIP and REJECT each require a CI excluding zero. HOLD is
the only verdict reachable without one. Whether a HOLD means *measured wash* or *underpowered*
is the single thing this lane must never blur — `skw3`'s central complaint about the record.

---

## 2. THE POOLED vs PER-PROVIDER CHOICE — **PER-PROVIDER**, fixed here, before data

**Decision: the rule is applied PER PROVIDER. A pooled verdict is reported only as a
pre-specified secondary, and never overrides a per-provider one.**

Four reasons, all available before any number exists:

1. **The effect is 4.20× larger on Anthropic** (`skw3` §3.4: per-request head saving
   $0.0068350 vs $0.0016266). Pooling averages a large true effect against a small one and
   returns a number describing neither cell.
2. **The program's hard constraint is provider-scoped**: *"Anthropic is the daily driver and
   must not regress"* (`00-what-we-know.md` §1). A pooled statistic cannot discharge a
   constraint that names one provider.
3. **The mechanisms differ in kind, not degree.** On Anthropic the head survives a compaction
   boundary (one cold head write per session); on OpenAI every boundary is a guaranteed cold
   rebuild, 3–5 per run (`skw3` §3.3, `00-what-we-know.md` §2a). Pooling assumes a common
   estimand that has been *measured* not to exist.
4. **Pooling across strata is already known to be confounded here** (`skw3` §1.1: cohort deltas
   +3.99% / −20.37%). Adding a provider stratum on top of a time stratum compounds it.

**Consequence, accepted in advance:** this lane can return **different verdicts on the two
providers**, and that is a result, not an inconsistency.

---

## 3. AFFORDABILITY, COMPUTED BEFORE SPENDING

`GOAL.md`: *"Price the deliverable at the observed validity/failure rate on the first read of
this goal. If the arithmetic does not close, record that as the finding (branch B), spend
nothing you cannot use, and name the authority that WOULD close it."*

### 3.1 Inputs — every one a prior measurement, none new

| input | value | source |
|---|---|---|
| S7-17 terra `$/run`, stock, VALID | mean **$3.2170**, sd **$0.59528**, n=10 | `skw3` `t1_corpus.json` |
| S7-17 terra `$/run`, V1, VALID | mean **$3.12636**, sd **$0.54559**, n=11 | `skw3` `t1_corpus.json` |
| pooled sd | **$0.5696659** | `skw3` `t1_corpus.json` |
| realised MDE at n 10/11 | **21.676%** | `skw3` `t1_corpus.json` |
| **`n_needed_5pct`** | **196.896 → 197/arm** | `skw3` `t1_corpus.json` |
| S7 validity, stock | **13/14 = 92.86%** | `skw3` `t1_corpus.json` boundaries block |
| S7 validity, V1 | **15/18 = 83.33%** | same |
| S7 validity, both arms | **28/32 = 87.50%** | same |
| published V1 validity (conservative) | **67%** | `5zp`, used by `skw3` |
| observed per-launch price | terra S7 **$3.217** · opus-5 (S3) **$3.53** · terra (S3) **$4.63** · blended **$4.08** | `skw3`, `GOAL.md` KNOWN |
| `D` per task, all four cells | terra/S7 −$0.219 · terra/S3 −$0.125 · opus-5/S7 −$0.762 · opus-5/S3 −$0.369 | `skw3` §3.4 |
| largest `B` ever observed | **+$0.40 (+12.6%)** | `3d2` §4.3, via `skw3` §5.1 |

### 3.2 The n this lane uses — **the recomputed one**, and the calculation

`GOAL.md` deliverable 1: *"n = 197/arm, or the recomputed n from `skw3`'s own variance for
MDE <= 5% — state which and show the calculation."*

**This lane uses the RECOMPUTED n. It reproduces 197 exactly**, which is where the item's figure
came from:

```
z = z(0.975) + z(0.80) = 1.959964 + 0.841621        K = z^2 = 7.8489
sd_pooled (skw3, VALID pool, n 10/11)               = $0.5696659
delta = 5% of the stock mean $3.2170                = $0.160850
n_per_arm = 2 * sd^2 * K / delta^2
          = 2 * 0.3245191 * 7.8489 / 0.02587272     = 196.896  ->  197
```

Cross-check against `skw3`'s own closed form at `3d2`'s published sd $0.54 and mean $3.156:
**n = 183.8 → 184**. The item's "n~184-197" is exactly this pair of sd estimates. **197 is the
conservative member and is what this lane prices.**

Second, independent derivation from the realised MDE (no sd needed):
`n = n_harmonic × (MDE_obs / 5%)^2 = 10.4762 × (21.676/5)^2 = 196.9`. **Same answer.**

### 3.3 What the item's literal deliverable costs — and it does not close

Deliverable: `$/task` per arm **per provider per scenario** with a 95% CI able to fire a ±5%
rule, over **2 arms × 2 providers (gpt-5.6-terra, claude-opus-5) × 2 scenarios (S7, S3)**.

```
n per arm                                    = 197
valid runs per cell (2 arms)                 = 394
cells (2 providers x 2 scenarios)            = 4          ->  1,576 valid runs
launches at 87.50% measured validity         = 1,801
launches at 67% published V1 validity        = 2,352

cost, best case  1,801 x $3.217 (cheapest observed)       = $5,794
cost, skw3 basis 2,352 x $4.08  (blended)                 = $9,596
```

**$5,794 – $9,596 against a $930 authority — 6.2× to 10.3× over. NOT-POSSIBLE.**

And it does not close by any reallocation inside $930:

| reduced design | valid runs | launches @87.5% | cost @$3.217 | vs $930 |
|---|---:|---:|---:|---|
| all 4 cells, ±5% (the deliverable) | 1,576 | 1,801 | **$5,794** | 6.2× |
| **one** cell only, ±5% | 394 | 450 | **$1,449** | **1.6×** |
| all 4 cells, ±10% (n=49.2/arm) | 394 | 450 | **$1,449** | 1.6× |
| all 4 cells, ±20% (n=12.3/arm) | 98 | 112 | **$362** | affordable, MDE 20% |

**Even the single cheapest cell at ±5% is 1.6× over the authority.**

**PRE-REGISTERED CONSEQUENCE, fixed now:** deliverable 1, read as *a CI able to fire the ±5%
rule in all four cells*, is **NOT-POSSIBLE at $930**. Recorded as **OUTCOME BRANCH B**; the item
is still **resolved**. **The authority that WOULD close it is $5,794 (best case) to $9,596
(`skw3`'s blended basis).**

### 3.4 The cap's own arithmetic does not close either — reported as a goal defect

`GOAL.md` Procedure 3 AUTHORING RULE requires a run-buying cap to be stated as
`runs × arms × per-run estimate / validity rate = cap`, and instructs the lane to report a cap
that fails this **as a finding, not a gap to absorb**. This cap states, in full:

> *"SPEND AUTHORITY for this item: **$930** — owner-funded at the decisive number; `skw3` priced
> the B-term at **~$810**."*

**Three defects, all knowable on first read:**

1. **No arithmetic is shown at all.** No run count, no arm count, no validity divisor. The rule
   requires the arithmetic; a bare figure plus a citation is what the rule forbids.
2. **The $810 is a price for a DIFFERENT, SMALLER design.** Traced to source: `skw3` §5 quotes
   *"`3d2` §4.4 already priced the dollar test at **n ≈ 126/arm ≈ $810**"* — that is **one cell**
   (terra/S7), at **n=126**, sized to `3d2`'s *observed* 6.1% effect, **not** to the ±5%
   threshold. This goal's deliverable is **n=197/arm across four cells** — 6.25× more valid runs.
   Reusing a price quoted for a smaller set on a larger one is **verbatim the `1ru` defect this
   same paragraph forbids** ("a price quoted for a smaller set may not be reused for a larger
   one").
3. **`skw3` had already priced *this* goal's deliverable, in the same document, at $8,964**, and
   that figure — not $810 — is the one the cap should have been built from.

**This lane does not absorb the gap.** It records the defect, buys what the authority *can* buy
(§4), and names the authority that would close the stated deliverable (§3.3).

---

## 4. WHAT $930 *CAN* DECISIVELY BUY — the design, fixed before data

### 4.1 The load-bearing observation: required n is not a constant

`skw3`'s n=197 is computed at **δ = the 5% threshold**. But the rule fires when the CI excludes
zero *at the true effect*, and required n scales as `1/δ²`. With
`cv = sd/mean = 0.5696659/3.2170 = 0.177084` (terra/S7, the only S7 cv that exists):

| true effect δ | n/arm for 80% power | where this δ comes from |
|---:|---:|---|
| 5.0% | **196.9** | the rule's threshold (the unaffordable deliverable) |
| 6.9% | 103.4 | `D` alone, terra/S7 |
| 9.0% | **60.8** | **`D` on opus-5/S7 (−21.6%) + `B` at its historical maximum (+12.6%)** |
| 10.4% | 45.5 | `D` alone, opus-5/S3 |
| 16.6% | 17.9 | the `B` a wash on opus-5/S7 would require (`skw3` §5.1) |
| 21.6% | **10.6** | **`D` alone, opus-5/S7 (i.e. if `B` ≈ 0)** |

**On `claude-opus-5` / S7 the program's own published bounds put `Δtotal` in [−21.6%, −9.0%],
so n between 11 and 61 per arm fires the rule.** That is inside this authority. On terra/S7 the
same bounds put `Δtotal` in [−6.9%, +5.7%], needing n ≥ 103 and possibly n = ∞ (a true wash),
which is not.

**This is why the money goes to Anthropic.** It is also the cell the hard constraint names, and
the cell in which `Δtotal` has **never been measured at all** (`skw3` §6.1 open question 2).

### 4.2 The purchase, in priority order

| # | purchase | why | pre-registered stop |
|---|---|---|---|
| **P0** | **$0**: this file; the `opus5-medium` arm file; the free grader canary | no API call | — |
| **P1** | **price/validity smoke**: 1 stock + 1 V1 end-to-end `opus-5` / S7-17 run | **the opus-5 S7 per-run price has never been observed** (`skw3` §6.2 explicitly flags it). Everything below is priced off it. | tripwire **$30** |
| **P2** | **bulk**: `opus-5` / S7-17, ABBA arm-blocked, toward **n = 61/arm** | the decisive cell (§4.1) | budget rule §6 |
| **P3** | *(only if P2 completes under budget)* terra / S7-17 top-up toward n = 103/arm | second provider, per-provider rule | budget rule §6 |

**S3 is dropped in advance and named here, not silently** (`GOAL.md` OPTIONAL-IF-CAP-PERMITS):
adding S3 doubles the cell count against an authority already 6.2× short, and `D` on S3 is
smaller in both providers (−8.1% / −10.4% vs −6.9% / −21.6% as a share of a run), so S3 is
strictly the *less* decisive scenario per dollar. **S3 will be recorded NOT-POSSIBLE with this
reason.**

### 4.3 The new cell, and its one honest caveat

`scenarios/s7-retention-headroom/arms/` holds `haiku-high`, `sonnet-high`, `terra-medium` only.
This lane creates **`opus5-medium`** (`provider_id: opus`, `model: claude-opus-5`,
`effort: medium`) **inside its own capture root**, never in the shared scenario directory
(`GOAL.md` 0rg hazard).

- `effort: medium` is chosen to match `terra-medium`'s rung and because the effort dial points
  **down** for opus-5 (`00-what-we-know.md` §2c: S3 85 vs 70, 5/5 vs 1/5, cheaper *and* faster).
- **Caveat, stated in advance** (`skw3`'s own objection, and it is right): this cell is
  **incomparable to the published S7 terra population**. It is used here **only** for a
  **within-cell A/B** — stock vs V1 on the same cell, same instrument, same window — which is
  exactly the estimand `Δtotal` needs and does not require cross-cell comparability.
- **`cv` is imported from terra/S7** for the power calculation because no opus-5 S7 `cv` exists.
  **The realised opus-5 `cv` will be reported**, and if it exceeds terra's the achieved MDE will
  be reported against it, not against the planned one.

### 4.4 Instrument, frozen — S7-17, byte-identical to every published S7 bound

`--max-tokens 90000 --max-turns 17 --constraints-file constraints_t17.json --min-boundaries 5`,
seed `ledger_tail6=7205ec`. **Not free variables** (`SPEC.md` §9.1). Moving either turn limit or
boundary gate makes these runs incomparable to every published bound, which `5zp` established.

**Expected V1 invalidity is the treatment's own mechanism, not a rig defect** (`5zp`;
`skw3` §7): the lean head fills the 90k window ~31% slower, crosses the cap fewer times inside a
frozen turn limit, and is failed by the ≥5-boundary gate for working as intended. Measured rate
**3/18 = 16.7% V1 vs 1/14 = 7.1% stock**. **Budgeted at 87.50% blended validity in §3.3 and §6.**
Pre-registered: the VALID-only analysis is **primary**; the ALL-runs analysis is a
**pre-specified sensitivity**, because filtering to VALID is known to discard the *cheap* V1 runs
and therefore biases **against** the treatment (`skw3` §7).

---

## 5. RUN ORDER — designed against the Anthropic cache-contention hazard

**The hazard** (`skw3` §4, and `GOAL.md` states it as a design requirement): two chains with
**different heads run back to back** contend for the Anthropic conversation cache; a miss costs
**~$0.065/request**; a single-arm control (same head, two chains) showed **0 misses in 4/4
chains**. Not closed at n=7 pairs. **Interleaving arms inside one process can manufacture a sign
reversal.**

**THE DESIGN, fixed here:**

1. **Arm-blocked in time. Never two different heads live simultaneously, anywhere, on the
   account.** A block is *k* concurrent runs of **one** arm across the DTUs. The next block does
   not start until the current block has fully drained.
2. **≥6-minute drain between blocks of different arms** — longer than Anthropic's 5-minute cache
   TTL, so the outgoing head's entries expire before the incoming head is written. This is the
   structural version of `skw3`'s single-arm control.
3. **ABBA block sequence** (`S,V,V,S,S,V,V,S,…`) so the calendar-time trend is balanced across
   arms. This is required, not cosmetic: `skw3` §1.1 measured cohort deltas of **+3.99% /
   −20.37%** — roughly **6× the effect the ±5% rule is trying to detect** — and a pure
   all-stock-then-all-V1 blocking would confound the treatment with that trend entirely.
4. **Block index is recorded as a stratum.** Pre-specified secondary estimator: **block-paired**
   (each S block matched to its adjacent V block), which is immune to a monotone time trend.
5. **Rejected alternative, and why**: `3d2` ran the two arms **concurrently** in two containers
   so both saw the same latency window. That is the best time-trend control available and the
   **worst** contention control — it puts two different heads live at once by construction,
   which is precisely the configuration `skw3` measured a miss mode in. ABBA blocking buys most
   of the time-trend control at none of the contention risk.
6. **Disclosed in advance — concurrency *within* an arm may share a head.** Three concurrent runs
   of the same arm present an identical prefix and may read one another's cache entry rather than
   each paying a cold write. **Direction of the bias is known and it is conservative:** it
   shrinks the head term `D` in both arms, and `D` is the negative (pro-treatment) term, so
   sharing attenuates the measured saving. A SHIP verdict under attenuation is a stronger SHIP,
   not a weaker one. **It will be measured, not assumed:** cold starts (`cache_read == 0`) per
   run per arm are counted and reported.

---

## 6. STOPPING RULE AND BUDGET DISCIPLINE

Carried in form from `skw3` §5, with the numbers re-derived for this authority.

```
LAUNCH the next block iff
    cumulative_spend + (block_size x worst_observed_single_run_cost) <= $930.00
worst_observed_single_run_cost is revised UPWARD ONLY,
    seeded at $4.63 (the most expensive per-run price in GOAL.md KNOWN)
    and replaced by the observed opus-5/S7 price after P1 if that is higher.
```

- **Blocks are bought on budget and clock alone — never on results.** There is **no interim
  analysis of the primary endpoint**. The primary is computed once, at the end, on whatever n
  was reached. This is what keeps the design from becoming a peeking rule.
- **PRE-REGISTERED PRICE GATE:** n=61/arm costs `122 valid / 0.875 = 140 launches`. At $930 that
  is affordable iff the observed opus-5/S7 price is **≤ $6.64/run**. If P1 returns a price above
  $6.64, **n=61 is NOT-POSSIBLE and this lane buys the largest n the authority funds**, reporting
  the achieved MDE against the 5% threshold rather than shrinking the threshold.
- **Residue rule** (`GOAL.md` SCOPE-OUTS): stop when the residue cannot buy the smallest
  indivisible purchase that advances a deliverable. **The smallest useful purchase here is one
  ABBA block-pair = 2 blocks = 6 launches.** The residue and the purchase it could not buy are
  both stated in the DONE-NOTE.
- Every purchase decision is appended to `RUNLOG.md` **before** the purchase, with its
  arithmetic.

---

## 7. ANALYSIS PLAN — fixed before data

**Primary, per provider** (§2): Welch's unequal-variance t on `$/run`, VALID runs only, two-sided
95% CI, reported as absolute dollars and as a percentage of the **stock** arm mean. The rule of
§1 is then applied verbatim. **The achieved MDE is reported alongside every verdict**, so a HOLD
is always labelled *measured wash* or *underpowered*.

**Pre-specified secondaries** (reported, never substituted for the primary):

1. **ALL-runs sensitivity** (VALID + invalid), for the anti-conservative-filter reason in §4.4.
2. **Block-paired estimator** (§5.4), immune to a monotone time trend.
3. **`B`, isolated**: `B = Δtotal − D`, with `D` taken from `skw3` §3.4 (measured on the wire to
   8 significant figures: opus-5 −$0.762/run on S7). This is the item's actual question and it
   is a subtraction, not a new measurement.
4. **`B` via the request-count channel**: `Δrequests` between arms, with its own CI. `3d2`
   observed +21.17 requests (+24.5%); `skw3` computed n\* = 5.01/arm for that counter, so it
   resolves at an n this lane will exceed. Reported as a **proxy**, and explicitly *not*
   converted to dollars, because that conversion is the weakness `skw3` §5 named.
5. **Cold-start counts** per run per arm (§5.6), and **boundary counts** per arm (the validity
   mechanism).

**Co-primary quality:** **cited, not re-measured** — `5zp`'s one-sided 95% **LB −7.15 pp**
against the frozen **−10 pp** margin (n 11 stock / 12 V1, power 0.82). Re-buying the quality arm
was not funded by this item and the item does not ask for it. **This lane's own S7 recall scores
are reported per arm as a within-lane consistency check only, and are explicitly NOT a
re-derivation of the LB.**

**Pre-registered SHIP consequence:** if and only if **both** primaries clear on a provider, this
lane files a **$0 CODE item** naming the exact head file(s) and requiring the Anthropic
non-regression guardrail. **No default is changed inside this lane.**

---

## 8. WHAT WOULD FALSIFY THIS LANE'S OWN RESULT

Stated before the data, so it cannot be chosen afterwards:

1. **A realised opus-5/S7 `cv` materially above terra's 0.1771** — the power table in §4.1
   collapses and the achieved MDE must be reported against the realised `cv`.
2. **Cold starts < 1 per run** — concurrency inside a block is sharing heads, `D` is attenuated,
   and the measured `Δtotal` understates the saving (§5.6).
3. **A block-paired estimator that disagrees in sign with the pooled one** — the time trend is
   doing the work, exactly as `skw3` §1.1 warned; the block-paired estimate then governs.
4. **V1-arm validity materially below 83.3%** — the treatment's own mechanism is stronger on
   this cell than on terra, the launch budget in §3.3/§6 is wrong, and the achieved n is lower
   than planned.
5. **A `B` larger than +16.6% on opus-5** — the bound in `skw3` §5.1 is broken and the lever is a
   wash on the daily driver after all. This is the outcome this lane exists to be able to see.
