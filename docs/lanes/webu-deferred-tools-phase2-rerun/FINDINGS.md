# `webu` — Phase 2, the measurement PR 83 reverted PR 82 for — FINDINGS

**Item:** `model_performance-webu` · **Date:** 2026-09-07 · **Spend: $30.4669 of a $170 authority**
(separate, owner-funded; the $60 programme cap stands at **$1.11479** — the two are reported, never netted)

**Pre-registration commits, all committed BEFORE the numbers they gate:**

| file | commit | fixed before |
|---|---|---|
| `PREREG.md` | **`c37ad942822e9c648bdc8b6cb10250950c512a96`** | the first API call **and** the first DTU launch |
| `PREREG-ADDENDUM-A.md` | **`ce4add33a29da9f80c81ff8d848ee06e1498d907`** | any run output was read |
| `PREREG-ADDENDUM-B.md` | **`d37487e0be36b67e74dc91d03d006baccd432624`** | 18 of the 20 terra runs were bought |
| `PREREG-ADDENDUM-C.md` | **`e8a7cdc1c0c577ca24b474a032864122edc2333c`** | 10 of the 24 runs, and the whole 2nd guardrail pair, existed |

**Parent pre-registration:** `ai-notes/w3-deferred-tool-loading/EVAL-SPEC.md` §3 (prereg `a386a20`).
**No threshold in EVAL-SPEC was altered by this lane.**

**Captures:** `/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-webu-phase2/`
**Regenerate every table below, spending nothing:** `python3 analyze.py --cap <that dir> --json ANALYSIS.json`

---

## THE HEADLINE, IN SIX LINES

1. **Every arm ran, as pre-registered, at full n. 24 launches, 24 valid, achieved validity 100%.**
   `t0`/`t1` S3 terra-medium **n=10 each**; the mandatory `g0`/`g1` Anthropic guardrail **n=2 each**,
   **LIVE**, not a hash replay. **$30.47 of $170.** The cap never bound.
2. **G9 PASS, and larger than anyone predicted.** The pinned head falls **18,725 → 12,411 tok**,
   a saving of **6,313 tok = 33.7%**, corroborated to **2 tokens** by an independent server-side
   figure. `cal`'s $0 census predicted 4,540 tok / 24.6% — **it under-predicted by 39%.**
3. **All four blocking Anthropic guardrail gates PASS on a LIVE RUN.** `tools` sha256
   **`561cd6fcbba28d79` identical at 53 of 53 request indices, 0 divergences**; system prompt
   **46,677 B in both arms, delta +0 B**; cache share within **3.0 / 4.9 pts**; re-warm **1 request
   at all 8 boundaries in both arms**; `ID_ONLY` **0**. The Anthropic path cannot observe the flag.
4. **The pre-registered D2 rule did NOT fire — and it did not fire because I wrote it too narrow.**
   Bash-surrogate substitution went the *protective* way (**8% → 0%, −8 pp**). But 6ei's own D2
   *form* — "reached in static, not in deferred" — applied to every tool shows
   **`write_file` 3/10 → 0/10, `edit_file` 4/10 → 0/10, `delegate` 4/10 → 0/10**, absorbed by the
   one always-visible tool, `apply_patch` (8/10 → **10/10**, +17 calls). **That is a larger and more
   complete recurrence than the 2/23 that caused PR 83.**
5. **Verdict: DON'T-BUILD as a default** — which this item states is a **PASS**. The saving is real,
   the containment is proven, the quality instrument saw no harm *on S3*; and S3 is exactly the
   scenario that cannot see the capability that vanished. **No default is shipped in this lane.**
6. **Two numbers in the goal were wrong by a lot, in the safe direction:** the observed terra price
   is **$0.939/launch, not $4.63** (4.9× over-estimate), and achieved validity is **100%, not 67%**.
   The $170 authority bought the deliverable **5.6× over**.

---

## 1. Every gate, its rule quoted verbatim, its verdict, its measured value

### 1a. The capability gates

