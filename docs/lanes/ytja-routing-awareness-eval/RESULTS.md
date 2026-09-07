# ytja — routing-awareness results

runs executed **480** · valid **480** · validity **1.000**
· measured spend **$130.6017**

## G-INSTRUMENT

- `events.jsonl tool:post` vs `transcript.jsonl role:"tool"` disagree on **0 / 480** valid runs.
- runs with a thinking-text mention of a reach tool but **zero executed** reach: **0**. Those are exactly the runs a thinking-text grader would have scored as reaches. None are counted here.

## Per-prompt cells (pass / n) — the aggregate never replaces these

| prompt | kind | opus stock | opus lean | opus Fisher p | terra stock | terra lean | terra Fisher p |
|---|---|---|---|---|---|---|---|
| H1 | hidden | 0/8 | 0/8 | UNEVAL | 1/8 | 2/8 | 0.9000 |
| H2 | hidden | 0/8 | 0/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| H3 | hidden | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| H4 | hidden | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| H5 | hidden | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| H6 | hidden | 0/8 | 0/8 | UNEVAL | 0/8 | 0/8 | UNEVAL |
| H7 | hidden | 0/8 | 0/8 | UNEVAL | 0/8 | 0/8 | UNEVAL |
| H8 | hidden | 0/8 | 0/8 | UNEVAL | 1/8 | 0/8 | 0.5000 |
| H9 | hidden | 0/8 | 0/8 | UNEVAL | 0/8 | 0/8 | UNEVAL |
| H10 | hidden | 0/8 | 0/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| C1 | control | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| C2 | control | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| C3 | control | 8/8 | 8/8 | UNEVAL | 7/8 | 7/8 | 0.7667 |
| C4 | control | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |
| C5 | control | 8/8 | 8/8 | UNEVAL | 8/8 | 8/8 | UNEVAL |

`UNEVAL` = degenerate cell (both arms identical at a boundary, or an empty arm). `otr`'s pre-registered gate came back UNEVALUABLE on counts `[0,0,1,0,0]`; reporting a verdict the data cannot support is the error, not the UNEVALUABLE.

Holm–Bonferroni across evaluable hidden cells: `H1|terra` 1.0000, `H8|terra` 1.0000

## Aggregate reach rates — PER-PROVIDER IS DECISIVE, pooled is transparency only

| scope | measure | stock | lean | diff (lean−stock) | 95% Newcombe CI | width |
|---|---|---:|---:|---:|---|---:|
| opus | hidden-reach | 24/80 = 0.300 | 24/80 = 0.300 | +0.00 pp | [-13.99, +13.99] pp | 27.99 pp |
| opus | control-pass (no over-reach) | 40/40 = 1.000 | 40/40 = 1.000 | +0.00 pp | [-8.76, +8.76] pp | 17.52 pp |
| terra | hidden-reach | 42/80 = 0.525 | 42/80 = 0.525 | +0.00 pp | [-15.12, +15.12] pp | 30.24 pp |
| terra | control-pass (no over-reach) | 39/40 = 0.975 | 39/40 = 0.975 | +0.00 pp | [-10.58, +10.58] pp | 21.17 pp |
| POOLED (not decisive) | hidden-reach | 66/160 = 0.412 | 66/160 = 0.412 | +0.00 pp | [-10.67, +10.67] pp | 21.34 pp |
| POOLED (not decisive) | control-pass (no over-reach) | 79/80 = 0.988 | 79/80 = 0.988 | +0.00 pp | [-5.59, +5.59] pp | 11.18 pp |

## The item's PRIMARY rule — applied, and reported with its power verdict

> Stage 1 is CLEAR if hidden-reach ≥ stock − 5 pp AND over-reach ≤ stock + 5 pp (both on the LB).

