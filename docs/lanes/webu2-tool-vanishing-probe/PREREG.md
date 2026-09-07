# `2gxp` — pre-registration (written and committed BEFORE any API call or DTU launch of this lane)

**Item:** `model_performance-2gxp` · **Date:** 2026-09-06 · **Lane:** `webu2-tool-vanishing-probe`
**Repo/branch:** `microsoft/amplifier-bundle-evaluation` @ `lane/webu2-tool-vanishing-probe`
**Capture root:** `/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-2gxp-tool-vanishing/`

**Parent pre-registrations, neither replaced by this file:**
- `ai-notes/w3-deferred-tool-loading/EVAL-SPEC.md` §3 (G9 and the arm definitions)
- `docs/lanes/webu-deferred-tools-phase2-rerun/PREREG.md` @ `c37ad942822e9c648bdc8b6cb10250950c512a96` (the arms this lane reproduces)

**Nothing below was computed from a run of this lane before this file was committed.** Numbers
quoted from `webu`'s already-published capture are labelled as such; they are prior art, not this
lane's results. A DTU launch runs a warm-up `amplifier run` during provisioning, which is an API
call, so provisioning is inside the fence too: this file is committed first.

Rule honoured: `00-what-we-know.md` rule 5 — *a gate you write after seeing the result is not a gate*.

---

## 0. What this lane buys, in one sentence

`webu` returned **DON'T-BUILD** on a judgment call: three deferred tools (`write_file`, `edit_file`,
`delegate`) went to **zero executed calls** while the always-visible `apply_patch` absorbed the work.
This lane asks **which cause** — *deferral + substitutability*, or *prompt wording* — by adding one
arm that defers everything **except** those three.

**No default is shipped in this lane, whatever the verdict.** The default stays `off`.

---

## 1. The three arms — the only variable is the `tool_search` block

