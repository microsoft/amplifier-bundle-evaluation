# `skw3b` — RUN LOG

Appended **as each purchase is decided**, never batched at the end. Authority **$930.00**.

Stopping rule (`PREREGISTRATION.md` §6):
`cumulative_spend + (block_size × worst_observed_single_run_cost) ≤ $930.00`,
`worst_observed_single_run_cost` revised **upward only**, seeded at **$4.63**.

---

## Purchase decisions — arithmetic recorded BEFORE each purchase

| # | when | purchase | cumulative before | arithmetic | decision |
|---|---|---|---:|---|---|
| 0 | pre-spend | `PREREGISTRATION.md` | $0.00 | reads committed JSON only | **committed at $0.00 spent** |

---

## Spend ledger — running

| # | item | $ |
|---|---|---:|
| | *(appended as each purchase completes)* | |
