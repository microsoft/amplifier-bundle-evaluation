# DONE-NOTE — `model_performance-2gxp` · lane `webu2-tool-vanishing-probe`

**OUTCOME BRANCH A — RESOLVED.** All deliverables DONE. The cap never bound
($19.9013 of $25). No deliverable is NOT-POSSIBLE.

**Result in one line:** the pre-registered rule returns **`DON'T-BUILD STANDS`** — which this item
states is a **PASS** — and the mechanism question underneath it is answered: **the three tools vanish
because they are DEFERRED while a substitute stays visible, not because of prompt wording.**

**Read `FINDINGS.md` for every number and its rule. `PREREG.md` (`a4506d3a96b5bee27eb16576e1aa859a67c6593a`)
was committed before the first API call and before the DTU launch.**

---

## 1. Deliverables, each resolved independently

| # | deliverable (from the goal) | state | evidence |
|---|---|---|---|
| 1 | **3 arms × n=6, pre-registered and committed BEFORE launch with the SHA quoted** | **DONE** | `PREREG.md` @ **`a4506d3a96b5bee27eb16576e1aa859a67c6593a`**; 18 launches, **18 valid**, achieved validity **1.000**; arms (a) all-deferred, (b) three tools always-visible, (c) control |
| 2 | **Per-tool EXECUTED-call counts per arm from `role:tool` result entries, discriminator quoted** | **DONE** | `FINDINGS.md` §2. Discriminator quoted verbatim; **42 of 42 cells** also agree with the `tool:pre` counter; instrument validated at **$0** against `webu`'s published table **before** spending (`evidence/instrument-validation-vs-webu.json`) |
| 3 | **`apply_patch` substitution rate per arm** | **DONE** | `apply_patch` calls **a 35 · b 27 · c 30**; D2 bash-surrogate sub-rate **a 0.0 · b 0.1 · c 0.1** (`FINDINGS.md` §2, §5) |
| 4 | **G9 head saving per arm** | **DONE** | saving vs control: **a −5,470 tok · b −2,782.5 tok** (pinned `cache_read`); **a −6,317.5 · b −2,783.5** (`cache_write` @ req 0). Arm b's saving is smaller, as required; **it is 50.9% / 44.1% of arm a's** (`FINDINGS.md` §4) |
| 5 | **THE RULE, applied verbatim** | **DONE** | clause 1 **FAIL** (−36.4%) · clause 2 **PASS** 50.9% / **FAIL** 44.1% → **`DON'T-BUILD STANDS`**. No design item filed, per the rule. No default shipped |
| 6 | **Pins proven on the wire** | **DONE** | provider-openai **`702b361a…`**, context-simple **`ee26d233…` = `ee26d23`**, driver md5 **`dc307c50`** 18/18; `tool_search`+`defer_loading` present on the wire in arms a **and** b; `namespace` round-trip present; **0** `Missing namespace` 400s; control provably untreated on its own wire; `mikb` split-state **ABSENT** (`wire/pin-proof-P1-P2-P5-P6.txt`, `ANALYSIS.json:pins_on_wire`) |
| 7 | **SPLIT table T-5NS, never the `web` namespace** | **DONE** | namespaces observed on the wire: `delegation`, `files`, `internet`, `knowledge`, `shell`. `web` never appears |

---

## 2. Spend — recorded to the cent, with arithmetic

```
18 launches · 18 valid · achieved validity 1.000 · $19.9013 of $25 · $1.1056 per launch

PRE-REGISTERED   6 runs x 3 arms x $0.9386 (webu's 20-run mean) / 1.000 valid = $16.89  <= $25
OBSERVED, stated BEFORE the bulk spend (cycle 1: a-01 $0.7893, b-01 $0.8699, c-01 $0.6553)
                 6 x 3 x $0.7715 / 1.000                                      = $13.89  <= $25
ACTUAL                                                                        = $19.90  <= $25
                 (+17.8% over the pre-registered estimate; the cap still never bound)

residue $5.0987  =  ~4.6 launches at the observed $1.1056
```

**The residue is deliberately unspent, and this is a choice, not an oversight.** The smallest
purchase that could advance anything is 1 launch ($1.11), which the residue *can* afford — but
buying more runs **after reading the verdict** is post-hoc n inflation. The design was
pre-registered at n=6/arm and is complete at n=6/arm. The honest use of $5.10 is a new
pre-registered question, not a bigger n for this one.

Per-arm spend: **a $6.7927 · b $5.3899 · c $7.7187.**

