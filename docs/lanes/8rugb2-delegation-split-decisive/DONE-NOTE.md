# DONE-NOTE — `model_performance-njpd`

**Decisive evaluation of foundation PR #369 (delegation-context split).**

## VERDICT: **NO-SHIP**

**The deciding number: the `opus` delegation ratio is `0.4737`, against a frozen
band of `[0.70, 1.30]`.** The split **more than halves** Anthropic's delegation
count. Measured at n=26 valid runs per arm — 6.5x `8rugb`'s n, same direction,
further outside the band (`8rugb` saw 0.667 at n=4).

The frozen rule, applied verbatim, unchanged, never re-derived:

> **SHIP iff success LB >= -5 pp AND delegation count within +/-30% of main.**

| Gating condition | Measured | Floor / band | |
|---|---:|---|---|
| **COND 1** — success LB, pooled | **-5.55 pp** | `>= -5.00 pp` | **FAIL** by 0.55 pp |
| **COND 2** — delegation ratio, `opus` | **0.4737** | `[0.70, 1.30]` | **FAIL** |
| **COND 2** — delegation ratio, `terra` | **1.1752** | `[0.70, 1.30]` | PASS |

`SHIP` requires all three. **NO-SHIP.**

---

## 1. THE RESULT IS NOT "THE SPLIT IS WORSE"

This matters and must not be lost in the verdict. **On every quality and cost
measure the split came out AHEAD:**

| | arm A (main) | arm B (split) | |
|---|---:|---:|---|
| success, pooled | **32/51** (62.75%) | **39/52** (75.00%) | **+12.25 pp for B** |
| S3 score, `opus` | 80.88 | 79.92 | tied |
| S3 score, `terra` | 75.00 | **84.04** | **+9.04 for B** |
| $/run, `opus` | $6.5354 | **$5.8924** | **-9.8% for B** |
| $/run, `terra` | $6.9969 | **$6.7286** | **-3.8% for B** |

Condition 1 fails on **interval width**, not on a measured regression — the same
diagnosis `8rugb` made, now confirmed at 7.4x its n. The point estimate is
**+12.25 pp in the split's favour**; the lower bound simply has not closed.

**What kills it is condition 2, and only on Anthropic.**

---

## 2. THE SECONDARY THAT EXPLAINS THE VERDICT: FAN-OUT WIDTH

Pre-registered as measured-never-gating (`PREREGISTRATION.md` §8). It is the
mechanism behind condition 2, and it is unambiguous.

**`opus` — spawns per delegating turn:**

| | distribution | mean | delegating turns |
|---|---|---:|---|
| arm A | **{1: 2, 2: 18}** | **1.90** | 20 |
| arm B | **{1: 14, 2: 2}** | **1.125** | 16 |

**18 of 20 arm-A delegating turns spawn exactly two agents. 14 of 16 arm-B turns
spawn exactly one.** The burst distribution is *identical* to the per-turn
distribution, which means every one of those pairs is dispatched inside a 5-second
window — **genuinely parallel, one tool-call batch.** The split collapses
Anthropic's paired parallel fan-out to a single spawn.