| id | rule (verbatim from `EVAL-SPEC.md` §3) | verdict | measured value |
|---|---|---|---|
| **G9** | *"Head reduction, in a real run. `t1` median pinned `cache_read` **≤** `t0` median − 3,000 tok"* | **PASS** | `t0` **18,725** → `t1` **12,411.5**; **saving 6,313.5 tok = 33.7% of the head**. Independent corroboration (`cache_write` @ req 0): 18,725 → 12,409.5, **agrees to 2 tok**. n=10/10 |
| **G10** | *"Quality non-inferiority. `t1` S3 median **≥** `t0` S3 median − 5 points, and `t1` strict-pass count ≥ `t0` − 1 of 10"* | **PASS on the strict-pass clause · median clause UNINFORMATIVE (ceiling)** | medians **100 / 100** — both at the S3 maximum, so that clause carries no information and is **not banked as no-harm**. Strict-pass **9/10 → 8/10**, which satisfies "≥ t0 − 1" **exactly at the threshold**. Scores `t0` [80,100×9] · `t1` [80,100×7,90,88] |
| **E5** (the gate `6ei` recorded **NOT MEASURED**) | `PREREG.md` §1b — two clauses, the second still informative at ceiling | **PASS** | E5-total = G10. E5-constraint: largest single-constraint drop is **1 of 10** (`C3 <120 lines` 10→9, `turn-3 revision` 9→8); the FAIL threshold is a drop of **≥2**. C1, C2, turn-2 retention, turn-5 extension: **10/10 in both arms** |
| **G11** | *"Cost. `t1` mean $/run **≤** `t0` mean $/run, with boundary counts within ±15%"* | **ADVISORY — cost clause PASS, cadence clause UNDEFINED** | mean cost **$0.9991 → $0.8782** (−12.1%). Boundaries **0.0 in both arms**, so the ±15% cadence clause is **undefined, not passed**. See §4 for the confounder that makes the cost figure unsafe to bank |
| **G4′** | *"Real loaded set (tripwire T4). Median distinct tools actually loaded per run **≤10 of 14**"* | **PASS** | `t1` median **10** (`t0` **13**). 9 of 10 `t1` runs load exactly `{bash, todo, edit_file, glob, grep, read_file, write_file, load_skill, mode, recipes}`; one run (`t1-04`) loaded **3**. **`delegate`, `web_search`, `web_fetch` were loaded in 0 of 10 runs** |
| **G12** | *"Tool-pair atomicity. `InvalidRequestError: No tool call found for function call output` count == **0** across all 10 `t1` runs"* | **PASS** | **0 hits.** 654 occurrences of the bare token `InvalidRequestError` were **excluded as false positives** — the S3 scenario seeds provider config-validation *source* that contains it (§5.3) |
| **G13** | *"Compaction survival …"* | **UNINFORMATIVE — no boundary crossed, and the dependency is unlanded** | **0 compaction boundaries in all 10 valid `t1` runs.** `context-simple` **break 5** has landed nowhere (`v5co` shipped it as a patch artifact). **Never recorded PASS under either branch** (`PREREG.md` §3) |

### 1b. The blocking Anthropic guardrail — **LIVE**, both pairs

`cal`: *"a gate that cannot fail is worse than an unbought gate."* None of these is a hash replay.
Pair **01** ran at the default compaction budget (0 boundaries); pair **02** at 45,000
(**9 boundaries in each arm**), so EVAL-SPEC's *"multi-turn with ≥3 compaction boundaries"* is met.
Arms are compared **within a pair**, never across.

