# STOP DECISION — declared 2026-09-07T08:45Z, BEFORE the runs it stops

Recorded at **launches = 45, valid = 39, spend = $310.75, n_A = 28, n_B = 26**
(both including the 8rugb prior stratum). Fixed here before any further data
exists, so the stopping point cannot be chosen to suit a number.

## The finding that forces it

`8rugb`'s power calc — the one this item is built on — is

```
best-case LB = -(1 - wilson_lower(n, n))     ->  n=73 gives -5.00 pp
```

That is the lower bound attained **only when BOTH arms score 100%**. S3 does not
do that. Measured here, pooled over both strata:

| success rate assumed | LB at n=73/arm | n/arm actually required for LB >= -5 pp | cost at $6.89/launch |
|---|---:|---:|---:|
| **1.000** (8rugb's assumption) | **-5.00 pp** | **73** | **$1,006** |
| 0.857 (8rugb's OWN observed 6/7) | — | **380** | **$5,239** |
| **0.667** (measured here, 36/54) | **-14.95 pp** | **681** | **$9,388** |

**Condition 1 is not satisfiable at n=73 either.** The item bought "the n at which
8rugb's rule can finally decide"; 73 is not that n at any success rate this
scenario actually produces. Even the best-case n=73 now costs **$1,006** at the
observed per-launch price — already above the $880 authority before the success
rate is taken into account at all.

## What that changes

Going from n≈50/arm to n≈68/arm (the largest the cap funds) moves condition 1's
LB from roughly **-13 pp to -12 pp**. Both are hopeless against a -5 pp floor.
That spend buys **nothing for the gating condition** — and the goal is explicit:
*"spend nothing you cannot use."*

**Condition 2 (delegation within +/-30%) is decidable at any n**, and it is where
the verdict actually turns. It is the one thing further runs still buy.

## The decision

**Stop at n >= 50 valid runs per arm** (including the prior stratum) — about
25 per provider per arm, enough to place each provider's delegation ratio
confidently against the [0.70, 1.30] band, including `terra`, which is the only
cell near a boundary.

Projected: ~46 more launches, ~$317, ending near **$628** of the $880 authority.
The residue and exactly what it could not buy are reported in `DONE-NOTE.md`.

This is a **declared deviation** from PREREGISTRATION.md §7, which said the lane
would stop "at the largest balanced n the cap did fund". That clause was written
believing n=73 was both the target and reachable. It is neither. Nothing about
the frozen rule, the operationalisation, the pooled/per-provider choice, the
validity gate, or the tie-breaks changes — **only how much of an unreachable
target to keep paying for.**
