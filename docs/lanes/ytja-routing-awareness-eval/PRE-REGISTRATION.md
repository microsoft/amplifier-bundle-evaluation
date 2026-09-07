# PRE-REGISTRATION — routing-awareness eval (`model_performance-ytja`)

**Committed BEFORE the first graded run.** Nothing below was written after seeing a graded
number. The two things that existed before this file — the arm containers and the wire census
in §2 — are *inputs* to the design, are $0.04 of haiku warm-up, and are named as such.

Lane: `ytja-routing-awareness-eval` · Item: `model_performance-ytja` · Authority: **$200**

---

## 1. THE QUESTION

Stage 1 is measured on **bytes and fidelity**. Fidelity proves a rule is still **PRESENT**.
It does not prove the rule is still **FOUND**. `webu` passed every pre-registered gate and still
returned DON'T-BUILD because three tools went to **zero executed calls** while every gate looked
fine. This eval asks the FOUND question directly: **does the model still reach for the right
capability?**

---

## 2. THE ARMS — pinned, and characterised ON THE WIRE before any graded run

| arm | repo | commit | container |
|---|---|---|---|
| **stock** | `microsoft/amplifier-foundation` | `ed64999d0be162cfe18a11f675fcc44538327f7c` (origin/main) | `ytja-stock` |
| **lean** | `microsoft/amplifier-foundation` | `7771ad22443fad4d8a881f3157285868a16bf7d1` (`lane/zc6t-lean-head-ship`) | `ytja-lean` |
| **stage-1** | — | **DOES NOT EXIST AT RUN TIME** — see §8 | not run |

Amplifier CLI pinned identically in both arms: `28588b93886dd4b134f131294ca98e944d71cbfd`
(`amplifier, version 2026.09.06-be25afd (core 1.6.1)`).

**Ref-pinning alone would have produced two byte-identical arms.** `bundles/anchors/bundle.md`
sources its own sub-parts with hardcoded `@main` URLs (line 54: `tool-delegate` ←
`amplifier-foundation@main`), and `anchors-amp-dev/bundle.md` includes `anchors` at `@main`.
Both arms therefore fetch foundation through a **Gitea mirror + `url_rewrites`**, so every
transitive `@main` resolves to the arm's tree. Both arms take the identical code path; only the
mirrored tree differs.

### 2.1 What the treatment actually is (measured, container wire, `llm:request.data.raw`)

| quantity | stock | lean | Δ |
|---|---:|---:|---:|
| `system` chars | 45,794 | 45,446 | **−348** |
| `tools` JSON chars | 38,542 | 38,276 | **−266** |
| **head total** | **84,336** | **83,722** | **−614 (−0.73%)** |
| `delegate` description | 11,800 | 11,548 | −252 |
| `delegate` **preamble** (bytes before `Available agents:`) | 1,192 | 940 | **−252 (−21.1%)** |
| agents in catalog | 12 | 12 | **0** |
| per-agent descriptions | — | — | **byte-identical** |
| other 13 tool descriptions | — | — | **byte-identical** |
| skills visible in system prompt | 51 | 51 | 0 |
| warm-up input tokens (haiku) | 22,578 | 22,425 | −153 |

**This is the load-bearing design fact.** The agent catalog is byte-identical across arms.
Every per-agent description, every skill name, and 13 of 14 tool descriptions are unchanged.
The treatment is confined to (a) the `delegate` **preamble** — −21.1%, which is where the stock
text's *"Why delegate: Every tool call YOU make consumes YOUR context window permanently …
Delegation = longer, more effective sessions"* motivation lived — (b) `anchors/context/system.md`
(1,358 → 1,142 B), (c) `anchors-amp-dev/context/amplifier-ecosystem.md`.

Therefore **any measured difference in reaching is attributable to the delegation framing, not
to catalog trimming.** That is a cleaner causal claim than the item anticipated, and it is
stated here before any graded run.

Independent corroboration of the arm split, verbatim from the containers:
`grep -c 'Why delegate' …/tool-delegate/__init__.py` → **stock 1 / lean 0**;
`wc -c …/anchors/context/system.md` → **stock 1358 / lean 1142**.

**Incidental defect found on the stock wire while characterising the arms:** stock's `delegate`
description emits the `- agent="self": Spawn yourself as a sub-agent` line **twice** (once
hardcoded in `base_description`, once from the feature registry). zc6t fixes it. Confirms zc6t's
own code comment against a value read off the wire.

---

## 3. THE SCENARIO SET

