# DONE-NOTE — lane `webu-deferred-tools-phase2-rerun`

**Work item:** `model_performance-webu` (project `model_performance`)
**Repo:** `microsoft/amplifier-bundle-evaluation`, branch `lane/webu-deferred-tools-phase2-rerun`, from `main` @ `7c36467`
**Outcome branch:** **A — RESOLVED.** Every run-buying deliverable ran at its full pre-registered n.
Nothing was recorded NOT-POSSIBLE for cap reasons; **the cap never bound.** One gate (`G13`) is
UNINFORMATIVE with its unlanded dependency named — that was pre-registered as its only two
possible outcomes before launch, and is not a cap outcome.
**Spend:** **$30.4669 of the $170 owner-funded authority** (17.9%). Residue **$139.5331**.
**Verdict:** **DON'T-BUILD as a default** — which this item states is a **PASS**.

---

## 1. Headline

**The measurement PR 83 reverted PR 82 for has now been bought, in full, at n.**

- **24 launches, 24 valid, achieved validity 100%** (the goal's price rested on 67%).
- **G9 PASS and bigger than predicted:** pinned head **18,725 → 12,411 tok**, a **6,313-tok / 33.7%**
  saving, corroborated to **2 tokens** by an independent server-side figure. `cal`'s $0 census
  predicted 4,540 / 24.6% — it **under**-predicted by 39%.
- **All four blocking Anthropic gates PASS on a LIVE run**, across 121 requests and **8 real
  compaction boundaries**: `tools` sha `561cd6fcbba28d79` identical at **53 of 53** indices,
  system prompt **+0 B**, re-warm **1 request at every boundary**, `ID_ONLY` **0**.
- **`6ei`'s `E5_quality`, recorded NOT MEASURED and one of the two reasons for the revert, is now
  MEASURED: PASS.**
- **And the revert's other reason recurs, larger, on a channel my own D2 rule did not watch.**
  The pre-registered D2 rule **did not fire** (it moved protectively, −8 pp). But 6ei's own D2
  *form* applied to every tool shows **`write_file` 3/10→0/10, `edit_file` 4/10→0/10,
  `delegate` 4/10→0/10**, absorbed by the one always-visible tool, `apply_patch` (8/10→**10/10**).
  6ei lost 2 of 23 calls of one tool; this is three tools at zero.

**That is why the default does not flip, and the full argument — including the numbers that support
the opposite reading — is `FINDINGS.md` §6.**

---

## 2. Deliverables

| # | Deliverable (from the goal) | State | Evidence |
|---|---|---|---|
| 1 | EVAL-SPEC §3 arms as pre-registered: `t0`/`t1` S3 terra-medium **n=10 each** + mandatory `g0`/`g1` **n=2 each** | **DONE — full n, 24/24 valid** | `FINDINGS.md` §4 Table 3; `ANALYSIS.json` |
| 2 | The guardrail is a **LIVE RUN**, not a hash replay | **DONE** | 121 live Anthropic requests, 2 pairs, 8 boundaries (`FINDINGS.md` §1b, §4 Table 2) |
| 3 | `FINDINGS.md` records G9, G10, G11, G4′, G12, G13 and blocking G5a–G5d as PASS/FAIL/UNINFORMATIVE **with measured value, each rule quoted verbatim** | **DONE** | `FINDINGS.md` §1a–§1b |
| 4 | **G10 UNINFORMATIVE if both arms hit the ceiling** — do not bank a ceiling as no-harm | **DONE** | G10's **median clause is recorded UNINFORMATIVE** (both medians at the 100 ceiling); the verdict rests only on the informative strict-pass clause, which lands **exactly on** its threshold |
| 5 | **D2 and E5 pre-registered and committed BEFORE launch, SHA quoted** | **DONE** | `PREREG.md` **`c37ad942822e9c648bdc8b6cb10250950c512a96`**, committed before the first API call **and** before the first DTU launch |
| 6 | **DTU pin proven ON THE WIRE** (not by asserting the profile) | **DONE — 4 legs** | `FINDINGS.md` §2; `wire/pin-proof-P1-P2.txt`. `702b361…` recorded by the installer, 80 grep hits, `tool_search`+`defer_loading` on the wire, `namespace` surviving the round trip, **0** `Missing namespace` 400s |
| 7 | **The FIXED S3 driver** (`i0cm`, md5 `dc307c50090b11d981eee44382668431`) **with its hash in EVERY run record** | **DONE** | `runs/*/driver_md5.txt` and `runs/*/meta.json`, all 24 |
| 8 | **ACHIEVED VALIDITY reported per arm** | **DONE — 1.000 in all four arms**, against the 67% the price rested on. **That is itself a finding** (§5) | `FINDINGS.md` §4 Table 3 |
| 9 | **Spend arithmetic to the cent**; DTUs ≤8 live; destroy every one; ledger 0 open rows verified | **DONE** | §4 below |
| 10 | **Verdict: BUILD / DON'T-BUILD / NOT-POSSIBLE** (a DON'T-BUILD is a PASS) | **DONE — DON'T-BUILD** | `FINDINGS.md` §6 |
| 11 | **NO DEFAULT SHIPPED IN THIS LANE** | **DONE** | Nothing in this branch touches a default. The verdict is DON'T-BUILD, so the "$0 CODE item on BUILD" clause does not apply; the cheap follow-up that would flip it is specified instead (`FINDINGS.md` §6) |
| 12 | **Write to your OWN artifact root only**; proposed diffs for `00-what-we-know.md` / `probes/INDEX.md` in the DONE-NOTE | **DONE** | §6 below; `proposed-00-what-we-know.diff` in this directory. **Neither file was edited.** |