- **opus hidden-reach** LB = **-13.99 pp** vs bar −5.00 pp → does not meet. But the BEST ATTAINABLE LB at n=80 is **-4.58 pp** — so the clause is satisfiable here.
- **opus over-reach** UB = **+8.76 pp** vs bar +5.00 pp → does not meet. Best attainable UB at n=40 is **+8.76 pp** — **cannot be met at this n by any data**.
- **terra hidden-reach** LB = **-15.12 pp** vs bar −5.00 pp → does not meet. But the BEST ATTAINABLE LB at n=80 is **-4.58 pp** — so the clause is satisfiable here.
- **terra over-reach** UB = **+10.58 pp** vs bar +5.00 pp → does not meet. Best attainable UB at n=40 is **+8.76 pp** — **cannot be met at this n by any data**.

**VERDICT ON THE PRIMARY RULE: NOT-POSSIBLE (cap-bound).** It needs 73 observations per arm per provider on each clause — 620 launches, $1,197.29 at the item's reference prices, against a $200 authority. Reporting a CLEAR from these interval widths would be the exact error S2a, `1ru` and `8rugb` were each caught making.

## The lane's SECONDARY rule — what the authority actually bought

**No hidden prompt regressed** at one-sided Fisher p < 0.05 on either provider.

**No control showed increased over-reach** at p < 0.05 on either provider.

## What the model reached FOR — the pass/fail metric hides this

First EXECUTED tool of the run, all 15 prompts, n=120 per arm per provider:

**terra**

| first tool | stock | lean | Fisher p (2-sided) |
|---|---:|---:|---:|
| `delegate` | 31 | 28 | 0.76449 |
| `glob` | 5 | 4 | 1.00000 |
| `load_skill` | 14 | 16 | 0.84558 |
| `mode` | 0 | 6 | 0.02931 |
| `read_file` | 39 | 36 | 0.78073 |
| `recipes` | 0 | 7 | 0.01428 |
| `todo` | 31 | 23 | 0.27917 |

**opus**

| first tool | stock | lean | Fisher p (2-sided) |
|---|---:|---:|---:|
| `bash` | 39 | 34 | 0.57480 |
| `delegate` | 16 | 16 | 1.00000 |
| `glob` | 17 | 21 | 0.59623 |
| `load_skill` | 8 | 8 | 1.00000 |
| `read_file` | 40 | 40 | 1.00000 |
| `todo` | 0 | 1 | 1.00000 |

### The discovery-tool shift — the real behavioural effect of the lean head

| provider | tool | stock | lean | Fisher p |
|---|---|---:|---:|---:|
| terra | `mode` anywhere in run | 0/120 | 21/120 | 0.000000 |
| terra | `recipes` anywhere in run | 0/120 | 21/120 | 0.000000 |
| opus | `mode` anywhere in run | 0/120 | 0/120 | 1.000000 |
| opus | `recipes` anywhere in run | 0/120 | 0/120 | 1.000000 |

First CAPABILITY REACH on terra, pooled over the five prompts where stock's first reach was `per-repo-conventions` (n=40 per arm):

| first reach | stock | lean | Fisher p |
|---|---:|---:|---:|
| `load_skill:per-repo-conventions` | 33/40 | 15/40 | 0.000077 |
| `mode:list` | 0/40 | 18/40 | 0.000001 |
| `load_skill:<list>` | 0/40 | 3/40 | 0.240506 |

### Failure-mode split on hidden prompts — no reach at all vs reached the wrong thing

| provider | arm | any capability reach | `delegate` used | `load_skill` used |
|---|---|---:|---:|---:|
| opus | stock | 24/80 | 16 | 8 |
| opus | lean | 26/80 | 16 | 10 |
| terra | stock | 80/80 | 62 | 49 |
| terra | lean | 80/80 | 56 | 50 |

### Cost and wall by arm — paired by prompt, 20,000-sample bootstrap

| provider | stock $/run | lean $/run | delta | 95% CI on the paired mean delta | verdict |
|---|---:|---:|---:|---|---|
| terra | $0.1688 | $0.1737 | +2.9% | [-0.0092, +0.0192] USD | **NOT significant** (CI spans 0) |
| opus | $0.3494 | $0.3965 | +13.5% | [-0.0166, +0.1304] USD | **NOT significant** (CI spans 0) |

- terra wall: stock 41.2s -> lean 44.2s (+7.2%)
- opus wall: stock 56.8s -> lean 68.7s (+20.9%)