All three arms run in **ONE DTU** (this lane's DTU allocation is 1), in the same container, against
the same S3 scenario, same driver, same pins. The arm is set per run by rewriting the
`tool_search` key on **every** `provider-openai` block of `/root/.amplifier/settings.yaml`, and is
**verified on that run's own captured wire** (§4 V3). Nothing else is touched between runs.

| arm | `tool_search` | `always_loaded` | reproduces |
|---|---|---|---|
| **a** | `mode: namespaced` | `[bash, todo]` | `webu`'s `t1` (treatment as-run) |
| **b** | `mode: namespaced` | `[bash, todo, write_file, edit_file, delegate]` | **new** — the three tools kept always-visible |
| **c** | *absent* | — | `webu`'s `t0` (control, no deferral) |

`apply_patch` is a **native** tool shape (`{"type":"apply_patch"}`), never namespaced and never
deferred by the provider (`_tool_search.py:build_namespaced_tools`, pin `702b361`) — it is
always-visible in all three arms, which is exactly why it is the substitution channel under test.

**n = 6 per arm, 18 runs.** Order is **interleaved round-robin** `a,b,c · a,b,c · …` (6 cycles), so
any drift over the session (provider latency, container state, residency) is spread evenly across
arms rather than confounded with one. Run ids: `a-01..a-06`, `b-01..b-06`, `c-01..c-06`.

---

## 2. The measurement — the discriminator, fixed now, and validated at $0 before launch

**Primary discriminator (the one the item mandates):** an executed tool call is a
**`{"role": "tool", "name": "<tool>"}` entry in `transcript.jsonl`** of any session in the run tree.
A thinking-text mention of a tool name is **not** a call and is never counted.

```
executed_calls(tool, run) = |{ line in <run>/all-sessions/**/sessions/*/transcript.jsonl :
                               json(line)["role"] == "tool" and json(line)["name"] == tool }|
reach(tool, arm)          = |{ runs in arm with executed_calls(tool, run) >= 1 }|
```

**Corroborating discriminator, reported beside it, never substituted for it:** `tool:pre` events in
`events.jsonl` (`data.tool_name`), whole-tree scoped by the `parent_id` chain, the counter
`webu`'s `analyze.py` used.

**Instrument validated against a value already known, at $0, before this lane spends anything.**
Both counters were run over `webu`'s published capture and reproduce its FINDINGS §3 table exactly:

| tool | `webu` published t0→t1 | this instrument, `role:tool` | this instrument, `tool:pre` |
|---|---|---|---|
| `write_file` | 3/10 → 0/10 · 12 → 0 | 3/10 → 0/10 · 12 → 0 | 3/10 → 0/10 · 12 → 0 |
| `edit_file` | 4/10 → 0/10 · 24 → 0 | 4/10 → 0/10 · 24 → 0 | 4/10 → 0/10 · 24 → 0 |
| `delegate` | 4/10 → 0/10 · 6 → 0 | 4/10 → 0/10 · **5** → 0 | 4/10 → 0/10 · 6 → 0 |
| `apply_patch` | 8/10 → 10/10 · 41 → 58 | 8/10 → 10/10 · 41 → 58 | 8/10 → 10/10 · 41 → 58 |

**The one disagreement is disclosed now, before it can be explained away:** control `delegate` is
**6** by `tool:pre` and **5** by `role:tool` — one delegate call was issued and never produced a
result entry in the transcript. Both figures are reported per arm; the `role:tool` figure is the
verdict figure, per the item.

**Head saving (G9 quantity), unchanged from `webu` so the arms stay comparable:**
`pinned cache_read` = `cached_tokens` of the **first root `llm:response` reporting ≥ 1024**.
`saving(arm) = median(pinned cache_read, arm c) − median(pinned cache_read, arm)`.
`cache_write` at request 0 is reported as the independent corroboration, as `webu` did.

---

## 3. THE RULE, and exactly how it is applied

Quoted verbatim from the item:

> if arm (b) restores the three tools to **within ±30% of control** **AND** keeps **≥50% of arm
> (a)'s head saving** → **REVISIT `webu`** (file the design item). **Otherwise `webu`'s DON'T-BUILD
> STANDS.**

**Clause 1 — restoration. PRIMARY statistic: the three tools taken TOGETHER.**

```
agg(arm)  = ( sum over runs of executed_calls(write_file) + executed_calls(edit_file)
              + executed_calls(delegate) ) / n_valid(arm)          # mean calls per run
CLAUSE 1 PASSES iff  | agg(b) / agg(c) - 1 |  <=  0.30
```

**Reported beside it, and NOT the verdict statistic: the per-tool form** — `|calls_b/calls_c − 1| ≤ 0.30`
for each of `write_file`, `edit_file`, `delegate` separately. A tool with `calls_c == 0` is recorded
`UNINFORMATIVE-ZERO-CONTROL`, never PASS and never FAIL.

**Clause 2 — head saving.**

```
CLAUSE 2 PASSES iff  saving(b)  >=  0.50 * saving(a)
```

**VERDICT.** `REVISIT` **iff clause 1 PASSES and clause 2 PASSES**. In every other case —
including any case where a clause is UNINFORMATIVE — **`webu`'s DON'T-BUILD STANDS**, because an
uninformative clause cannot establish the restoration the REVISIT branch requires. Either verdict
is a complete result and a PASS of this item.

---

## 4. Validity — fixed now, per run

A run is **VALID** iff all of:

- **V1** `md5(scripted_driver.py) == dc307c50090b11d981eee44382668431` (`i0cm`'s fixed driver).
- **V2** all 5 turns captured, `transcript.txt` non-empty, `scorecard.json` parses.
- **V3 — arm shape proven on that run's own wire** (this is what makes in-container arm switching
  safe; the profile is never trusted):
  - arm **c**: **no** `{"type":"tool_search"}` entry and **no** `defer_loading` key anywhere in the
    request `tools` array;
  - arm **a**: `tool_search` entry present **and** `defer_loading: true` on `write_file`,
    `edit_file`, `delegate`;
  - arm **b**: `tool_search` entry present, `defer_loading` **absent** on `write_file`, `edit_file`,
    `delegate`, **and** `defer_loading: true` on at least `read_file`, `grep`, `glob`.
- **V4** zero `Missing namespace for function_call` HTTP 400s in the run tree (`webu` saw 0/24).
- **V5** root session resolved and `measure.json` yields a cost.

An INVALID run is reported with its reason and replaced if the cap permits. Achieved validity is
itself reported as a finding.

---

## 5. Pins — proven on the wire, not by asserting the profile

| leg | proof |
|---|---|
| **P-1** | in-container: installed `amplifier_module_provider_openai/_tool_search.py` contains `tool_search` (`grep -c`) |
| **P-2** | in-container: the resolved commit of that install is `702b361a4d4d178da70cef96300591dc4015b9b1` |
| **P-3** | ON THE WIRE: a captured arm-a/arm-b request whose `tools` array carries **both** `{"type":"tool_search"}` **and** ≥1 `"defer_loading": true` |
| **P-4** | ON THE WIRE: a captured request from turn ≥2 whose replayed `function_call` input item carries a `namespace` field |
| **P-5** | in-container: the installed `context-simple` resolved commit, reported verbatim against the goal's `ee26d23` (break 5, `l4s1`) |
| **P-6** | `mikb` split-state trap: the installed package sha and the bundle-cache sha are read **separately** and compared; a split is a hard stop |
| **P-7** | `driver_md5` recorded per run (V1) |

Arm **c** gets the mirror-image proof: provably untreated on its own wire.

The **SPLIT table T-5NS** is the shipped default of pin `702b361` and is used unmodified. The `web`
namespace is **never** re-introduced (reserved; Phase 1 renamed it `internet`).

---

## 6. Predictions, registered BEFORE the spend so they can be wrong

Computed at $0 from `webu`'s already-published capture. **These are predictions, not results.**

**P-A — clause 2 will FAIL, and here is the arithmetic.** From `webu`'s captured control `tools`
array, the per-schema wire cost (chars ÷ 4.627) is `delegate` **3,077.2**, `edit_file` **411.9**,
`write_file` **257.2**; the full set arm a defers is **7,222.2 tok**, and its measured pinned-head
saving was **6,313.5 tok** (ratio 0.874, i.e. ~908.7 tok of namespace overhead added back). Arm b
keeps **3,746.3 tok** of that loaded, deferring only **3,475.9**:

```
proportional model : 6,313.5 * (3,475.9 / 7,222.2)          = 3,038 tok = 48.1% of arm a's saving
overhead model     : 3,475.9 - 908.7                        = 2,567 tok = 40.7% of arm a's saving
```

Both land **below the 50% threshold** ⇒ **clause 2 predicted FAIL**. Recorded now so that a measured
pass is a real surprise and a measured fail is not a retrofit. `cal`'s $0 census under-predicted
`webu`'s head saving by 39%, so this model is not treated as decisive.

**P-B** — arm a reproduces `webu`: `write_file`/`edit_file`/`delegate` reach **0/6**.

**P-C** — if the cause is *deferral + substitutability*, arm b restores those tools to roughly
control rates; if the cause is *prompt wording*, arm b looks like arm a.

### 6a. POWER — the honest limit of the ±30% clause, disclosed before spending

`webu`'s control per-run aggregate of the three tools is `[5, 13, 4, 6, 0, 11, 0, 0, 0, 2]` —
mean 4.10/run and **wildly overdispersed** (4 of 10 runs use none of the three at all).
Bootstrap, 200,000 resamples, **both arms drawn from that same control distribution at n=6**
(i.e. *perfect* restoration, the hypothesis the clause exists to detect):

```
P( clause 1 PASSES | arm b is a perfect clone of control )  =  0.353
```

Per-tool, under a Poisson model at `webu`'s control rates and n=6, the same probability is
`write_file` 0.534 · `edit_file` 0.709 · `delegate` **0.404** (all three simultaneously ≈ 0.153).

**Therefore, stated before the first dollar:** the pre-registered rule has roughly a **1-in-6 to
1-in-3** chance of returning REVISIT *even if the treatment effect is exactly what the REVISIT
branch describes*. That is a property of the rule at n=6, not of the cap — the cap funds the
runs the item asks for (§8). It is registered here so that a DON'T-BUILD-STANDS verdict is read
correctly: **"the rule did not clear" is not the same claim as "the tools did not come back."**

### 6b. The well-powered mechanism observable, registered as a SECONDARY finding

Because §6a shows the ±30% clause cannot carry the mechanism question at n=6, the mechanism
question is answered by **reach**, the observable `webu`'s finding was actually stated in:

```
REACH-RESTORED   iff  reach(any of the three, arm b) >= 4/6   and  reach(..., arm a) <= 1/6
REACH-VANISHED   iff  reach(any of the three, arm b) <= 1/6   and  reach(..., arm a) <= 1/6
```

Fisher exact two-tailed, 6 v 6: `5/6 vs 0/6 → p = 0.0152`; `4/6 vs 0/6 → p = 0.0606`;
`3/6 vs 0/6 → p = 0.1818`. Control's own per-run rate of using ≥1 of the three is 0.60, so a truly
restored arm b shows ≥1 such run with probability **0.996**.

**This secondary observable NEVER overrides the rule.** REVISIT is reached only through §3.
REACH-RESTORED with a failing rule is reported as exactly that: *the tools came back, the
pre-registered rule still did not clear, and here is which clause blocked it.*

---

## 7. Reported beside the verdict, fixed now (no new thresholds)

`apply_patch` substitution rate per arm · the full per-tool reach/call table for all 10 tools ·
`webu`'s D2 bash-surrogate sub-rate per arm · S3 median score and strict-pass per arm ·
mean cost and wall per arm · boundaries per arm · achieved validity per arm · loaded-tool set per arm.

---

## 8. Spend authority, priced BEFORE the bulk spend

Authority **$25**, owner-funded. `webu`'s observed terra price is **$0.9386/launch**, the mean over
its **20** terra runs (`webu` FINDINGS §6; recomputed here from its 20 `measure.json` files:
mean 0.9386, median 0.9060, range 0.6055–1.6181, total 18.7725) — a price quoted over a run count
**larger** than this lane's 18, so reusing it does not repeat `1ru`'s error of reusing a small-set
price for a larger set.

```
6 runs x 3 arms x $0.9386 / 1.000 achieved validity  =  $16.89   <=  $25      CLOSES
                        at 0.80 validity: 22.5 launches x $0.9386 = $21.12    still closes
                        at 0.67 validity: 26.9 launches x $0.9386 = $25.23    would NOT close
```

The arithmetic closes at `webu`'s achieved validity (1.000) with **$8.11** of slack, and still
closes at 0.80. **The observed per-run price of this lane's own first runs is stated before the
bulk spend** and the arithmetic is re-checked against it.

**Stop rule:** stop when the remaining budget cannot fund the smallest purchase that advances a
deliverable — one launch at the observed price. The residue and the purchase it could not buy are
both stated.

---

## 9. Terminal state — chosen ONCE, here

- All 18 runs bought and the rule applied → **OUTCOME A: RESOLVED**, verdict whatever it is.
- The cap binds before n=6/arm → **OUTCOME B: RESOLVED AT THE CAP**, the affected deliverable
  recorded NOT-POSSIBLE with the reason **leading with what was executed**, and the item still
  resolved.
- Unreachable for a reason **other than** the cap → **OUTCOME C: BLOCKED.md** + `work_release`.

There is no fourth branch, and the choice is not re-decided if a later reader disagrees with the
verdict — a DON'T-BUILD confirmation is a PASS of this item, in the item's own words.