| id | rule (verbatim) | verdict | measured value |
|---|---|---|---|
| **G5a** | *"`sha256` of `params["tools"]` equal between `g0` and `g1` at **every** request index — N of N identical, 0 divergences, no tolerance band"* | **PASS** | **53 of 53** indices identical (pair 01: 27, pair 02: 26). **0 divergences.** `g0` and `g1` each emit exactly **one distinct** tools sha for the whole run: **`561cd6fcbba28d79`** in both arms |
| **G5b′** | `cal` §1c re-scope — **absolute per-arm**: B1 exactly one marker · B2 breakpoint used · B3 on the last entry that can carry one · B4 ≤4 markers | **PASS** | **121 requests checked across both arms and both pairs, 0 violations.** Chosen over old-G5b because old-G5b is a pure function of the array G5a hashes and has **zero marginal coverage** |
| **G5c** | *"Distinct `instructions` sha256 per run == 1; byte delta vs control == **+0 B**"* | **PASS** | **1 distinct system sha per run** in every arm of both pairs; **46,677 B in `g0` and 46,677 B in `g1`**, **delta +0 B**, both pairs |
| **G5d** | *"`cache_read` share within **±10 pts** of `g0`; re-warm **≤1 request** at every boundary; `ID_ONLY` divergences == **0**"* | **PASS** | share pair 01 **92.4 → 89.4 (−3.0 pts)**, pair 02 **79.7 → 74.8 (−4.9 pts)**; **re-warm = 1 request at all 8 boundaries in `g1` and all 8 in `g0`**; `ID_ONLY` **0** |

**T3, the merge blocker, is not tripped.** The Anthropic request path is byte-identical with the
flag on, proven live across 121 requests and 8 real compaction boundaries.

### 1c. The tripwires

