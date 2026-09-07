# PRE-REGISTERED ANALYSIS PLAN — `model_performance-njpd`

**Decisive evaluation of foundation PR #369 (delegation-context split) at the n
at which `8rugb`'s own frozen rule is arithmetically satisfiable.**

Written and committed **BEFORE the first run of this lane**. Nothing below may be
changed after a number exists. The commit SHA of this file is quoted in
`DONE-NOTE.md` and is the object the verdict is accountable to.

---

## 0. THE RULE — FROZEN, QUOTED, NOT RE-DERIVED

> **SHIP iff success LB >= -5 pp AND delegation count within +/-30% of main.**

This lane does not loosen it, tighten it, or re-derive it. It buys the sample
size at which it can return an answer, and applies it verbatim.

**Why this lane exists.** `8rugb` returned NO-SHIP at 14 launches / 14 valid /
$69.18, and flagged that condition 1 failed on **interval width, not on a
measured regression**: pooled success **6/7 vs 6/7, diff 0.0 pp, LB −38.8 pp**.
Because `best-case LB = −(1 − wilson_lower(n, n))`, the best attainable LB is
**−56 pp at n=3** and **−5.00 pp at n=73**. At its own n, condition 1 could not
be satisfied by any possible data. That is a power defect, not a finding.

---

## 1. ARMS — AND A DECLARED DEVIATION FROM THE GOAL TEXT

| Arm | Ref | SHA |
|---|---|---|
| **A** (control, "main") | `amplifier-foundation` merge-base of the PR branch | `a0decc61f41ed78a92db6d5b70a71e15722a5624` |
| **B** (treatment) | `lane/8rug-foundation-root-hygiene-b` (PR #369) | `3d676d68d0e45620330c24ae0142de86efa39234` |

Pinned in the DTU by **source override only** (`bundle.added.foundation`). **No
foundation commits are produced by this lane.**

### DEVIATION D-1 — arm A is the merge-base `a0decc6`, not `main` @ `ed64999`

The goal names arm A as "foundation main (>= `ed64999`)". **That contrast is
confounded and this lane does not run it.** Evidence, from
`git diff --stat main 3d676d6`:

```
a0decc6..main contains TWO merged PRs the B branch does not:
  aac89ea  #368  foundation's ROOT body was documentation prose sent as system instruction
  ed64999  #371  the context-token estimator understated by 6.28x
```

Comparing `ed64999` against `3d676d6` therefore measures **the delegation split
PLUS the reversal of #368 and #371** — and #368 is itself a change to the root
system instruction, i.e. exactly the class of change that moves delegation
behaviour. The diff shows those reversals plainly: `main -> 3d676d6` *deletes*
`tests/test_context_include_estimator.py` (271 lines) and
`tests/test_tool_skills_double_mount.py` (175 lines).

The unconfounded contrast for "what does the split do" is **merge-base vs
branch**, which is what `8rugb` ran and what this lane runs.

*The clean alternative — rebase #369 onto `ed64999` and compare `main` vs
`main+split` — requires a ref that exists on the foundation remote, and creating
one is a foundation commit from this lane, which the goal forbids. The deviation
is therefore forced, not chosen.*

**Consequence, stated up front:** the verdict is about the split **as a delta
from its own merge-base**. It does not certify that `main + #369` behaves
identically, because `main` has moved by two PRs since the branch was cut.

---

## 2. WHAT COUNTS AS A RUN

One **launch** = one invocation of `run_cell.sh <dtu> <arm> <provider> <model>
<effort> <runid>` — an S3 scenario run: workspace reset, harness + scenario
pushed, cell configured, reference seeded, the 5-turn scripted driver executed,
graded in-container by `s3/grader.py`, sessions pulled, measured by
`probes/dw_measure.py`.

A launch becomes a **valid run** iff `summarize_run.py` records `valid: true`.
That gate is `8rugb`'s, reused byte-identically, and is composed **only of
mechanical execution facts — never of the score**:

1. `driver_record.json` exists (the turn loop returned);
2. `turns_done == 5`;
3. no turn recorded `marker == "TIMEOUT"`;
4. session continuity: every session id the CLI actually printed is the same id;
5. the root session file carries exactly **5** `prompt:complete` events;
6. a gradeable `scorecard.json` with a `total`;
7. a measurable session tree (`tree_sessions >= 1`).

**A run is never invalidated after its score is seen.** Validity is computed by
`summarize_run.py` from fields 1–7 above; the score is read from the same file
but is not an input to validity.

---

## 3. HOW INVALID RUNS ARE HANDLED AND REPLACED

- An invalid launch is **replaced 1-for-1** by a new launch in the **same cell**
  (same arm, same provider), appended to that cell's queue.
- Every launch — valid or not — is **counted in spend** and appears in the run
  table with its `invalid_reasons`. Invalid launches are never deleted, hidden,
  or excluded from the cost accounting.
- Replacement stops when either the cell's target is met, or the stopping rule
  in §7 fires.
- **Achieved validity is itself a reported finding**, not a nuisance parameter.

---

## 4. THE DECISIVE CHOICE: POOLED vs PER-PROVIDER

**This is the choice the goal requires be made before the numbers exist, because
it decides the verdict.** `8rugb`'s two providers moved in opposite directions
(anthropic ratio **0.667**, openai **1.188**). It is fixed here as follows.

### Condition 1 — success LB >= −5 pp: **POOLED across providers.**

Forced by arithmetic, not preference. The item's own power calc (n=73 -> LB
−5.00 pp) is a pooled calculation. At a balanced provider split, n=73/arm gives
n≈36/provider/arm, and the best attainable LB at n=36 is
`−(1 − wilson_lower(36,36)) = −9.64 pp` — **worse than −5 pp for any possible
data.** A per-provider condition 1 would reproduce exactly the unsatisfiability
defect this lane exists to remove.

