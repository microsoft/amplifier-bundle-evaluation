# `2gxp` — does the tool vanishing come from DEFERRAL, or from PROMPT WORDING? — FINDINGS

**Item:** `model_performance-2gxp` · **Date:** 2026-09-07 · **Spend: $19.9013 of a $25 authority**
**Pre-registration:** `PREREG.md` @ **`a4506d3a96b5bee27eb16576e1aa859a67c6593a`**, committed
**before the first API call and before the DTU launch** of this lane.
**Captures:** `/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-2gxp-tool-vanishing/`
**Regenerate every table below, spending nothing:**
`python3 analyze.py --cap <that dir> --prereg-sha a4506d3a96b5bee27eb16576e1aa859a67c6593a --json ANALYSIS.json`

---

## THE HEADLINE, IN SIX LINES

1. **Every arm ran at full n. 18 launches, 18 valid, achieved validity 1.000.** 3 arms × n=6, one
   DTU, interleaved round-robin, every arm's shape **proven on its own captured wire**, 0
   `Missing namespace` HTTP 400s, 0 G12 hits, driver md5 `dc307c50` on all 18.
2. **THE RULE RETURNS `DON'T-BUILD STANDS`** — which this item states is a **PASS**.
   Clause 1 (restore the three tools to within ±30% of control) **FAILS at −36.4%**;
   clause 2 (keep ≥50% of arm a's head saving) **PASSES at 50.9%** on the pre-registered estimator
   and **FAILS at 44.1%** on its corroborating one. **REVISIT needs both. It does not get both.**
3. **The mechanism question the item actually asked is ANSWERED, and the answer is DEFERRAL, not
   prompt wording.** The only difference between arm a and arm b is whether those three tools carry
   `defer_loading`. Executed calls go **1 → 14**; runs reaching any of the three go **1/6 → 4/6**.
4. **Arm a is significantly worse than control; arm b is statistically indistinguishable from it.**
   Fisher exact, reach of any of the three: **a 1/6 vs c 6/6 → p = 0.0152**;
   **b 4/6 vs c 6/6 → p = 0.4545**; b vs a → p = 0.2424 (suggestive, not significant at n=6).
5. **The head saving is real but it is given back at runtime, and that is new.** In **3 of 6** arm-a
   runs the pinned head **grows after the model calls `tool_search`** (12,4xx at request 0 →
   14,101 / 16,183 / 16,290 later). The steady-state saving is smaller than the request-0 figure
   `webu` published; both estimators are reported here rather than one being picked.
6. **Both of this lane's pre-registered warnings landed.** The predicted head-saving band
   (40.7–48.1% of arm a's saving) contains the corroborating measurement (**44.1%**); and the
   **power ceiling of 0.353** registered for clause 1 is exactly why a −36.4% miss must not be read
   as "the tools did not come back" — **they demonstrably did.**

---

## 1. THE RULE, quoted verbatim, applied verbatim

> if arm (b) restores the three tools to **within ±30% of control** **AND** keeps **≥50% of arm (a)'s
> head saving** → **REVISIT `webu`**. **Otherwise `webu`'s DON'T-BUILD STANDS.**

| clause | rule as pre-registered (`PREREG.md` §3) | measured | verdict |
|---|---|---:|---|
| **1 — restoration** | `\|agg(b)/agg(c) − 1\| ≤ 0.30`, `agg` = mean executed calls/run of `write_file`+`edit_file`+`delegate` | b **2.333**/run vs c **3.667**/run · ratio **0.636** · **−36.4%** | **FAIL** |
| **2 — head saving** | `saving(b) ≥ 0.50 × saving(a)`, saving on median pinned `cache_read` | saving(a) **5,470** · saving(b) **2,782.5** · **50.9%** | **PASS** |
| **2 — same rule, corroborating estimator** | identical, on median `cache_write` @ request 0 | saving(a) **6,317.5** · saving(b) **2,783.5** · **44.1%** | **FAIL** |

**VERDICT: `DON'T-BUILD STANDS`.** REVISIT requires both clauses; clause 1 fails on either
estimator, so the verdict is **robust to the clause-2 estimator disagreement**. No design item is
filed, per the rule. No default is shipped in this lane.

**Per-tool form of clause 1 — reported, explicitly NOT the verdict statistic** (`PREREG.md` §3):

| tool | b calls/run | c calls/run | ratio | per-tool verdict |
|---|---:|---:|---:|---|
| `write_file` | 0.667 | **0.000** | — | **UNINFORMATIVE-ZERO-CONTROL** (control never used it in 6 runs; arm b used it 4×) |
| `edit_file` | 1.000 | 2.333 | 0.429 | FAIL |
| `delegate` | 0.667 | 1.333 | 0.500 | FAIL |

---

## 2. THE TABLE THAT ANSWERS THE ITEM — per-tool EXECUTED calls, `role:tool` result entries

**Discriminator, quoted:** an executed call is a **`{"role": "tool", "name": "<tool>"}` entry in
`transcript.jsonl`** of any session in the run tree. **A `"type":"thinking"` mention of a tool name
is not a call and is never counted** — that is the exact confusion that made the manager's first
recompute of `webu` read `write_file` as 9/10 runs when its `role:tool` entries were absent.

**Both counters agree on 42 of 42 cells** in this lane (`role:tool` / `tool:pre`). `webu`'s single
disagreement (control `delegate` 6 by `tool:pre` vs 5 by `role:tool` — one issued call that never
produced a result entry) **did not recur**.

| tool | deferred in a? | **a** reach · calls | **b** reach · calls | **c** reach · calls |
|---|---|---:|---:|---:|
| **`write_file`** | a: yes · b: **no** | **0/6 · 0** | **1/6 · 4** | 0/6 · 0 |
| **`edit_file`** | a: yes · b: **no** | **0/6 · 0** | **1/6 · 6** | 3/6 · 14 |
| **`delegate`** | a: yes · b: **no** | **1/6 · 1** | **4/6 · 4** | 6/6 · 8 |
| **the three, aggregated** | | **1/6 runs · 1 call** | **4/6 runs · 14 calls** | **6/6 runs · 22 calls** |
| `apply_patch` | never (native shape) | 6/6 · **35** | 6/6 · 27 | 6/6 · 30 |
| `read_file` | a: yes · b: yes | 6/6 · 73 | 6/6 · 44 | 6/6 · 120 |
| `grep` | a: yes · b: yes | 6/6 · 35 | 4/6 · 20 | 6/6 · 35 |
| `glob` | a: yes · b: yes | 6/6 · 23 | 6/6 · 17 | 6/6 · 21 |
| `load_skill` | a: yes · b: yes | 6/6 · 10 | 6/6 · 8 | 6/6 · 10 |
| `bash` | never (always-loaded) | 6/6 · 41 | 6/6 · 47 | 6/6 · 53 |
| `todo` | never (always-loaded) | 6/6 · 45 | 6/6 · 41 | 6/6 · 58 |

**Arm a reproduces `webu`'s t1 almost exactly**: `write_file` 0, `edit_file` 0, `delegate` 1 call in
1 of 6 runs (`webu`: 0 of 10), while the always-visible `apply_patch` carries the most calls of any
arm (**35**, vs control's 30 — the absorption `webu` measured).

**Arm b restores them.** The three tools go from **1 executed call across 6 runs** to **14**, and
`delegate` — the capability `webu` called "the one that matters" — comes back in **4 of 6** runs.
Nothing else changed: same container, same scenario, same driver, same pins, same prompt.

---

## 3. So the answer to the item's question is DEFERRAL — with one honest qualification

**The item asked:** *is the vanishing caused by DEFERRAL + SUBSTITUTABILITY, or by PROMPT WORDING?*

Arm a and arm b are **byte-identical apart from which tools carry `defer_loading: true`** — same
system prompt, same S3 turns, same 5 namespaces, same always-visible `apply_patch`. Prompt wording
is held constant **by construction**. Moving three tools out of the deferred set moved their use
from 1 call to 14. **Deferral is the cause. Prompt wording is not.**

**The qualification, stated because it is not a full restoration:** arm b recovers **64%** of
control's call volume, not 100%, and the pre-registered ±30% band rejects that. Two readings survive
the data and this lane does not pretend to separate them at n=6:

- **(i) Real residual suppression.** A namespaced always-loaded member is still *inside* a namespace
  object; it may be marginally less salient than a flat top-level tool.
- **(ii) Sampling.** Control's own per-run aggregate is wildly overdispersed — `webu`'s was
  `[5,13,4,6,0,11,0,0,0,2]`, this lane's control is `[1,1,6,1,6,7]`. The registered power ceiling
  for clause 1 was **0.353 even under perfect restoration**; a −36.4% miss is well inside that noise.

`b 4/6 vs c 6/6 → p = 0.4545`: **arm b is not statistically distinguishable from control.**
`a 1/6 vs c 6/6 → p = 0.0152`: **arm a is.** That contrast is the finding.

---

## 4. The head, and the part of the saving that is handed back at runtime

| quantity (median over 6 valid runs) | **a** | **b** | **c** |
|---|---:|---:|---:|
| **pinned `cache_read`** (the G9 quantity, pre-registered) | **13,256.5** | **15,944.0** | **18,726.5** |
| `cache_write` @ request 0 (corroboration) | 12,409.0 | 15,943.0 | 18,726.5 |
| total billed prompt @ request 0 | 16,181.5 | 16,781.5 | 18,729.5 |
| non-cacheable term @ request 0 (cold-start cost) | **3,771.0** | **837.5** | 3.0 |
| tools-array **wire** payload (chars ÷ 4.627) | 8,310.1 | 8,296.5 | 8,117.1 |
| saving vs control, pinned `cache_read` | −5,470.0 | −2,782.5 | — |
| saving vs control, `cache_write` @ req 0 | −6,317.5 | −2,783.5 | — |

**The new observation.** In arm c and mostly in arm b the two estimators agree to ~1 token. In
**arm a they diverge by 847 tokens at the median**, and per run the reason is visible:

```
a-01 12,409 / 12,409   a-02 12,412 / 12,412   a-03 12,409 / 12,409      (pinned / cache_write@req0)
a-04 16,183 / 12,404   a-05 14,101 / 12,410   a-06 16,290 / 12,407      <-- head GREW mid-run
b-02 17,658 / 15,942   b-05 19,165 / 15,946                             <-- same effect, smaller
```

In **3 of 6** arm-a runs the model called `tool_search`, the loaded tool schemas entered the cached
prefix, and the head that is actually pinned for the rest of the run is **1.7k–3.9k tokens larger**
than the request-0 figure. **`webu`'s published −6,313.5 tok / −33.7% is the request-0 saving, not
the steady-state saving**; on this lane's n=6, steady state is **−5,470 (−29.2%)**. `webu` was not
wrong — it measured what it registered, and its two estimators agreed *on its runs* — but the
quantity is not stable across runs, and a reader should not treat request-0 head saving as what the
run costs. Filed as discovered work (`model_performance-3413`).

**Arm b's cold-start term is 4.5× smaller than arm a's** (837.5 vs 3,771.0): fewer deferred schemas
means less non-cacheable `tool_search` machinery on the cold request.

---

## 5. Everything else that was pre-registered to be reported (no new thresholds)

| quantity | **a** | **b** | **c** |
|---|---:|---:|---:|
| launches · valid · achieved validity | 6 · 6 · **1.000** | 6 · 6 · **1.000** | 6 · 6 · **1.000** |
| median S3 score · strict-pass | 90 · **6/6** | 100 · 5/6 | 100 · 5/6 |
| mean cost / run | $1.1321 | **$0.8983** | $1.2865 |
| mean wall (s) | 250.6 | 259.8 | 299.7 |
| compaction boundaries | 0 | 0 | 0 |
| D2 bash-surrogate sub-rate (median) | **0.0** | 0.1 | 0.1 |
| surrogate calls · file-domain calls | 10 · 166 | 16 · 118 | 24 · 220 |
| `Missing namespace` HTTP 400s · G12 hits | 0 · 0 | 0 · 0 | 0 · 0 |

**No quality harm is visible in any arm** — and S3 remains the ceiling-bound instrument `webu`
flagged: it cannot price the delegation that arm a loses, because S3 never needs delegation.
**`webu`'s D2 tripwire again moves protectively** (arm a's surrogate rate is the *lowest* of the
three), reproducing its −8.0 pp result: **the harm still takes a shape that rule cannot see.**

The cost ordering (**b cheapest, c dearest**) is **not banked**: `c-05` alone cost $2.59 and the
arms differ by less than the run-to-run spread. Descriptive only, at n=6.

---

## 6. Pins, proven on the wire

| leg | result |
|---|---|
| **P-1** | `grep -c tool_search` over the installed provider package = **80** (`cal` measured 0 at pre-`v5co` HEAD `94dd5ed`) |
| **P-2** | provider-openai install resolves to **`702b361a4d4d178da70cef96300591dc4015b9b1`** — the sha the goal names |
| **P-3** | ON THE WIRE: arm a **and** arm b requests carry both `{"type":"tool_search"}` and ≥1 `"defer_loading": true` — **true for both** |
| **P-4** | ON THE WIRE: replayed `function_call` input items carry a `namespace` field — **true** |
| **P-5** | context-simple resolves to **`ee26d233ddc4f7db30eb77dbe94ff52561035a71`** = **`ee26d23`**, break 5, landed by `l4s1` |
| **P-6** | `mikb` split-state trap: exactly **one** install path per module, no `site-packages` copy — **ABSENT**, as `webu` also found |
| **P-7** | driver md5 `dc307c50090b11d981eee44382668431` on **18 of 18** runs |
| **control** | arm c is **provably untreated** on its own wire: no `tool_search` entry, no `defer_loading` key, in all 6 runs |

Namespaces observed on the wire: `delegation`, `files`, `internet`, `knowledge`, `shell` — the
**SPLIT table T-5NS**. The reserved `web` namespace was never re-introduced.

**Arm assignment is never taken on trust.** Arms were switched inside one container by rewriting
`tool_search` on all 5 `provider-openai` blocks; every run's arm was then **re-derived from its own
captured request** (`PREREG.md` §4 V3) and had to match its assignment or the run is INVALID.
18 of 18 matched.

---

## 7. Spend

```
18 launches, 18 valid (validity 1.000), $19.9013 of $25  =  $1.1056 / launch

pre-registered arithmetic : 6 x 3 x $0.9386 / 1.000 = $16.89   (webu's price, 20-run mean)
observed after cycle 1    : 6 x 3 x $0.7715 / 1.000 = $13.89   (recorded before the bulk spend)
ACTUAL                    :                           $19.90   (+17.8% over the prereg estimate)
residue                   : $5.0987  =  ~4.6 launches at the observed price
```

**The residue is deliberately unspent.** Buying more runs *after* reading the verdict would be
post-hoc n inflation: the design was pre-registered at n=6/arm and is complete at n=6/arm. The
honest use of $5.10 is a *new* pre-registered question, not a bigger n for this one.

---

## 8. What a reader should take from this

1. **`webu`'s DON'T-BUILD verdict stands, on this lane's own pre-registered rule.** That is a PASS
   of this item, in the item's words.
2. **The reason `webu` gave for it is now mechanistically confirmed and mechanistically fixable.**
   The three tools vanish **because they are deferred while a substitute stays visible** — not
   because of prompt wording. Undeferring them brings them back to a level statistically
   indistinguishable from control.
3. **The fix has a price, and the price is roughly half the win.** Keeping `write_file`,
   `edit_file` and `delegate` always-visible costs **56% of the head saving** (2,782.5 of 5,470
   tok), because `delegate` alone is 3,077 tok of schema. A future proposal has to argue that trade
   on its merits; **this lane ships no default and files no design item.**
4. **Do not read a failed ±30% clause as "the tools stayed gone."** Registered before launch: that
   clause passes only 35% of the time even under perfect restoration at n=6. The reach evidence,
   not the ratio, is what carries the mechanism.
5. **Request-0 head saving ≠ steady-state head saving** in the deferred arm. Three of six arm-a runs
   re-grew the pinned head after `tool_search`. Quote which estimator you mean.