| id | rule | verdict | measured value |
|---|---|---|---|
| **D2** (as pre-registered, `PREREG.md` §1a) | *median(`sub_rate` t1) − median(`sub_rate` t0) ≥ 0.05* | **DID NOT FIRE** — and moved **protectively** | median shell-surrogate rate **`t0` 0.08 → `t1` 0.00**, **delta −8.0 pp**. Counts: `t0` 18 surrogates / 265 file-domain calls; `t1` 10 / 221. **Strong surrogates (`cat`/`head`/`tail`/`sed`/`grep`/`rg`) = 0 in BOTH arms** |
| **D2-class** (6ei's own D2 *form*, every tool — **NOT** the pre-registered rule) | *reached in static but not in deferred* | **PRESENT — see §3** | `write_file` **3/10 → 0/10** · `edit_file` **4/10 → 0/10** · `delegate` **4/10 → 0/10** |
| **T4** | median loaded ≤ 10 | not tripped | G4′ above |
| **T3** | Anthropic containment failure | not tripped | G5a–G5d above |

---

## 2. The DTU pin, proven ON THE WIRE — four legs, all PASS

The goal requires `702b361` *"demonstrated by a captured request carrying the `namespace`/`tool_search`
fields — not by asserting the profile"*, and names `mikb`'s split-state trap.

| leg | what it proves | result |
|---|---|---|
| **P-1** | the **installed** package's own source carries the feature | `grep -c tool_search` on the installed `amplifier_module_provider_openai/*.py` = **80** in all four containers (`cal` measured **0** at pre-`v5co` HEAD `94dd5ed`) |
| **P-2** | the resolved commit is the one the goal names | **`702b361a4d4d178da70cef96300591dc4015b9b1`**, recorded by the installer, in all four containers. **Exactly one install path exists per container** — the mikb split state was checked for and is **absent** |
| **P-3** | the treatment is on the wire | `t1` root requests carry **`{"type":"tool_search"}`** and `defer_loading: true` on namespace members. The `t1` tools array is **7 entries** — `apply_patch` + the five T-5NS namespaces `[delegation, files, internet, knowledge, shell]` + `tool_search` — against `t0`'s **14 flat functions** |
| **P-4** | `v5co`'s break-6 second half holds across the round trip | a replayed `function_call` **input** item carrying a `namespace` field is present in `t1`. **`Missing namespace for function_call` HTTP 400s across all 24 runs: 0** |
| **control** | the control arm is provably **untreated** | `t0`: **no** `tool_search` entry and **no** `defer_loading` key in any request, all 10 runs |

Every upstream source was pinned to a resolved sha, not `@main`: provider-openai `702b361…`,
provider-anthropic `feca467e…`, foundation `ed64999d…`, routing-matrix `0cc0cf8b…`, CLI `28588b93…`.
`t0` and `t1` profiles differ in **29 lines: 4 of name/description and 25 of `tool_search`** —
the arm is the one variable, and that is proven by diff, not asserted.

---

## 3. THE FINDING THAT DECIDES IT — the model reaches for what it can already see

The pre-registered D2 rule watched **one** channel (`bash` standing in for a file tool), because
that is the channel `6ei` happened to observe. Applying **6ei's own D2 form** — *"tool reached in
static but not in deferred"* — to **every** tool shows a much larger effect on a channel my rule
did not cover.

| tool | deferred? | `t0` reach | `t1` reach | `t0` calls | `t1` calls |
|---|---|---:|---:|---:|---:|
| `read_file` | deferred | 10/10 | 9/10 | 114 | 83 |
| `grep` | deferred | 9/10 | 9/10 | 47 | 53 |
| `glob` | deferred | 9/10 | 8/10 | 27 | 27 |
| `load_skill` | deferred | 10/10 | 10/10 | 19 | 17 |
| **`write_file`** | deferred | **3/10** | **0/10** | 12 | **0** |
| **`edit_file`** | deferred | **4/10** | **0/10** | 24 | **0** |
| **`delegate`** | deferred | **4/10** | **0/10** | 6 | **0** |
| **`apply_patch`** | **always visible** | 8/10 | **10/10** | 41 | **58** |
| `bash` | always visible | 10/10 | 10/10 | 78 | 59 |
| `todo` | always visible | 10/10 | 10/10 | 80 | 79 |

**Two distinct mechanisms, and they are not equally serious.**

**(a) Lateral substitution inside the `files` namespace — probably benign, measured.**
`edit_file` and `write_file` go to **zero** and the always-visible `apply_patch` absorbs them
(+17 calls, reach 8/10 → 10/10). `apply_patch` does the same job, and the quality instrument sees
no harm: median 100 in both arms, `C1`/`C2` 10/10 in both, `C3` 10 → 9.
**Note the asymmetry that makes this specific:** `read_file`, `grep` and `glob` are in the *same*
deferred namespace and were discovered and used normally. Only the tools with an always-visible
substitute vanished.

**(b) Capability disappearance — `delegate`, and this is the one that matters.**
`delegate` is alone in its own `delegation` namespace (the T-5NS split, which exists precisely
because `delegate` is 3,602 tok on its own). **In 10 treatment runs the model never once searched
that namespace**, and `delegate` never appears in the loaded set of any `t1` run. Delegation simply
stopped happening: 6 calls across 4 control runs, **0 calls across 10 treatment runs**.

At n=10/10 that is Fisher-exact **p ≈ 0.087** two-tailed — **suggestive, not significant**, and it is
reported as such. But significance is the wrong test here: the point is that **S3 does not need
delegation**, so this scenario is structurally incapable of pricing what was lost. `00-what-we-know.md`
§2c records delegation as *"the load-bearing confounder"* of this entire programme. A treatment that
silently switches it off is not cleared by a scenario that never asked for it.

**Honesty about what this is.** This is **not** the pre-registered D2 rule firing — that rule did
not fire, and it moved protectively. It is a **third defect this lane found in its own gates**: I
encoded 6ei's *mechanism* rather than 6ei's *phenomenon*. A reader who judges (a) benign and (b)
unproven can reach **BUILD** from exactly these numbers. §6 states why I do not.

---

## 4. The measured tables

### TABLE 1 — the head, and what it really costs (n=10 per arm)

At root request 0 the **`input` is 1,969 chars and `instructions` 45,802 chars in all 20 runs of
both arms** — verified, not assumed — so the tools block is the only difference.

| quantity | `t0` | `t1` | delta |
|---|---:|---:|---:|
| **pinned `cache_read`** (EVAL-SPEC's own words — **the G9 verdict**) | **18,725** | **12,411.5** | **−6,313.5 tok = −33.7%** |
| `cache_write` @ req 0 (independent corroboration) | 18,725 | 12,409.5 | −6,315.5 (**agrees to 2 tok**) |
| total billed prompt @ req 0 (cold request) | 18,728 | 16,171.5 | −2,556.5 |
| **non-cacheable term @ req 0** | **3** | **3,762.5** | **+3,759.5 tok — a real cost** |
| tools-array **wire payload** (12v's chars/4.627) | 8,117.1 | 8,310.1 | **+193 — see §5.2** |
| median distinct tools loaded | 13 | 10 | −3 |
| mean cost / run | $0.9991 | $0.8782 | −12.1% |
| mean wall (s) | 274.5 | 244.3 | −11.0% |
| compaction boundaries | 0.0 | 0.0 | — |
| delegate calls (total) | **6** | **0** | −6 |
| sub-agent sessions in the run tree (total) | **17 − 10 = 7** | **0** | −7 |

**Read both directions or you are being misled.** The **33.7% saving applies from the second
request onward, for the life of the session**; the **cold first request gives back 3,760 tok** of
non-cacheable billed prompt, so its net saving is only 2,557 tok. On a 26-request session the
pinned saving dominates by roughly 25:1 — but a workload of very short sessions would not see it.

**`cal`'s census under-predicted.** It predicted median saving **4,540 tok (24.6%)** from a
149-session joint census, explicitly labelled `inferred`. The real-run figure is **6,313.5 tok
(33.7%)** — **+39%** on the prediction. The census was conservative in the direction it said it
would be (whole-namespace loading is the conservative end).

### TABLE 2 — the Anthropic guardrail, live (n=2 per arm, two pairs)

| | pair 01 (default budget) | pair 02 (`max_tokens` 45,000) |
|---|---|---|
| compaction boundaries `g0` / `g1` | 0 / 0 | **9 / 9** |
| Anthropic requests compared | 27 indices | 26 indices |
| `tools` sha256 divergences | **0** | **0** |
| distinct `tools` sha per arm | 1 / 1 (`561cd6fcbba28d79`) | 1 / 1 (`561cd6fcbba28d79`) |
| system prompt bytes `g0` / `g1` | 46,677 / 46,677 (**Δ 0**) | 46,677 / 46,677 (**Δ 0**) |
| cache-read share `g0` / `g1` | 92.4 / 89.4 (−3.0 pts) | 79.7 / 74.8 (−4.9 pts) |
| re-warm distance at every boundary | n/a | **1 request, all 8** |
| `ID_ONLY` divergences | 0 | 0 |
| `g5b′` violations (B1–B4) | 0 | 0 |

### TABLE 3 — spend, to the cent

| arm | launches | valid | achieved validity | spend | $/launch |
|---|---:|---:|---:|---:|---:|
| `t0` S3 terra-medium | 10 | 10 | **1.000** | $9.990600 | $0.999060 |
| `t1` S3 terra-medium | 10 | 10 | **1.000** | $8.781900 | $0.878190 |
| `g0` Anthropic guardrail | 2 | 2 | **1.000** | $6.518800 | $3.259400 |
| `g1` Anthropic guardrail | 2 | 2 | **1.000** | $5.175600 | $2.587800 |
| **TOTAL** | **24** | **24** | **1.000** | **$30.466900** | — |

**Arithmetic, as the goal requires — launches × $/launch ÷ achieved validity:**

```
terra   20 launches x $0.938625/launch / 1.000 valid  =  $18.7725
anth     4 launches x $2.923600/launch / 1.000 valid  =  $11.6944
                                              TOTAL   =  $30.4669   of $170.00
RESIDUE $139.5331 -- and it is genuinely spendable (the smallest useful purchase, one more
matched terra pair, costs ~$1.88), it simply was not needed: every deliverable landed at its
own pre-registered n.
```

**Reconciling the spec's ~$47 and the goal's $170 against what was actually paid:**

| source | terra $/run | anth $/run | validity | predicted total | error vs actual |
|---|---:|---:|---:|---:|---:|
| `EVAL-SPEC.md` §3 (the "~$47") | $1.55 | $2.33 | 1.00 (implicit) | $46.40 incl. 15% headroom | **1.5× over** |
| the work item / this goal ($170) | $4.63 | $3.53 | 0.67 | $160.08 + slack | **5.6× over** |
| **measured here** | **$0.9386** | **$2.9236** | **1.000** | — | **$30.4669** |

The spec's per-run terra figure came from `00-what-we-know.md:44` (threeknob, **$1.55**); the goal's
came from a delegation-heavy configuration (`8rugb` measured **$5.28–$6.63/run** on foundation-as-root
S3). **This lane's runs sit below both, and §3 explains part of why the treatment arm is cheaper:
it never delegated.** The goal's authority was over-sized, which is the safe direction — recorded,
per the goal's authoring rule, as a finding rather than absorbed.

**Achieved validity is 100%, against the 67% the price rested on.** That figure is itself a finding:
the **fixed** S3 driver (md5 `dc307c50090b11d981eee44382668431`, recorded in all 24 run records)
reported `session_continuity_ok: true` on **24 of 24** runs. The pristine driver reported it **false
on 152/152 records and true on zero** — a constant carrying no information. On this lane's evidence
the low historical validity rate was substantially an **instrument** problem, not a run problem.

---

## 5. Three defects this lane found — two of them in its OWN gates

### 5.1 `E-A` (modal `cached_tokens`) was defective, **arm-asymmetrically** — `ADDENDUM-B` §B1

Pre-registered in `ADDENDUM-A` on the strength of `00-what-we-know.md`'s *"froze at 18,454 for 80
consecutive requests"*. Under `persist` mode the conversation is cached too, so the mode tracks
**transcript length** — and `t1`'s transcript grew to 262,186 `input` chars against `t0`'s 78,725,
so the estimator is inflated **more in the arm under test**. Its value stands, reported, unrepaired:
`t0` 18,725 · `t1` 12,411.5 (it happens to agree here; on the pilot it read **73,981** for `t1`).

### 5.2 `E-B` (12v's chars/4.627) measures the WIRE, not the BILLED PROMPT — `ADDENDUM-B` §B2

**A method invalidation, not just a wrong number.** The namespace entries ship every member's full
description **and** full `parameters` schema inline — the `t1` tools array is **38,516 chars**, of
which `delegation` alone is 14,466 and `files` 10,389 — because the server needs them to serve
`tool_search`. The server does **not** bill them: the same request is charged **12,410** pinned
tokens against the control's **18,725**.

> **Any local byte-count analysis of a namespaced tools block reads a 33.7% saving as a 2.4% LOSS.**
> `12v`'s chars/4.627 rule is sound for a flat block, where wire bytes and billed prompt are the same
> population. Under `tool_search` they are different populations. Recorded loudly so the next lane
> does not re-derive it the expensive way.

### 5.3 Two detectors that were INERT, both caught before their verdict was banked

- **The D2 surrogate detector read the wrong field.** The harness writes `tool_name` / `tool_input`;
  the first implementation looked only at `tool` / `arguments`, so it saw **0 bash commands** and
  returned `sub_rate = 0.0` in **every run of both arms** — a constant carrying no information,
  the exact shape of the defect `i0cm` found in the S3 driver. Fixed; D2 then returned real,
  differing rates (0.08 / 0.00).
- **G12's matcher was too wide.** `ADDENDUM-A` widened EVAL-SPEC's single phrase to
  `phrase OR "InvalidRequestError"`. The S3 scenario **seeds provider config-validation source that
  contains that token**, so the wide matcher scored **654 hits** — it was grading the scenario's own
  reference material. Narrowed to EVAL-SPEC's verbatim phrase; **0 real hits**.

### 5.4 And one in a shared harness — `configure_cell.py --max-tokens` silently no-ops

`find_bundle_md()` returns `bundles/anchors-amp-dev/bundle.md`, but `context.config.max_tokens: 300000`
lives in **`bundles/anchors/bundle.md`** (measured in all four containers). `patch_max_tokens()` then
exits non-zero **on stderr**, and every caller in this programme pipes only **stdout** (`| tail -2`,
`| tail -3`) — so the failure is invisible and the run proceeds at the default budget **with no
compaction boundary at all**. Any lane that believed it had lowered the compaction trigger this way
did not. Proposed correction in `DONE-NOTE.md` §6; this lane did not edit the shared harness.

---

## 6. Verdict — **DON'T-BUILD** as a default, which this item states is a **PASS**

```
BUILD / DON'T-BUILD / NOT-POSSIBLE      ->      DON'T-BUILD (as a default)
```

**What is proven, and it is a lot:**
- the head saving is **real, large and larger than predicted**: 6,313 tok, **33.7%**, n=10/10,
  corroborated to 2 tokens by an independent server-side figure;
- the Anthropic containment is **proven live**, 121 requests, 8 real compaction boundaries,
  0 divergences at 53 of 53 indices — T3 is not tripped;
- tool-pair atomicity holds (**G12 0 hits**), the loaded set stays inside T4 (**median 10**), and
  the pre-registered substitution tripwire moved **protectively**;
- quality on S3 is **non-inferior** at n=10.

**Why the default still does not flip:**
1. **A D2-class recurrence is present and it is more complete than the one that caused PR 83.**
   `6ei` lost 2 of 23 calls of one tool; here **three deferred tools go to zero reach** and the one
   always-visible tool absorbs the work. This item's own instruction is that a D2 recurrence is
   decisive *"regardless of what G9 and G10 say"*.
2. **`delegate` disappearing is an untested capability loss, not a measured-safe one.** S3 does not
   need delegation, so the only quality instrument in play is structurally blind to it — and
   delegation is the load-bearing confounder of this whole programme.
3. **G10's median clause is at the ceiling** and is recorded UNINFORMATIVE. The only informative
   quality clause, strict-pass, lands **exactly on** its threshold (8 ≥ 9 − 1). That is a pass, not
   a margin.
4. **G13 could not be measured at all** — no boundary in `t1`, and `context-simple` break 5 is
   unlanded. Compaction survival of the loaded set remains entirely unbought.

**This is a judgment call, and the numbers that support the other reading are all above.** The
pre-registered D2 rule **did not fire**. A reader who judges `edit_file → apply_patch` benign (the
quality data supports that) and who is willing to ship an opt-in flag with delegation untested can
reach **BUILD** from exactly these tables. I do not, because `cal`, `6ei` and PR 83 each failed in
the same direction — banking something that had not been measured — and the cheap measurement that
would settle it is named below.

**What this authorises:** keeping `tool_search.mode` on `main` as the **opt-in, default-off**
provider config it already is (`702b361`), with **G5a and G5b′ wired into CI** so containment stays
proven after merge rather than only at merge.

**What this does NOT authorise:** flipping the default; any performance claim in a PR body,
MANIFEST or docstring (`00-what-we-know.md:131`); or generalising past `gpt-5.6-terra` @ `medium`
on S3.

**The one measurement that would flip this, and it is cheap.** A single A/B on a scenario that
*requires* delegation (S1 exercises it; `00-what-we-know.md` §2c gives the delegation profile),
n=3/arm, with `delegate` reach as the pre-registered outcome. At this lane's observed price that is
**6 launches ≈ $5.63**. If `delegate` reach survives, finding (b) collapses and the remaining
objection is finding (a), which the quality data already argues is benign.

**NO DEFAULT IS SHIPPED IN THIS LANE**, and none would have been on a BUILD either.

---

## 7. What was NOT re-derived

Per the goal, none of `cal`'s measurements were re-bought: the granularity band `[2,002 , 3,006]`
and its prompt-driven mechanism, the reserved namespace names (`web` never re-introduced — the
shipped table uses `internet`), the +18-token cost of the T-5NS split, the 14.8% → 0.0% net-worse
population, and the G5b re-scope. All are cited, none recomputed. The shipped `DEFAULT_NAMESPACES`
in `702b361` **is** T-5NS — `{delegation, files, internet, knowledge, shell}` with
`always_loaded = (bash, todo)` — so no namespace table was overridden by this lane. One difference
from `cal`'s paper table is recorded rather than absorbed: the shipped `files` namespace has **six**
members (it also lists `apply_patch`, for the function-shaped fallback) where `cal`'s listed five.