Per-provider success LB **is still reported** (the goal requires it) and is
explicitly **non-gating and non-decidable at its own n** — labelled as such in
every table.

### Condition 2 — delegation within +/-30% of main: **PER-PROVIDER. Both must pass.**

Three reasons, all stated before any number of this lane exists:

1. **The program's hard constraint.** `00-what-we-know.md` §1: *"Anthropic is the
   daily driver and must not regress ... Any treatment that helps OpenAI and
   costs Anthropic ... is not shippable."* Pooling lets an OpenAI gain mask an
   Anthropic regression — the precise failure mode that constraint exists to
   prevent.
2. **Pooling these two counts is incoherent.** Anthropic delegates ~1–2 per run;
   terra delegates ~9–17. A pooled mean is dominated by terra and is not a
   meaningful "delegation count" for either.
3. **Continuity.** `8rugb`'s `analyze.py` already operationalised condition 2
   per-provider; changing it now would be a post-hoc move.

**Full disclosure of the consequence.** This choice is the *conservative* one:
on `8rugb`'s published numbers, pooled would have PASSED condition 2
(mean_A 5.429, mean_B 6.000, ratio **1.105**, inside the band) while
per-provider FAILS on anthropic (**0.667**). The choice is being made with that
direction already known — it is published in the item text and cannot be
un-known — so the reasoning above, not the outcome, is the justification, and
**both** the per-provider and the pooled condition-2 result are reported so any
reader can see exactly what the choice bought.

### Operationalisation (unchanged from `8rugb`)

| Term | Definition |
|---|---|
| success | the S3 grader's own `pass` field |
| success LB | Newcombe/Wilson lower bound on `p(B) − p(A)`, in pp, Z = 1.959963985 |
| delegation count | `dw_measure.root_delegate_calls` = `delegate:agent_spawned` events in the **root** session |
| +/-30% | `mean(B)/mean(A)` in the **inclusive** interval `[0.70, 1.30]` |
| UNEVALUABLE | arm-A delegation median 0, **or** fewer than 2 valid arm-A runs at that provider record >=1 delegation |