---

## MECHANISM — located in the text, not inferred

The discovery-tool shift is explained by one line of `bundles/anchors/context/system.md`.

**stock** (`ed64999d`):

```
- Skills, modes, and recipes are available. Use `load_skill(list=true)`,
  `mode(operation="list")`, or `recipes(operation="list")` to discover them.
```

**lean** (`7771ad22`):

```
- Discover skills, modes, recipes via `load_skill(list=true)`,
  `mode(operation="list")`, `recipes(operation="list")`.
```

Every fact survives: all three tools named, all three operations named, `list` in each. A
fidelity check passes. What changed is the **mood** — a *declarative statement of availability*
became an *imperative instruction*. gpt-5.6-terra obeyed it: `mode` and `recipes` went from
**0/120 to 21/120 runs each** (p < 1e-6), and `mode:list` displaced
`load_skill:per-repo-conventions` as the first capability reach on five prompts
(**0/40 → 18/40**, p = 1e-6). claude-opus-5 did not move at all (0/120 → 0/120).

**This is the exact class of failure the item was filed to catch, arriving with the opposite
sign.** The item's worry was *"a description can keep every fact and stop triggering."* What was
measured is a description that kept every fact and **started triggering something else**.
Fidelity checking cannot see either one.

---

## WHAT THE PRIMARY RULE WOULD ACTUALLY HAVE COST — repriced at the OBSERVED reach rates

The pre-registration priced the rule under its **best case** (perfect agreement at a reach rate of
1.0): 73 obs/arm/provider. That was optimistic, and the measurement says by how much. Interval
width is widest near p = 0.5, and the observed rates are **opus 0.300** and **terra 0.525**.

| clause | observed rate | obs/arm/provider needed for the bar |
|---|---:|---:|
| hidden-reach ≥ −5 pp (opus) | 0.300 | **650** |
| hidden-reach ≥ −5 pp (terra) | 0.525 | **770** |
| over-reach ≤ +5 pp | 0.0125 | **100** |

| variant | launches | cost at THIS lane's observed prices |
|---|---:|---:|
| 2 arms × 2 providers (per-provider, decisive) | **3,240** | **$1,022.22** |
| 3 arms × 2 providers | 4,860 | $1,533.33 |
| *(the best-case 73-obs version, for reference)* | 584 | $134.39 |

**$1,022.22 against a $200 authority is 5.1× short** — and the best-case figure the
pre-registration quoted ($1,197.29 at the item's reference prices) turns out to have been the
*right order of magnitude for the wrong reason*: this lane's launches are 3–5× cheaper than the
reference, but the rule needs ~9× more of them than the best case implied. The two errors nearly
cancel. **Anyone re-funding this must price the rule at the observed reach rate, not at 1.0.**

---

## ARM 3 (stage-1) — not run, priced here

At run time **`mse0` and `6f80` have no branch at all**, and `kp79`/`kv98` are a different
workstream in bundle repos outside this container's mount set. Nothing was substituted.

**Price of the arm-3 re-run at this lane's own observed prices:** 15 prompts × n=8 × 2 providers
= **120 launches = $65.30** for the third arm alone, or **$195.90 (360 launches)** to re-run all
three arms together, which is what a clean 3-arm comparison requires (the existing arm-1/arm-2
captures are usable as-is only if the container, CLI SHA and prompt set are held byte-identical).

---

## SPEND

| item | launches | cost |
|---|---:|---:|
| discarded pilot (amendment A1) | 4 | $0.10 |
| price probe (folded into rep 1) | — | — |
| graded sweep, 15 prompts × n=8 × 2 arms × 2 providers | **480** | **$130.6017** |
| **total** | **484** | **$130.70** |

Validity **480/480 = 1.000**. Authority $200; **residue $69.30**. The smallest purchase that would
advance the remaining deliverable is the arm-3 re-run at **$65.30** — which the residue *would*
cover for the third arm alone, but **not** the $195.90 three-arm re-run a clean comparison needs,
and arm 3 has no code to point at in any case. Mean cost per launch **$0.2721**.
