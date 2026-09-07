# `skw3b` — RUN LOG

Appended **as each purchase is decided**, never batched at the end. Authority **$930.00**.

Stopping rule (`PREREGISTRATION.md` §6):
`cumulative_spend + (block_size × worst_observed_single_run_cost) ≤ $930.00`,
`worst_observed_single_run_cost` revised **upward only**, seeded at **$4.63**.

---

## Purchase decisions — arithmetic recorded BEFORE each purchase

| # | when | purchase | cumulative before | arithmetic | decision |
|---|---|---|---:|---|---|
| 0 | pre-spend | `PREREGISTRATION.md` (`741a71b`) | $0.00 | reads committed JSON only | **committed at $0.00 spent** |
| 1 | before P1 | **P1 price/validity smoke** — 1 stock + 1 V1 end-to-end `opus-5`/S7-17, sequential, DTU `val-g7h3-a` | $0.00 | the opus-5/S7 per-run price has **never been observed** (`skw3` §6.2); everything in §4 is priced off it. Seed worst-case $4.63/run x 2 = **$9.26 est.**, tripwire **$30.00**. `0.00 + 30.00 = 30.00 <= 930.00` | **LAUNCH** |

---

## Spend ledger — running

| # | item | $ |
|---|---|---:|
| 1 | **P1a — VOIDED by a harness defect, cost real and kept**: 1 stock `opus-5`/S7-17 run, `VOID-noconfig-stock-r01` | **3.8500** |
| | **cumulative** | **3.8500** |

---

## Purchase 1 outcome — the run was bought, and it bought a defect instead of a datum

`VOID-noconfig-stock-r01`: **$3.85**, wall **615.3 s**, recall **100/100**,
`context:compaction` **0** against the required ≥5 → **INVALID**.

**Diagnosed to root cause for $0**, and it is not the treatment and not this cell:

```
scripted_driver.py  configure: (empty)          <- vs vbs/3d2: "PRIMARY_OK ... | MAXTOK_OK max_tokens=90000 budget_cap=inserted"
configure_cell.py   exit 5, stderr "FAIL: 'max_tokens:' line not found in context config"
find_bundle_md()    hardcodes  <foundation>/bundles/anchors-amp-dev/bundle.md
that file today     1,528 bytes, pure `includes:` -- NO context block, NO max_tokens line
the line now lives  <foundation>/bundles/anchors/bundle.md:33  ->  max_tokens: 300000
```

So the S7/S5 compaction-forcing knob is **dead against today's
`amplifier-foundation@main`**: compaction fires at the inherited 300,000
instead of the configured 90,000, no boundary is ever crossed, and the run is
scored INVALID *after* it has been paid for in full.

**It reproduces for terra in the same container** (`FAIL` identical), so this is
**not** Anthropic-specific and **not** this lane's new cell — it is every S7/S5
run launched today.

**The failure is loud in `configure_cell.py` and silent in `scripted_driver.py`**:
`dexec_out()` returns only `stdout`, drops `stderr`, and the driver never checks
the exit code. That is what turns a 1-line config break into a full-price
invalid run.

Fix emitted as `skw3b-configure-cell-anchors-fallback.diff` (content-selected
fallback to `bundles/anchors/bundle.md`). **The shared `_harness/` file was NOT
edited** (GOAL.md 0rg hazard). This lane runs its own patched copy and passes
`--skip-configure`, and `run_arm.sh` now **refuses to launch** unless the
configure step really printed `MAXTOK_OK max_tokens=90000`.

Verified on `val-g7h3-b` before any relaunch:
`PRIMARY_OK id=opus model=claude-opus-5 effort=medium priority=0 | MAXTOK_OK max_tokens=90000 budget_cap=inserted cs=...`
— byte-shape identical to the `configure:` line in every published `vbs`/`3d2` run log.

| # | when | purchase | cumulative before | arithmetic | decision |
|---|---|---|---:|---|---|
| 2 | before P1b | **P1b relaunch** of the price/validity smoke with the configure fix, 1 stock then 1 V1 | $3.85 | the $3.85 bought a defect, not a price. Same tripwire: `3.85 + 2 x 6.50 = 16.85 <= 930.00` | **LAUNCH** |

| 3 | 09:40Z, **before any analysis of any delta** | **EXTENSION decided in advance**: if the pre-registered 24-block sequence completes and the budget gate still passes, append **8 more ABBA blocks (b27-b34, `v s s v v s s v`)**. Decided on **clock and budget alone**, exactly as `PREREGISTRATION.md` §6 requires — no interim analysis of the primary endpoint was run, and none will be until the sequence stops. | ~$180 | 8 blocks x 3 launches x $6.72 worst = $161.28; $180 + $161 = $341 <= $930 | **QUEUE** |

---

## STOP DECISION — recorded here, not in the write-up

**SEQUENCE COMPLETE at 14:28:37Z. 98 launches, $428.10 of $930.00. Residue $501.90,
spendable and deliberately unspent.**

Spending stopped because **no remaining purchase changes a verdict**:

* all three pre-registered estimators already **exclude zero** and agree in sign and
  magnitude (−13.57% / −16.42% / −14.44%); more `n` on this cell tightens a CI that has
  already fired;
* ±5% on this cell needs `2 × 55.6 / 0.194 = 574 launches × $4.33` = **$2,484**;
* terra/S7 needs `n=103.4/arm → 236 launches × $3.217` = **$760**;
* the stated four-cell deliverable needs **$5,794–$9,596**.

**The smallest purchase that would advance an open deliverable is $760. $501.90 does not
buy it.** This is NOT `1ru`'s unspendable-residue situation and must not be read as one —
the residue is spendable; there is simply nothing worth buying with it.

## Full spend ledger

| # | item | $ |
|---|---|---:|
| 1 | `VOID-noconfig-stock-r01` (bought the harness defect, not a datum) | 3.8500 |
| 2 | P1b smoke: 1 stock $6.72 + 1 V1 $4.03 | 10.7500 |
| 3 | ABBA blocks b03–b34, 96 launches | 413.5000 |
| | **cumulative** | **428.1000** |