---

## 3. Gate summary (regenerable at $0: `python3 analyze.py --cap <capture root>`)

| gate | verdict | measured value |
|---|---|---|
| **G9** head reduction | **PASS** | 18,725 → **12,411.5** tok; **−6,313.5 = −33.7%**; corroborated to **2 tok** |
| **G10** quality non-inferiority | **PASS** (strict-pass clause) · **median clause UNINFORMATIVE — ceiling** | medians 100/100; strict-pass **9/10 → 8/10**, exactly at threshold |
| **E5** quality (6ei's unmeasured gate) | **PASS** | max single-constraint drop **1 of 10**; FAIL threshold is ≥2 |
| **G11** cost / cadence | **ADVISORY — cost PASS, cadence UNDEFINED** | mean $0.9991 → $0.8782 (−12.1%); boundaries 0.0 in both arms |
| **G4′** real loaded set (T4) | **PASS** | median **10** of 14 (`t0` 13) |
| **G12** tool-pair atomicity | **PASS** | **0** hits; 654 bare-token false positives excluded |
| **G13** compaction survival | **UNINFORMATIVE + dependency named** | 0 boundaries in `t1`; `context-simple` break 5 unlanded. **Never PASS** |
| **G5a** Anthropic `tools` byte-identity, LIVE | **PASS** | **53/53** indices, **0** divergences, sha `561cd6fcbba28d79` both arms |
| **G5b′** breakpoint invariant (cal's re-scope) | **PASS** | **121** requests, **0** violations |
| **G5c** system-prompt stability | **PASS** | 46,677 B both arms, **Δ +0 B**, 1 sha per run |
| **G5d** Anthropic live behaviour | **PASS** | share −3.0 / −4.9 pts; re-warm **1** at all 8 boundaries; `ID_ONLY` **0** |
| **D2** (as pre-registered) | **DID NOT FIRE** — moved protectively | median shell-surrogate rate 0.08 → 0.00, **−8.0 pp** |
| **D2-class** (6ei's own form, every tool) | **PRESENT** | `write_file` 3/10→**0/10**, `edit_file` 4/10→**0/10**, `delegate` 4/10→**0/10** |

---

## 4. Spend and infrastructure

### 4a. Spend, to the cent

| arm | launches | valid | validity | spend | $/launch |
|---|---:|---:|---:|---:|---:|
| `t0` | 10 | 10 | 1.000 | $9.990600 | $0.999060 |
| `t1` | 10 | 10 | 1.000 | $8.781900 | $0.878190 |
| `g0` | 2 | 2 | 1.000 | $6.518800 | $3.259400 |
| `g1` | 2 | 2 | 1.000 | $5.175600 | $2.587800 |
| **TOTAL** | **24** | **24** | **1.000** | **$30.466900** | — |

```
terra   20 x $0.938625 / 1.000 valid  =  $18.7725
anth     4 x $2.923600 / 1.000 valid  =  $11.6944
                              TOTAL   =  $30.4669  of $170.00 authority
RESIDUE $139.5331 -- spendable (smallest useful purchase, one matched terra pair, ~$1.88),
simply not needed: every deliverable landed at its own pre-registered n.
```

**Programme accounting, both reported and not netted:** Phase 1 (`bub`) + `cal` spent **$1.11479**
of the original **$60** programme cap. **This lane's $30.4669 is against the separate, owner-funded
$170 authority.**

**Reconciling the spec's ~$47** (goal deliverable): `EVAL-SPEC.md` §3 priced Phase 2 at **$46.40**
(20 terra × $1.55 + 4 anth × $2.33 + 15% headroom). Actual **$30.4669** — the spec was **1.5× over**.
The goal's repriced **$160.08 + slack = $170** was **5.6× over**. Both erred in the safe direction.
Per-run terra: spec $1.55, goal $4.63, **measured $0.9386**.

### 4b. Infrastructure — 8 DTUs, all mine, all destroyed

Registered at creation and claimed to this lane; torn down with `lane_teardown.sh` using the **FULL**
lane name. **`infra_ledger.sh sweep` was never run** (it is the manager's batch-close verb and would
destroy other live lanes' infrastructure).

```
webu-t0  webu-t0b  webu-t0c   (terra control, 3 runs each)
webu-t1  webu-t1b  webu-t1c   (terra treatment, 3 runs each)
webu-g0  webu-g1              (Anthropic guardrail, 2 runs each)
```

**Peak concurrency 8**, which is the cap this goal sets.

**Teardown, verified:**

```
TEARDOWN: lane=webu-deferred-tools-phase2-rerun verified-gone=8 rows-flipped=8
  already-absent=0 failed=0 live-skipped=0 unknown-skipped=0 unverifiable=0 protected-untouched=0

ledger rows matching "webu"      : (none -- all 8 flipped)
open ledger rows, whole batch    : 0
live DTUs after teardown         : steward-desk-test, wayfinder-scout-eval   (BOTH other lanes' -- untouched)
webu-* containers still live     : NONE
```

Full transcript: `<capture root>/teardown.log`. A dry-run was executed first and inspected.

---

## 5. Findings that belong to the programme, not just to this lane

1. **`12v`'s chars/4.627 method is INVALID on a namespaced tools block.** The wire payload carries
   every deferred member's full schema (38,516 chars; `delegation` alone is 14,466) while the server
   bills 12,410. **A local byte count reads a 33.7% saving as a 2.4% loss.** (`FINDINGS.md` §5.2)
2. **The head saving has a cold-start price nobody had measured.** `t1` adds **+3,760 tok** of
   non-cacheable billed prompt at request 0, so the cold request nets only −2,557 tok while every
   request after it nets −6,313. Both numbers must travel together.
3. **The treatment arm never delegated: 6 calls / 4 runs → 0 calls / 0 runs** (Fisher **p ≈ 0.087**,
   suggestive not significant). It also makes `t1`'s lower cost unsafe to bank as a treatment effect —
   `t0`'s delegating runs are its expensive ones.
4. **Achieved validity was 100%, not 67%** — with the **fixed** i0cm driver, `session_continuity_ok`
   was true on **24/24**. The pristine driver reported it false on **152/152 and true on zero**. On
   this evidence the historical low validity rate was substantially an **instrument** problem.
5. **`configure_cell.py --max-tokens` silently no-ops** on the current foundation layout, and every
   caller in the programme hides the failure by piping only stdout. (`FINDINGS.md` §5.4, §6 below.)

---

## 6. Proposed corrections — NOT APPLIED BY THIS LANE

Per the goal, this lane edited **neither** `ai-notes/00-what-we-know.md` **nor** `probes/INDEX.md`.

- **`proposed-00-what-we-know.diff`** (this directory) — adds a `webu` entry to §2 covering: the
  measured 33.7% head saving, the cold-start term, the chars/4.627 method invalidation, the
  D2-class tool-reach table, and the live Anthropic guardrail result. Apply from the evals repo root
  with `git apply`.
- **`probes/INDEX.md`** — no diff is proposed. This lane's artefacts live in the
  `amplifier-bundle-evaluation` repo under `docs/lanes/webu-deferred-tools-phase2-rerun/`, not under
  the evals repo's `probes/`, so there is no probe directory to index. If the manager wants a
  cross-reference, the one line to add is:
  `webu-deferred-tools-phase2-rerun -- Phase 2 deferred tool loading, full n, DON'T-BUILD (amplifier-bundle-evaluation@lane/webu-deferred-tools-phase2-rerun)`
- **`_harness/configure_cell.py`** — a one-line-class fix the manager should apply where the file
  actually lives (outside this lane's paths): `find_bundle_md()` must search
  `bundles/*/bundle.md` for the file that actually carries `max_tokens:` (it is
  `bundles/anchors/bundle.md`, not `bundles/anchors-amp-dev/bundle.md`), and callers must stop
  discarding stderr. `patch_budget.sh` in the capture root is a working reference implementation
  that proves its own application.

---

## 7. Goal defects and made choices, reported rather than absorbed

`cal` filed four goal defects and all four were correct; the goal asks for the same treatment here.

### 7a. Goal defects (2)

1. **The cap was over-sized by 5.6×, and it was knowable on the first read.** The goal's authority is
   built on `$4.63/terra launch` at `0.67 validity`. That price came from a delegation-heavy
   configuration (`8rugb`, foundation-as-root, $5.28–$6.63/run); `00-what-we-know.md:44`'s own
   figure for terra-medium S3 is **$1.55**, and the measured figure here is **$0.9386**. The goal's
   arithmetic *closes at its own quoted price* (`30 × 4.63 + 6 × 3.53 = 160.08 ≤ 170`), so it is
   internally consistent and it erred safe — but a lane reading it could reasonably have concluded
   the deliverable was marginal when it was in fact 5.6× affordable. **Recommendation:** when a goal
   quotes a per-run price, name the configuration it was measured on.
2. **`G13`'s dependency makes one deliverable unreachable from inside any single lane, and the goal
   already knows it.** The goal says *"If it has not landed, record G13 NOT-POSSIBLE with the
   dependency named"* — which is right — but `context-simple` break 5 has now been homeless across
   three lanes (`v5co` shipped it as a verified patch artifact, `cal` could not apply it, this lane
   may not either). **Recommendation:** land `v5co`'s patch as its own $0 item before any lane is
   asked for `G13` again. It applies clean at `a2a098b`, fail-before 1 failed/2 passed → 3 passed.

### 7b. Made choices, each recorded in the pre-registration before it mattered

1. **The treatment was applied to every `provider-openai` block, not only `terra`** (`PREREG.md`
   MADE CHOICE 1). The routing matrix sends sub-agent work to other OpenAI cells; treating only the
   root would have left most OpenAI requests untreated and measured D2 on a minority of calls. G9 is
   still read off the **root** session, so the choice cannot manufacture a head saving.
2. **The shipped default namespace table was used verbatim** (`PREREG.md` MADE CHOICE 2). It **is**
   T-5NS. One difference from `cal`'s paper table is recorded, not absorbed: the shipped `files`
   namespace has **six** members (it also lists `apply_patch`) where `cal`'s listed five.
3. **Guardrail pair 2 runs at a patched compaction budget** (`ADDENDUM-B` §B5), because
   `configure_cell.py --max-tokens` does not work. Both arms of the pair get the identical patch, and
   `analyze.py` compares **within a pair, never across** — so the arm remains the one variable.
4. **G9's verdict is read on `pinned cache_read`**, the quantity EVAL-SPEC's sentence names
   (`ADDENDUM-C`). Two rejected estimators are reported with their values and their defects.

### 7c. Three defects this lane found in its OWN instruments — all caught before a verdict was banked

| # | defect | how it would have lied | disclosed in |
|---|---|---|---|
| 1 | `E-A` = modal `cached_tokens` | tracks transcript length, **arm-asymmetrically** (read 73,981 for `t1` on the pilot) | `ADDENDUM-B` §B1 |
| 2 | `E-A′` = total billed prompt @ req 0 | includes a treatment-only non-cacheable term; would have scored G9 **FAIL** at −2,557 | `ADDENDUM-C` §C2 |
| 3 | the D2 surrogate detector read `tool`/`arguments`, not `tool_name`/`tool_input` | **inert** — returned `sub_rate = 0.0` in every run of both arms, an i0cm-shaped constant | `FINDINGS.md` §5.3 |

A fourth, in the opposite direction: **G12's matcher was too wide** and scored **654** hits off the
S3 scenario's own seeded reference source. Narrowed to EVAL-SPEC's verbatim phrase; **0** real hits.

---

## 8. Artefacts

```
docs/lanes/webu-deferred-tools-phase2-rerun/
  PREREG.md                     c37ad94  the gates, D2 and E5, the cap arithmetic  (before the first API call)
  PREREG-ADDENDUM-A.md          ce4add3  field-level arithmetic for every gate     (before any output was read)
  PREREG-ADDENDUM-B.md          d37487e  G9 estimator superseded in the open       (before 18 of 20 terra runs)
  PREREG-ADDENDUM-C.md          e8a7cdc  which quantity carries G9's verdict       (before 14 of 24 runs)
  FINDINGS.md                            every gate, verbatim rule, measured value, verdict
  DONE-NOTE.md                           this file
  analyze.py                             regenerates every table, spends nothing
  proposed-00-what-we-know.diff          for the manager to apply; NOT applied here

capture root (outside this repo, as the goal requires):
  /home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-webu-phase2/
    ANALYSIS.json          the full machine-readable record
    runs/{t0,t1,g0,g1}-NN/ driver_record, scorecard, measure, meta, driver_md5, all-sessions/
    profiles/              the four arm profiles (t0 vs t1 differ in 29 lines: 4 name/desc + 25 tool_search)
    scenario/s3/           the FIXED i0cm driver, md5 dc307c50090b11d981eee44382668431
    wire/pin-proof-P1-P2.txt
    run_cell.sh · seq_runs.sh · gen_profiles.py · patch_budget.sh · analyze.py
```