`scenarios/prompts.json` (committed with this file) is authoritative: **10 hidden-capability
prompts** (H1–H10) and **5 over-reach controls** (C1–C5), each with its expected target and its
**equivalence set**, fixed here.

- H1–H5 are the item's five given prompts. All five capabilities were **verified present in the
  arm catalog** before registration (`digital-twin-universe:dtu-profile-builder`,
  `context-intelligence:session-navigator`, `app-cli:cli-expert`, the `gitea` skill, and
  cli-expert's `/provider` authority).
- H6–H10 are lane-designed, each keyed to a catalog entry's own `USE WHEN` line, and each
  phrased so the capability is **never named**.
- C1–C5 are single-file, fully-specified tasks where a specialist is over-reach. They are
  deliberately *not* trivial arithmetic: each has visible pull toward `builder`/`explorer`, so
  the control can move in **both** directions. A design that can only detect one direction is
  not a measurement.

Controls run against a seeded `/root/work` (`src/app.py`, `README.md`, `pyproject.toml`) pushed
identically into both containers; the seed is committed under `scenarios/work-seed/`.

---

## 4. GRADING — trajectory-based, from EXECUTED RESULT entries only

Graded from **`events.jsonl` `tool:post`** entries (the executed-result entry), cross-checked
against **`transcript.jsonl` `role:"tool"`** entries; per-cell agreement between the two is
reported as an instrument check (2gxp's `tool:pre` agreed on 42/42 cells).

**Thinking-text mentions are never counted.** The manager's first recompute of `webu` was fooled
by exactly that: `write_file` looked like 9/10 runs, but those were one-per-run occurrences
inside `"type":"thinking"` text while the executed-result entries were absent entirely.

- **HIDDEN PASS** — the **first capability-reach within the first N=4 tool calls**
  (`delegate` target / `load_skill` name / `mode` name) equals the pre-registered expected
  target **or a member of that prompt's equivalence set**.
- **HIDDEN FAIL** — no capability-reach in the first N=4, or the first reach lands outside the
  equivalence set.
- **CONTROL PASS** — **zero** `delegate` and **zero** `load_skill` executed calls in the run.

---

## 5. THE DECISION RULE — registered verbatim, AND priced against its own power

### 5.1 The rule (verbatim from the goal)

> **Stage 1 is CLEAR if hidden-reach ≥ stock − 5 pp AND over-reach ≤ stock + 5 pp (both on the LB).**
> Otherwise **name which prompts regressed.**

### 5.2 POOLED vs PER-PROVIDER — fixed here: **PER-PROVIDER IS DECISIVE**

`njpd`'s COND2 **failed per-provider at 0.4737** and would have **passed pooled at 1.1131**;
pooling let a terra gain mask a **53% collapse** in opus delegation. Pooled figures are reported
for transparency and are **never decisive**. A CLEAR requires the rule to hold on
**claude-opus-5 AND gpt-5.6-terra independently**.

### 5.3 THE RULE IS UNSATISFIABLE AT ITS OWN REGISTERED n — computed at $0, BEFORE spending

Two-sided 95% Newcombe score interval on (lean − stock), **best case = perfect agreement**:

| observations / arm | hidden LB (both n/n) | control UB (both 0/n) |
|---:|---:|---:|
| 25 | −13.32 pp | +13.32 pp |
| **50** | **−7.13 pp** | +7.13 pp |
| 73 | **−5.00 pp** | **+5.00 pp** |
| 100 | −3.70 pp | +3.70 pp |

The item's registered design is **10 prompts × n=5 = 50** hidden observations and
**5 prompts × n=5 = 25** control observations per arm per provider. So, **even if the lean arm
reproduces stock perfectly on every single run**:

- hidden clause best-case LB = **−7.13 pp** → **FAILS** the −5 pp bar
- control clause best-case UB = **+13.32 pp** → **FAILS** the +5 pp bar

**Both clauses are vacuous-in-the-failing-direction at the registered n: no achievable data can
satisfy them.** This is the fourth instance of the family the program has already named three
times — S2a's vacuous Gate 3, `1ru`, and `8rugb`'s unsatisfiable success condition. Verified
against a value already known: my independent computation reproduces `8rugb`'s published
`n=73 → −5.00 pp` exactly.

**What the rule would cost.** 73 obs/arm/provider ⇒ hidden n=8/prompt (80 obs) + control
n=15/prompt (75 obs) = **155 launches per arm per provider**.

| variant | launches | terra @ $0.9386 | opus @ $2.9236 | total |
|---|---:|---:|---:|---:|
| 2 arms × 2 providers (per-provider, decisive) | 620 | $290.97 | $906.32 | **$1,197.29** |
| 3 arms × 2 providers | 930 | $436.45 | $1,359.47 | **$1,795.93** |
| 2 arms, **pooled** (njpd says do not) | 320 | $150.18 | $467.78 | **$617.96** |

Reference prices are the item's own (`webu`/`skw3b`, validity 1.000). **$1,197.29 against a $200
authority is 5.99× short.** Even the pooled variant the program forbids is 3.09× short.

**Registered consequence:** the item's decision rule is recorded **NOT-POSSIBLE (cap-bound)** and
this lane does **not** report a CLEAR/NOT-CLEAR verdict against it. That is OUTCOME branch B.

### 5.4 THE SECONDARY RULE — registered here, satisfiable, and what the money buys

`webu`'s failure mode was **collapse to zero**, and collapse *is* detectable at small n. A
one-sided Fisher exact test, per prompt, per provider:

| n/prompt/arm | stock n/n → lean 0/n | stock n/n → lean 50% |
|---:|---:|---:|
| 5 | p = 0.0040 | p = 0.0833 |
| 6 | p = 0.0011 | p = 0.0909 |
| 8 | p = 0.00008 | p = 0.0385 |

**SECONDARY RULE (decisive for this lane's verdict):**

1. **COLLAPSE** — a prompt is flagged REGRESSED if lean's reach rate is lower than stock's at
   one-sided Fisher **p < 0.05**, per provider. Holm–Bonferroni across the 10 hidden prompts is
   reported alongside the raw p, and both are shown; the raw p is the flag.
2. **OVER-REACH** — same test in the other direction on C1–C5: a control is flagged if lean's
   over-reach rate is *higher* than stock's at one-sided p < 0.05.
3. **DEGENERACY** — a cell whose stock arm is all-zero or all-one *and* whose lean arm matches it
   carries no information about direction; it is reported **UNEVALUABLE**, never as a verdict.
   `otr`'s pre-registered gate came back UNEVALUABLE on counts `[0,0,1,0,0]`; that is the correct
   outcome, not a failure.
4. **POINT ESTIMATES** — hidden-reach and over-reach rates are reported per provider and pooled,
   with n and 95% Newcombe intervals on the difference, **with the interval width stated**. No
   equivalence claim is made from them.

**A CLEAR is not available from this lane at any n it can buy. A REGRESSION is.** That asymmetry
is registered here, before the numbers exist.

---

## 6. INTEGRITY GATES — checked before and during the spend

- **G-ARM (checked, PASSED, §2.1).** The two arms must differ on the captured wire in the
  expected direction and locations. If they had been byte-identical the comparison would be VOID
  and nothing would be spent. `Why delegate` 1/0; system.md 1358/1142; head −614 chars.
- **G-PRICE.** The observed per-launch price is measured on a small probe and **stated before the
  bulk spend**. The bulk n is then set from the observed price, not from the reference price.
- **G-VALIDITY.** A run is VALID iff its root session exists, `prompt:complete` is present, and at
  least one `tool:post` OR a final assistant message exists. **No `>=5-boundary` gate is
  inherited**: `g7h3` measured that S7-17's validity gate is calibrated for terra and rejects
  ~80% of opus-5 runs in BOTH arms, and SPEC.md 9.1 freezes profiles — this eval's single-prompt
  scenario gets its own gate rather than inheriting S7-17 unexamined.
- **G-INSTRUMENT.** `events.jsonl` `tool:post` and `transcript.jsonl` `role:"tool"` must agree on
  the per-run reach classification. Disagreements are reported per cell, not smoothed.

---

## 7. SPEND PLAN

Authority **$200**, stated as arithmetic (authoring rule): `launches × arms × per-run observed
price / validity rate = spend`. The per-run price is **measured on this eval's own single-prompt
profile**, not inherited from the multi-turn S5/S7 references, because a price quoted for a
different run shape may not be reused.

- Probe: 1 launch × 2 providers × 2 arms = **4 launches**, graded and counted toward n if valid.
- Bulk n is then the largest integer n such that
  `15 prompts × n × 2 arms × (price_terra + price_opus) / validity ≤ $200 − probe_spend − 10% reserve`.
- If the honest n is below the item's registered n=5, the shrink is **named in the DONE-NOTE with
  its arithmetic**, never applied silently.

Every API and DTU spend is recorded in `DONE-NOTE.md` in this lane's artifact root.

---

## 8. ARM 3 (stage-1) — NOT RUN, recorded as a re-run item WITH ITS PRICE

Registered per the item's instruction ("if stage-1 has not landed, run arms 1–2 now and record
arm 3 as a re-run item WITH ITS PRICE — do not stall, and do not silently substitute").

At registration time: **`mse0` and `6f80` have no branch at all** (queued behind zc6t landing);
`kp79` and `kv98` are a *different* workstream — per-bundle agent/skill catalog diets in bundle
repos (browser-tester, dot-graph, context-intelligence, work-tracker, …), only partially pushed,
and **not in this eval container's mount set**. There is no stage-1 tree to pin.

**Price of the arm-3 re-run, at this lane's own observed price, is stated in the DONE-NOTE once
that price is measured.** Nothing is substituted for arm 3.

---

## 9. WHAT THIS LANE WILL AND WILL NOT CONCLUDE

- It **will** say, per prompt and per provider, whether reaching collapsed.
- It **will** report reach and over-reach rates with n and interval width.
- It **will not** issue the item's CLEAR/NOT-CLEAR verdict: that rule is unsatisfiable at any n
  this authority can buy, and saying otherwise would be the exact error the program has already
  paid for three times.
- **No default ships from this lane.** A finding that the lean head regressed routing and a
  finding that it did not are worth the same here.

---

## AMENDMENT A1 — 2026-09-07, after the PILOT probe, before any graded run

**Disclosed, not silent.** The 4-launch pilot (stock/terra, $0.10) exposed an instrument defect,
not a result: a hidden prompt with **no referent** ends a single-shot run with a **clarifying
question and ZERO tool calls**. `H1` as originally written produced 1 request, 0 tool calls, and a
thinking block reading *"I need to confirm the specific app, feature, URL, or path they're
referring to"* — which is **correct model behaviour** and a **degenerate, uninformative cell in
both arms**. That is `otr`'s failure mode arriving before the spend instead of after it.

**What changed:** six hidden prompts (H1, H6, H7, H8, H9, H10) gain a concrete referent
(`/root/work`). **Nothing else.** No `expected_target` changed, no `equivalence_set` changed, and
the target capability is still **never named** in any prompt. The change is
**outcome-independent**: it was made from a single stock-arm pilot, with no lean-arm data in
existence, and it cannot favour either arm.

**The 4 pilot launches are DISCARDED and counted toward n for nothing.** Their $0.10 is charged to
the spend ledger anyway.

Original prompt text is preserved per-prompt as `prompt_v1` in `scenarios/prompts.json`.

---

## G-PRICE — OBSERVED per-launch price, stated BEFORE the bulk spend

Measured on **this eval's own single-prompt profile**, stock arm, 6 launches (H1/H3/C2 ×
terra/opus), validity **6/6 = 1.000**, cost summed from `llm:response.data.usage.cost_usd` over
each run's whole session tree (root + delegated sub-sessions):

| | hidden mean | control mean |
|---|---:|---:|
| gpt-5.6-terra | **$0.3145** | **$0.0547** |
| claude-opus-5 | **$0.4838** | **$0.1431** |

Per-launch figures observed: terra H1 $0.4775 · H3 $0.1514 · C2 $0.0547; opus H1 $0.5786 ·
H3 $0.3889 · C2 $0.1431. The probe mix (2 hidden : 1 control) is the design's own ratio
(10:5), so the blend is not a favourable selection.

**These are 3.0×–5.4× BELOW the item's reference prices** (terra $0.9386, opus $2.9236), because
those were quoted for multi-turn S5/S7 scenarios and this eval's launch is one short prompt. Per
the authoring rule, a price quoted for a different run shape is not reused — so this lane's own
observed price is what the arithmetic below uses.

**ARITHMETIC (stated before the spend):**

```
per rep = 2 arms x [ terra(10 x 0.3145 + 5 x 0.0547) + opus(10 x 0.4838 + 5 x 0.1431) ]
        = 2 x [ 3.4180 + 5.5530 ]
        = $17.94   (60 launches)

n=3 -> $53.83   n=5 -> $89.71   n=8 -> $143.54     (+ $1.89 already spent)
```

**REGISTERED n AND STOPPING RULE — budget-only, fixed here.** Reps are added **uniformly across
all 60 cells**, in rep order, targeting **n=8** (the per-prompt n the primary rule's hidden clause
would need). The run stops when `cumulative_spend + projected_next_rep_cost > $185`
($200 authority less a $15 reserve), **or** at n=8, whichever comes first.

**n is chosen by budget, never by results.** No interim result may add, drop, or extend a cell.
If the sweep stops below n=8 the achieved n is reported with its arithmetic.