`8rugb` called this exactly right at n=4 ("arm A spawns two parallel explorers,
arm B one"). It holds at n=26.

**`terra` — the opposite direction, and a different mechanism:**

| | per-turn mean | per-turn max | **burst** mean | delegating turns/run |
|---|---:|---:|---:|---:|
| arm A | 3.646 | 12 | **1.346** | 3.16 |
| arm B | **4.632** | **22** | **1.239** | 2.923 |

Terra delegates *more* per turn under the split — but its bursts are ~1.3, i.e.
**terra's delegations are essentially SEQUENTIAL, not parallel.** That is the
reason the two providers move in opposite directions, and it is new: the
treatment removes a block of always-loaded delegation prose, and a model that
fans out in parallel loses a spawn while a model that iterates sequentially adds
iterations.

---

## 3. THE PRE-REGISTERED CHOICE IS WHAT DECIDES THIS, AND IT WAS MADE FIRST

`PREREGISTRATION.md` (committed **`68b3b68e7a28ba02d404675cf2d624bcb751a020`**,
before run 1) fixed condition 2 as **PER-PROVIDER**. The consequence, disclosed
then and confirmed now:

| condition 2 evaluated | ratio | result |
|---|---:|---|
| **PER-PROVIDER (pre-registered, GATING)** | `opus` **0.4737** / `terra` 1.1752 | **FAIL** |
| POOLED (disclosed, NON-GATING) | **1.1131** | would PASS |

**Pooled would have shipped this.** The per-provider choice is the whole verdict,
and it was fixed before any number of this lane existed, on three stated grounds:
the program's hard "Anthropic is the daily driver and must not regress"
constraint; the incoherence of pooling counts that differ ~9x in scale
(`opus` mean 1.46, `terra` mean 11.52); and continuity with `8rugb`.

This is precisely the failure mode the hard constraint exists to catch: **an
OpenAI gain (+17.5% delegation, +9 quality points, cheaper) masking a 53%
collapse in Anthropic delegation.**

**Robustness — the prior stratum is not driving anything.** Dropping `8rugb`'s
14 runs and analysing this lane's 89 alone: LB **-5.29 pp**, `opus` **0.4375**,
`terra` **1.1732**, verdict **NO-SHIP**. Same answer, same deciding condition.

---

## 4. **THE LOAD-BEARING FINDING: n=73 WAS NEVER GOING TO WORK EITHER**

The item bought "the n at which `8rugb`'s own rule can finally decide". **73 is
not that n**, and this is the single most important thing this lane learned.

`8rugb`'s power calc is `best-case LB = -(1 - wilson_lower(n, n))`, giving
n=73 -> -5.00 pp. **That bound is attained only when BOTH arms score 100%.** S3
does not do that — pooled success measured here is **0.6893**.

| success rate assumed | LB at n=73/arm | n/arm needed for LB >= -5 pp | cost at $6.7822/launch |
|---|---:|---:|---:|
| 1.000 (`8rugb`'s assumption) | -5.00 pp | 73 | **$990** |
| 0.857 (`8rugb`'s **own** observed 6/7) | — | **380** | **$5,154** |
| **0.6893 (measured here, 71/103)** | **-14.80 pp** | **655** | **$8,885** |

**Condition 1 was arithmetically unsatisfiable at n=73 for the same reason it was
unsatisfiable at n=3 — the target n was computed from a formula the data does not
satisfy.** Even the best-case n=73 costs **$990** at the observed price, already
above the $880 authority before the success rate enters at all.

A caution for whoever picks this up: **the LB is not monotone in n at fixed
observed rates**, because the integer pass-counts re-round. A naive "what n would
have passed" search returns unstable answers. The stable statements are the two
in the table above: the LB at the achieved n, and the n required for a *tied*
treatment at the observed success rate.

---

## 5. AN INSTRUMENT DEFECT THAT WOULD HAVE POISONED THE RESULT

**Found, root-caused, fixed, and quantified — and it was biased BY ARM.**

The first 8 launches produced **2 valid**. Every failure was the same:
5 `prompt:submit`, only **4** `prompt:complete` in the root session — the
pre-registered validity gate correctly rejecting them.

**Root cause:** the CLI process exits before the session writer has flushed that
turn's `prompt:complete`. `run_cell.sh` pulled the session tree immediately after
the driver returned, capturing the transcript one event short.

**The dangerous part — the lag is arm-dependent:**

```
arm A  prompt:complete present at   0 s   (no race at all)
arm B  prompt:complete present at 135 s, 300 s   (the wait was load-bearing)
```

**5 of the 6 pre-fix invalid launches were arm B.** Left unfixed, this would have
systematically discarded arm-B runs and produced a differentially-invalid sample —
a verdict computed on it would have been worthless, and nothing in the run
outputs would have shown it.

**Fix:** poll the container for the 5th `prompt:complete` (600 s cap) before
pulling. It cannot manufacture a completion — a turn that genuinely failed still
times out and still fails the gate, which is exactly what happened to the one
post-fix invalid (`turns_done=4`, a real driver-cap failure).

| | launches | valid | rate | spend |
|---|---:|---:|---:|---:|
| pre-fix | 8 | 2 | 0.250 | $47.26 |
| **post-fix** | **88** | **87** | **0.9886** | $605.45 |
| **total** | **96** | **89** | **0.9271** | **$652.71** |

Cost of the defect: **7 invalid launches, $48.90.** This is the third time this
program has found that a low "validity rate" was substantially an *instrument*
problem (cf. `webu`/`i0cm`, historical 0.67 -> 1.000).

---

## 6. DELIVERABLES

| # | Deliverable | State |
|---|---|---|
| 1 | **n >= 73 valid runs per arm, both providers** | **NOT-POSSIBLE (cap)** — see below |
| 2 | Analysis plan committed BEFORE run 1, SHA quoted | **DONE** — `68b3b68` |
| 3 | Frozen rule applied verbatim; LB + delegation ratio per arm per provider; verdict with the deciding number | **DONE** — NO-SHIP, `opus` ratio **0.4737** |
| 4 | Fan-out width per delegation as a measured secondary | **DONE** — §2, never gating |
| 5 | `anchors` cannot see the treatment; foundation-root container required | **DONE** — §7 |
| 6 | Note (do not fix) the deleted `delegation-instructions.md` | **DONE** — §7 |
| 7 | If SHIP, mark #369 ready | **N/A** — NO-SHIP. Nothing was marked ready; nothing shipped from this lane. |

### Deliverable 1 — NOT-POSSIBLE, with what WAS executed first

**Executed: 96 launches, 89 valid runs (validity 0.9271), 103 valid runs in the
primary analysis including the prior stratum, 445 graded S3 turns, $652.71
measured spend, 30.8 run-hours across 4 DTUs.** n reached **51 per arm (A) and 52
per arm (B)** of the 73 registered.

The arithmetic, priced BEFORE the bulk spend from `8rugb`'s own 14 launches on
this same harness ($4.1783 `opus` / $5.9582 `terra`):

```
  73 x $4.1783  +  73 x $5.9582  =  $739.97  <=  $880    -> CLOSED, 15.9% slack
```

It then failed for two measured reasons, both reported rather than absorbed:

1. **The observed price ran 34% above `8rugb`'s.** Measured here over 89 valid
   runs: `opus` **$6.5840**, `terra` **$6.9804**, blended **$6.7822** vs the
   $5.0680 the plan was priced at. At the true price, 146 launches costs
   **$990.20** — over the authority on its own.
2. **$48.90 was spent on 7 invalid launches** before the flush defect was found.

**Stopped at $652.71 of $880. Residue $227.29.** The smallest purchase that could
advance the deliverable is one balanced pair: `opus` **$13.17**, `terra`
**$13.96**. The residue *could* buy ~33 more pairs — so it is spendable, and this
lane chose not to spend it. That choice is recorded in **`STOP-DECISION.md`**,
committed **`b144705`**, and was fixed *before* the runs it stops, on the ground
in §4: going from n=51 to n=68 (the most $880 funds) moves condition 1's LB from
about -13 pp to -12 pp against a -5 pp floor. **It buys nothing for the gate, and
the goal says spend nothing you cannot use.** Condition 2, which is decidable at
any n and is what actually returns the verdict, was already decisive.

**The authority that would close the stated deliverable is not $880 + a little.
It is ~$8,885** (n=655/arm at the measured success rate), or **~$5,154** if one
accepts `8rugb`'s more favourable 0.857. **This is a defect in the target n, not
in the funding** — and it was knowable from `8rugb`'s own 6/7, before this item
was written.

---

## 7. VERIFICATIONS PERFORMED (each against a value already known)

**Arms are real and different** — read out of the running containers, not assumed:

| | arm A `a0decc6` | arm B `3d676d6` |
|---|---|---|
| bundle cache | `amplifier-foundation-c909465861f9d6ce` | `amplifier-foundation-351cc6fad2a647a8` |
| `context/agents/` | `delegation-instructions.md` **17,497 B** | `delegation-core.md` **1,967 B** + `delegation-depth.md` 13,378 B |
| root `session:config` | 0 mentions of `delegation-depth` | **2** mentions of `delegation-depth` |

`delegation-core.md` at 1,967 B = **492 tokens** at len//4, matching the item's
claimed 487 within rounding.

**`anchors` really is blind to this treatment.** `bundles/anchors/bundle.md`
mounts `tool-delegate` directly (line 53) and contains **zero** references to
`behaviors/agents.yaml`, `delegation-instructions.md`, `delegation-core.md`, or
`delegation-depth.md`. The treatment lives entirely in
`behaviors/agents.yaml`'s `context.include`. **Satisfied by running a
foundation-ROOT container** — `bundle.active: foundation`, `app: []` — whose
`bundle.md` line 27 includes `foundation:behaviors/agents`. The `session:config`
row above is the proof it landed.

**`mikb`'s DTU trap is ABSENT**, checked the way `webu` checked it: each arm is
pinned by `bundle.added.foundation` at provision time and no in-container
`amplifier update` path is exercised. The two distinct cache hashes above are the
positive evidence — a split state would have shown one cache serving both arms.

**Instruments validated before use, against published values.** `analyze_njpd.py`
replays `8rugb`'s 14 runs to its exact published figures (6/7 vs 6/7, diff 0.0 pp,
LB **-38.84** vs published -38.8, `opus` 0.667, `terra` 1.1875, NO-SHIP).
`fanout.py` replays `8rugb`'s own captures to `A-anth-01 [2]` / `B-anth-01 [1]` /
`A-oai-01 [1,7,3]`, reproducing its qualitative finding before this lane's first
run.

**NOTED, NOT FIXED (as instructed):** the branch **deletes**
`context/agents/delegation-instructions.md`. Any external bundle `@`-mentioning
that path breaks. Confirmed absent from every arm-B container. Out of scope.

---

## 8. DEVIATIONS, DECLARED

**D-1 — arm A is the merge-base `a0decc6`, not `main` @ `ed64999`.** Declared in
`PREREGISTRATION.md` §1 before any run. `a0decc6..main` contains two merged PRs
the branch does not (`#368`, which rewrote foundation's ROOT system instruction,
and `#371`), so `ed64999` vs `3d676d6` would measure *the split plus the reversal
of both*. The clean alternative — rebase #369 onto main — needs a ref on the
foundation remote, i.e. a foundation commit, which the goal forbids. **The
deviation is forced, not chosen.** Consequence: the verdict is about the split as
a delta from its own merge-base; it does not certify `main + #369`.

**D-2 — the stopping n.** `PREREGISTRATION.md` §7 said the lane would stop at
"the largest balanced n the cap did fund". It stopped at n>=50/arm instead, for
the reason in §4, declared in `STOP-DECISION.md` (`b144705`) before the runs it
stops. **Nothing about the rule, the operationalisation, the pooled/per-provider
choice, the validity gate, or the tie-breaks changed** — only how much of an
unreachable target to keep paying for.

**D-3 — the flush wait** (§5) is a change to the *capture* step, not to the
pre-registered validity gate, which is unchanged and still requires 5
`prompt:complete`.

---

## 9. SPEND LEDGER

| | |
|---|---:|
| Authority | **$880.00** |
| Measured spend (96 launches, this lane) | **$652.71** |
| — of which 7 invalid launches | $48.90 |
| — of which 89 valid runs | $603.81 |
| **Residue** | **$227.29** |
| Smallest useful purchase (one balanced pair) | `opus` $13.17 / `terra` $13.96 |
| Observed $/launch | `opus` **$6.5840**, `terra` **$6.9804**, blended **$6.7822** |
| Priced at (from `8rugb`, before the bulk spend) | blended $5.0680 -> **actual ran 34% high** |
| Infrastructure | 4 DTUs, registered + claimed at creation, **all 4 verified destroyed** |

No API or DTU spend occurred outside this ledger. Wall clock: 8h 53m
(04:41Z–13:35Z), 30.8 run-hours across 4 DTUs, mean 1,248 s per run.

---

## 10. WHAT REMAINS OPEN

1. **PR #369 is NOT ready and was not marked ready.** The split is quality-positive
   and cost-negative on both providers, and its only measured harm is the
   Anthropic fan-out collapse in §2. **The obvious next treatment is a variant
   that keeps the 487-token core but restores whatever cue produced the paired
   parallel spawn on Anthropic** — that would be evaluated against the same frozen
   rule, and this lane's 103 runs are its control.
2. **The frozen rule's condition 1 cannot be satisfied by this scenario at any
   affordable n** (§4). Before another lane is funded to "buy the n", the rule
   needs either a scenario with a higher success ceiling or a floor calibrated to
   the achievable interval. **Funding another n-purchase against S3 at -5 pp would
   repeat this lane's cap failure at 6-11x the price.**
3. **Condition 2 has no n problem and decided this cleanly.** If the program wants
   a fast delegation-regression gate, condition 2 alone is already decisive at
   n~26/provider/arm for about $350.