---

## 5. HOW TIES BREAK

1. **Condition 1 at exactly −5.00 pp PASSES.** The rule says `>= -5`.
2. **Condition 2 at exactly 0.700 or exactly 1.300 PASSES.** The band is
   inclusive (`0.70 <= ratio <= 1.30`).
3. Rounding is for **display only**. Both conditions are evaluated on the
   unrounded float; a value that displays as `-5.0` but is `-5.04` FAILS.
4. **SHIP requires every gating condition true**: pooled condition 1, **and**
   condition 2 at **both** providers. Any one false => **NO-SHIP**.
5. If any provider is UNEVALUABLE, the verdict is **UNEVALUABLE**, not NO-SHIP.
6. A verdict is reported once. No re-decision without a number changing.

---

## 6. SAMPLE, ALLOCATION, AND THE PRIOR STRATUM

- **Target: n >= 73 valid runs per arm (146 pooled).**
- **Allocation: balanced 50/50 between providers within each arm** (~36–37 per
  provider per arm). Cells are filled round-robin so that an early stop leaves
  the arms and providers as close to balanced as the achieved n allows.
- **Cells:** anthropic root = `opus` / `claude-opus-5` / `xhigh`;
  openai root = `terra` / `gpt-5.6-terra` / `high`. As originally registered.

### The `8rugb` prior stratum — INCLUDED, and reported both ways

`8rugb`'s **14 valid runs** were produced by the **same harness, same scenario,
same driver, same grader, same two SHAs, same provider cells, same day**. They
are **included in the primary analysis** as a pre-registered prior stratum
(7 valid per arm), and the analysis **also reports this-lane-only** so the
pooling is fully reversible by any reader. Declared now, before this lane's
first run.

---

## 7. STOPPING RULE, AND THE SPEND ARITHMETIC

**Spend authority: $880.**

**Observed per-launch price** — from `8rugb`, the same harness on the same
scenario at the same two SHAs, 14 launches, **14 valid (validity 1.000)**,
`measured_spend_usd` **$69.1752**:

| Provider | Launches | Spend | **$/launch** |
|---|---:|---:|---:|
| anthropic (`opus`) | 8 | $33.4263 | **$4.1783** |
| openai (`terra`) | 6 | $35.7489 | **$5.9582** |
| **blended (8:6 mix)** | **14** | **$69.1752** | **$4.9411** |

> The goal's "measured references terra **$0.9386** / anthropic **$2.9236** per
> launch" are `webu`'s, from a **different and cheaper scenario**. On *this*
> scenario terra is the *more* expensive provider, because it delegates 9–17
> times per run and the sub-work routes to `sol`. Using webu's figures here would
> under-price the design by ~2.4x. The `8rugb` figures above are the ones quoted
> for **this** run count and **this** scenario, as the goal's authoring rule
> requires.

**Arithmetic for the stated deliverable** (146 launches, balanced 73/73 provider
split, at observed validity):

```
  73 anthropic x $4.1783  =  $305.02
+ 73 terra     x $5.9582  =  $434.95
                            ---------
  146 launches            =  $739.97   / validity 1.000  =  $739.97
```

**$739.97 <= $880 — the arithmetic CLOSES**, with **$140.03 (15.9%) of slack.**
Net of the 14 prior-stratum runs already bought by `8rugb`, this lane's own
purchase is **132 launches ≈ $669**.

**Break-even validity: `$739.97 / $880 = 0.841`.** If achieved validity falls
below **84.1%**, the design does not complete at this cap; that is recorded as
NOT-POSSIBLE with the arithmetic (OUTCOME branch B), never absorbed by
overspending and never by silently shrinking n.

**Stopping rule (fires on whichever comes first):**