---

## 3. Decisions taken without a human (goal: choose, record, continue)

1. **One DTU, arms switched in-container.** The lane's DTU allocation is **1**, and the three arms
   differ only by the `tool_search` key. Arms were set by rewriting that key on all 5
   `provider-openai` blocks of `/root/.amplifier/settings.yaml`, with the **same rewrite path used
   for the control**, so the arms cannot differ in how the file was produced. **The arm is never
   taken on trust:** every run's arm is re-derived from its own captured request and must match its
   assignment or the run is INVALID (`PREREG.md` §4 V3). **18 of 18 matched.** Side benefit over
   `webu`'s 8-container design: container-level confounds are removed entirely.
2. **Interleaved round-robin `a,b,c × 6`** rather than arm-blocked, so provider drift over the
   ~90-minute session is spread across arms instead of confounded with one.
3. **Clause 1's primary statistic is the three tools AGGREGATED**, with the per-tool form reported
   beside it. Registered before launch, with the reason: at n=6 the per-tool counts are too small
   for a ±30% band to carry information (`delegate` alone: P = 0.404 even under perfect
   restoration).
4. **Clause 2 is reported on BOTH estimators** because they straddle the 50% threshold (50.9% vs
   44.1%). The pre-registered one (pinned `cache_read`) gives the verdict; the disagreement is
   reported, not resolved by preference. **The overall verdict is robust either way** — clause 1
   fails on both.
5. **No design item filed** (the rule conditions it on REVISIT). One *discovered* item was filed —
   `model_performance-3413`, the G9 estimator instability — because it is a measurement finding
   about how a published number should be quoted, not a build proposal.

---

## 4. Deviations from the pre-registration

**None in the design, the arms, the thresholds, or the discriminator.** Two things are worth naming:

- The **pre-registered price** ($0.9386/launch) under-estimated the actual ($1.1056/launch) by
  17.8%; the cap still closed with $5.10 to spare.
- The pre-registered **REACH-RESTORED** bar (`b ≥ 4/6` and `a ≤ 1/6`) was met exactly (**b 4/6,
  a 1/6**). Its Fisher p against arm a is **0.2424** — suggestive, not significant — and is reported
  as such rather than being quietly upgraded. The significant contrast is **a 1/6 vs c 6/6,
  p = 0.0152**, against **b 4/6 vs c 6/6, p = 0.4545**.

---

## 5. Infrastructure — registered, claimed, torn down

| id | type | note |
|---|---|---|
| `p2gxp` | DTU | the lane's single allocated container; all 18 runs |
| `dtu-0318529b` | DTU | **a partial launch of mine**: the first `launch` was invoked without `--name` and its host process was killed by a tool timeout mid-provisioning. Registered, claimed, and destroyed before relaunching. Recorded here rather than left silent |

Both rows were added with `infra_ledger.sh add` at creation and claimed with
`lane_teardown.sh … claim`. Teardown used `lane_teardown.sh … teardown --yes` with the **full** lane
name. **`infra_ledger.sh sweep` was never run** — it is the manager's batch-close verb and other
lanes were live throughout.

---

## 6. Files this lane wrote

**Inside the lane artifact root** (`docs/lanes/webu2-tool-vanishing-probe/`):
`PREREG.md` · `FINDINGS.md` · `DONE-NOTE.md` · `analyze.py` ·
`2gxp-00-what-we-know.diff` + `2gxp-00-what-we-know.section.md` (**proposed** — the lane did not
edit `ai-notes/00-what-we-know.md` or `probes/INDEX.md`) ·
`evidence/instrument-validation-vs-webu.json` · `evidence/power_check.py` + `power-check.txt` ·
`evidence/predict_head_saving.py` + `predicted-head-saving.txt`.

**Outside the repo** (captures, per the goal):
`/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-2gxp-tool-vanishing/`
— 18 run directories, `ANALYSIS.json`, `profiles/`, `wire/pin-proof-P1-P2-P5-P6.txt`,
`observed-price-before-bulk-spend.txt`, the harness (`run_cell.sh`, `seq_runs.sh`, `set_arm.py`).

**The proposed diff is a pure append at EOF.** If another lane's append lands first, apply
`2gxp-00-what-we-know.section.md` verbatim as a new trailing section instead of running `patch`
(the `147-lines-out-of-place` near-miss is why both forms are provided). Section letter **(s)** —
(q) is `i0cm`, (r) is `webu`.