1. **73 valid runs in each arm** — target met, stop.
2. **Remaining budget < the smallest useful purchase.** The smallest indivisible
   purchase that advances the deliverable is **one launch pair (one arm-A + one
   arm-B launch in the same provider cell)**: anthropic **$8.36**, terra
   **$11.92**. When the residue cannot buy the cheaper of those, it is
   **unspendable**, not "remaining budget". The residue and the purchase it could
   not buy are both stated.
3. **Projected completion exceeds $880.** Spend is reconciled after every batch;
   if `spent + (runs_remaining x observed $/launch)` exceeds $880, the lane stops
   at the largest balanced n the cap did fund and records NOT-POSSIBLE with the
   arithmetic and the n achieved.

**In every stop except (1), the outcome is still RESOLVED (branch B), with the
reason leading with what was executed.**

---

## 8. SECONDARY, MEASURED AND NEVER GATING: FAN-OUT WIDTH

`8rugb`'s real finding is that the split does **not** suppress delegation and does
**not** cause over-delegation — both arms delegated on 13 of 14 runs, same turn,
same agent — but that it **narrows fan-out width**. `root_delegate_calls` is a
flat count and cannot see that. `fanout.py` groups the same
`delegate:agent_spawned` events two mechanical ways:

- **`fanout_per_turn`** — spawns per root turn, turn boundaries taken from
  `prompt:complete` in the root session; reported for turns with >=1 spawn.
- **`fanout_burst`** — spawns clustered by a **5.0 s** inter-spawn gap; a proxy
  for "dispatched in one parallel tool-call batch", which turn-grouping cannot
  separate from two sequential delegations inside one turn.

**Instrument validated against a value already known** before this lane's first
run, by replaying `8rugb`'s own captures:

```
A-anth-01  fanout_per_turn [2]        fanout_burst [2]      <- two PARALLEL explorers
B-anth-01  fanout_per_turn [1]        fanout_burst [1]      <- one
A-oai-01   fanout_per_turn [1,7,3]    fanout_burst [1]x11   <- terra's 11 are SEQUENTIAL
```

This reproduces 8rugb's anthropic observation exactly, and adds the reason its
two providers moved in opposite directions: **anthropic's delegations are
parallel bursts, terra's are sequential.**

Reported per arm per provider: `fanout_per_turn` distribution, max, mean;
`fanout_burst` distribution, max, mean; delegating-turn count.
**It never enters the verdict.**

---

## 9. WHAT IS NOTED, NOT FIXED

- The branch **deletes `context/agents/delegation-instructions.md`**. Any external
  bundle `@`-mentioning that path breaks. **Noted; out of scope; not fixed here.**
- **`anchors` cannot see this treatment at all**: it mounts `tool-delegate`
  directly and never includes `foundation:behaviors/agents.yaml`. The standard
  eval container is therefore blind to the change. **This lane satisfies the
  requirement by running a FOUNDATION-ROOT container** — `bundle.active:
  foundation` with `app: []` in `settings.yaml` — inherited unchanged from
  `8rugb`'s profiles, which is why the treatment is visible at all.
- **`mikb`'s DTU trap** (`amplifier update` refreshes the bundle cache while
  `site-packages` stays newer, silently producing a false arm) **does not apply**:
  the arm is pinned by `bundle.added.foundation` at provision time and no
  in-container upgrade path is exercised. Checked and reported in the DONE-NOTE
  the way `webu` did.

---

## 10. DELIVERABLE ARTIFACTS

| Artifact | Path |
|---|---|
| this plan | `docs/lanes/8rugb2-delegation-split-decisive/PREREGISTRATION.md` |
| capture root | `.amplifier/evaluation/treatment-validation/20260906-njpd/` (evals repo) |
| per-run record | `runs/<runid>/summary.json`, `fanout.json` |
| aggregate + verdict | `ANALYSIS.json` |
| lane note | `docs/lanes/8rugb2-delegation-split-decisive/DONE-NOTE.md` |
