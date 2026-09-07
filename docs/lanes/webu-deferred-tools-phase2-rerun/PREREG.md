# `webu` — Phase 2 pre-registration (written BEFORE any API call of this lane)

**Item:** `model_performance-webu` · **Date:** 2026-09-06 · **Lane:** `webu-deferred-tools-phase2-rerun`
**Repo/branch:** `microsoft/amplifier-bundle-evaluation` @ `lane/webu-deferred-tools-phase2-rerun`

**Parent pre-registrations, neither replaced by this file:**
- `ai-notes/w3-deferred-tool-loading/EVAL-SPEC.md` §3 (the arms and gates G9–G13, G5a–G5d)
- `probes/cal-deferred-tools-phase2/PREREG.md` (the $0 census gates and the W1/W2/W3 wire gates)

**Nothing below was computed before this file was committed.** The commit SHA of this file is
quoted verbatim in `FINDINGS.md` and in `DONE.json`. It is committed **before the first API call
and before the first DTU launch of this lane** — a DTU launch runs `amplifier run "Say exactly:
warmup-ok"` during provisioning, which is an API call, so provisioning is inside the fence too.

Rule being honoured: `00-what-we-know.md:278` (rule 5) — *a gate you write after seeing the result
is not a gate*.

---

## 0. What this lane is buying, in one sentence

**The measurement PR 83 reverted PR 82 for.** `6ei` shipped this machinery (`39aae65`, PR 82);
PR 83 (`7a8da74`) reverted it three hours later under *"main carries wins only"* because `6ei`'s
own pre-registered `E5_quality` gate was **NOT MEASURED** and tripwire **D2 fired 2/23** in the
deferred arm vs **0/13** in control. `v5co` restored the code as `702b361`. **Restoring the code
did not retire that verdict.** This lane buys `E5` and re-tests `D2` on a real agent loop.

**No default is shipped in this lane, whatever the verdict.** The default stays `off`.

---

## 1. THE TWO GATES `6ei` LEFT OPEN — fixed here, before launch

These are the two the goal names explicitly. Both are computed by `analyze.py` from the captured
`events.jsonl` trees; neither requires a human judgment call.

### 1a. **D2 — deferred-tool substitution** (tripwire; a firing is a DON'T-BUILD)

`6ei`'s recorded firing, verbatim from its `DONE.json`:

> `D2_tool_reached_in_static_but_not_deferred`: **FIRES** — read_file reached **21/23** in the
> deferred arm vs **13/13** static; both misses called always-loaded `bash` instead of searching.
> **Substitution, not absence.** n=23 is too thin to pin the rate (~8.7% point estimate).

`6ei` measured that on a 3-turn scripted script where the target tool was named by the prompt.
S3 does not name tools, so D2 is restated here as a **rate over the whole run tree**, fixed now:

```
POPULATION   every tool:pre event in the ROOT session and in every sub-session of the run tree
             (same tree resolution dw_measure.py uses: parent_id chain to root).

FILE-DOMAIN
TOOL CALL    a call to one of: read_file, write_file, edit_file, glob, grep, apply_patch
             (exactly the deferrable `files` namespace members of the SHIPPED table).

SURROGATE    a `bash` call whose command, after stripping leading `cd ... && ` segments,
CALL         matches  ^(cat|head|tail|less|sed|grep|rg|ls|find|awk|cut|wc|touch|mkdir|cp|mv)\b
             OR contains a shell redirect ( >  or  >> ) whose target path ends in a file
             extension.  i.e. the shell doing a job a deferred `files` tool exists for.

sub_rate(run) = surrogate_calls / (surrogate_calls + file_domain_tool_calls)
```

```
D2 FIRES  iff   median(sub_rate over VALID t1 runs) - median(sub_rate over VALID t0 runs) >= 0.05
          or    any t1 run contains a tool_search failure (tool_search_call with no usable
                tool_search_output, or an HTTP 4xx naming tool_search) followed inside the SAME
                turn by a surrogate call.

D2 UNINFORMATIVE iff  (surrogate_calls + file_domain_tool_calls) == 0 in >= half the runs of
                      EITHER arm — there is then no substitution opportunity to observe.
```

**Threshold justification, fixed now so it cannot be tuned later.** `6ei` observed 2/23 = **8.7 pp**
of substitution in the deferred arm against 0/13 = 0 pp in control. **0.05 (5 pp) sits BELOW that
observed effect**, so this gate can fire on a recurrence of the exact size already seen. A
threshold above 8.7 pp would have been a gate that cannot fail on the runs that motivated it —
the Gate-3 vacuity failure (`00-what-we-know.md:26`).

**Consequence, fixed now:** **a D2 firing is a DON'T-BUILD regardless of what G9 and G10 show.**

### 1b. **E5_quality — the gate `6ei` recorded as NOT MEASURED**

`6ei`'s `DONE.json`: `E5_quality`: *"NOT MEASURED — pre-registered as out of cap"*. That omission
is one of the two reasons PR 83 reverted PR 82. E5 is discharged here by the S3 rubric, and is
**deliberately not a synonym for G10**:

```
E5-total       PASS iff median(score t1) >= median(score t0) - 5
               AND strict_pass_count(t1) >= strict_pass_count(t0) - 1
               (identical thresholds to G10 — same measurement, so it cannot disagree with G10)

E5-constraint  PASS iff for EVERY pre-registered S3 constraint c in
               {C1 stdlib-only, C2 exit codes, C3 <120 lines, turn-2 retention,
                turn-3 revision, turn-5 extension} :
                    pass_count_c(t1) >= pass_count_c(t0) - 2      (of n per arm)
               FAIL if any single constraint drops by >= 2.

E5 = PASS only if BOTH clauses PASS.  E5 FAILS if E5-constraint fails, EVEN IF E5-total passes.
```

**Why the second clause exists, fixed now:** the S3 total can sit at ceiling while one specific
capability is destroyed — exactly the ceiling trap `00-what-we-know.md:55` records. E5-total may
come back UNINFORMATIVE (both arms at ceiling); **the E5-constraint clause is still evaluated in
that case** and is the part of E5 that carries information at ceiling.

**E5 UNINFORMATIVE-total rule:** if `median(t0) == median(t1) == the S3 maximum` **and**
`strict_pass(t0) == strict_pass(t1) == n`, E5-total is recorded **UNINFORMATIVE**, never PASS —
the same self-correction G10 carries.

---

## 2. The EVAL-SPEC §3 gates, quoted verbatim, thresholds unchanged

Restated here only so every verdict in `FINDINGS.md` has its rule beside it. **No threshold in
this table is altered by this lane.** Source: `ai-notes/w3-deferred-tool-loading/EVAL-SPEC.md` §3.

| id | gate (verbatim) | PASS threshold | blocking |
|---|---|---|---|
| **G9** | *"Head reduction, in a real run. `t1` median pinned `cache_read` **≤** `t0` median − 3,000 tok"* | ≥3,000 tok off the head | **yes** |
| **G10** | *"Quality non-inferiority. `t1` S3 median **≥** `t0` S3 median − 5 points, and `t1` strict-pass count ≥ `t0` − 1 of 10"* | as stated | **yes** |
| **G11** | *"Cost. `t1` mean $/run **≤** `t0` mean $/run, with boundary counts within ±15% between arms"* | as stated | no (advisory) |
| **G4′** | *"Real loaded set (tripwire T4). Median distinct tools actually loaded per run **≤10 of 14**"* | ≤10 | **yes** |
| **G12** | *"Tool-pair atomicity. `InvalidRequestError: No tool call found for function call output` count == **0** across all 10 `t1` runs"* | 0 | **yes** |
| **G13** | *"Compaction survival. After every compaction boundary in `t1`, every previously-loaded tool is still callable"* | 0 lost tools, 0 position changes | **yes** |
| **G5a** | *"Anthropic tools byte-identity. `sha256` of `params["tools"]` equal between `g0` and `g1` at **every** request index"* | N of N identical, 0 divergences, no tolerance band | **yes — merge blocker (T3)** |
| **G5b′** | re-scoped by `cal` §1c to an **absolute per-arm invariant** (B1 exactly one marker · B2 breakpoint used · B3 on the last tool that can carry one · B4 ≤4 markers), because old-G5b is a pure function of the array G5a hashes and has **zero marginal coverage** | B1–B4 hold in EVERY arm at EVERY request index | **yes** |
| **G5c** | *"Anthropic system-prompt stability. Distinct `instructions` sha256 per run == 1; byte delta vs control == **+0 B**"* | exact | **yes** |
| **G5d** | *"Anthropic live behaviour. `cache_read` share within **±10 pts** of `g0`; re-warm **≤1 request** at every boundary; `ID_ONLY` divergences == **0**"* | as stated | **yes** |

**G10 UNINFORMATIVE rule, quoted and binding:** *"vacuous if both arms hit 100/100 — then report
UNINFORMATIVE, exactly as `00-what-we-know.md:55` requires, and do not bank it as evidence of no
harm."* **A ceiling is never banked as no-harm.**

**G5a–G5d must be a LIVE RUN.** `cal`: *"a gate that cannot fail is worse than an unbought gate."*
A static hash comparison does **not** discharge them and will not be reported as discharging them.

---

## 3. G13's dependency, declared before launch

`G13` needs `amplifier-module-context-simple` **break 5** (loaded-tool-state protection across a
compaction boundary). `v5co` shipped it as a **verified patch artifact only** — it has landed in
no repo. This lane's worktree is `amplifier-bundle-evaluation`; it may not write `context-simple`.

**Fixed now, both branches:**
1. If **zero compaction boundaries** occur in the `t1` arm, G13 is **UNINFORMATIVE — no boundary
   crossed** (a fact about S3's length, reported as such), *and* the dependency is still named.
2. If boundaries do occur, G13 is **NOT-POSSIBLE — dependency `context-simple` break 5 unlanded**,
   named exactly as the goal's KNOWN section instructs, and the observed behaviour is reported as
   an *observation*, never as a G13 verdict.

Under neither branch is G13 recorded PASS.

---

## 4. The arms, and the ONE variable

| arm | n | provider cell | `tool_search` |
|---|---|---|---|
| `t0` control | 10 | `terra` = `gpt-5.6-terra` @ `medium`, priority 0 | absent (default `off`) |
| `t1` treatment | 10 | identical | `mode: namespaced`, `always_loaded: [bash, todo]` |
| `g0` anth control | 2 | `sonnet` = `claude-sonnet-5` @ `high`, priority 0 | absent |
| `g1` anth guardrail | 2 | identical | `mode: namespaced` set on the **OpenAI** provider blocks; the Anthropic provider never reads it |

**Held fixed across arms** (every one a known confounder in this programme): the DTU profile bytes
apart from the `tool_search` block, `--max-tokens` / compaction cadence, reasoning effort, the
routing matrix, `token_meter` at its default, the scenario turns, the grader, and the **fixed** S3
driver.

### MADE CHOICE 1 — the treatment is applied to **every `provider-openai` block**, not only `terra`

The routing matrix sends sub-agent work to other OpenAI cells (`sol`, `openai`, `luna`), and the
delegation confounder is load-bearing in this programme (`00-what-we-know.md:49`; 8rugb measured
9–17 delegate calls per terra S3 run). Setting the flag on `terra` alone would leave most OpenAI
requests in the run **untreated**, so `t1` would not be "the flag is on" as it would ship, and D2 —
whose whole subject is what the model does when a tool is not visible — would be measured on a
minority of the calls. Recorded as a choice, not an assumption; G9 is still read off the **root**
session, so this choice cannot manufacture a head saving.

### MADE CHOICE 2 — the SHIPPED default namespace table is used verbatim (it is T-5NS)

`702b361`'s `DEFAULT_NAMESPACES` is `{delegation, files, internet, knowledge, shell}` with
`DEFAULT_ALWAYS_LOADED = (bash, todo)` — i.e. **T-5NS, the split table the goal requires**, with
`internet` (never the reserved `web`). One difference from `cal`'s paper T-5NS is recorded here
rather than silently absorbed: the shipped `files` namespace has **six** members (it also lists
`apply_patch`, for the function-shaped fallback), where `cal`'s table listed five. No namespace
table is overridden by this lane.

### MADE CHOICE 3 — the fixed S3 driver, hash recorded per run

`scripted_driver.py` md5 **`dc307c50090b11d981eee44382668431`** (i0cm's patch applied to the
pristine `a5c14242df801eabe776e742724177da`). The pristine driver's `session_continuity_ok` was
false on **152/152** records and true on **zero** — a constant carrying no information, which hid
one genuine break that scored 90/100 and was counted. The hash is written into every run record.

---

## 5. Run validity — fixed before launch, so ACHIEVED VALIDITY is not a judgment call

A launched run is **VALID** iff every one of these holds:

```
V1  driver_record.json exists and turns_done == 5
V2  driver_record.json session_continuity_ok == true   (fixed driver only)
V3  a root session id resolves and its events.jsonl carries >= 1 llm:response
V4  the grader produced scorecard.json with a numeric total
V5  no HTTP 400 "Missing namespace for function_call" anywhere in the run
    (that means the container is NOT pinned at >= 702b361 — an infrastructure fault,
     recorded as INVALID, never as a finding about the treatment)
```

Anything else is **INVALID**, with its reason recorded. **An invalid run still counts against
spend** — that is the whole point of tracking achieved validity.

`achieved_validity(arm) = valid_runs / launches`, reported **per arm**. The goal's price rests on
**67%**; a better or worse figure **is itself a finding** and is reported as one.

---

## 6. THE CAP, AS ARITHMETIC — and the stop rule, fixed before spending

**Authority: $170**, owner-funded, separate from the $60 programme cap (which stands at
$1.11479 spent by Phase 1 + `cal`). Both are reported; they are not netted.

The goal's own arithmetic:
```
perfect validity : 20 terra x $4.63 + 4 anth x $3.53 = $92.60 + $14.12 = $106.72
at 67% validity  : 30 terra x $4.63 + 6 anth x $3.53 = $138.90 + $21.18 = $160.08
                                                        + slack        = $170.00
```
**That arithmetic closes at $4.63/terra launch and 0.67 validity.** It is checked, not assumed:
`$160.08 <= $170.00`, and `20/0.667 = 30.0`, `4/0.667 = 6.0`. **The goal's cap is correctly sized
FOR ITS OWN QUOTED PRICE.** Whether that price holds is what §6a buys.

**Prior evidence says the quoted price is optimistic**, and this is recorded now, not after:
threeknob measured terra-medium S3 at **$1.55/run** (`00-what-we-know.md:44`); **8rugb measured
terra S3 at $5.283–$6.633 mean per run** on 6 runs (`ANALYSIS.json`, `cost_mean_A` 6.633 /
`cost_mean_B` 5.283) at 100% validity. The goal's $4.63 sits between them. **If this lane's
observed price lands at 8rugb's level, the authority does not fund n=10/arm**, and that is a
finding under OUTCOME branch B — not a gap to absorb by overspending or by quietly shrinking n.

### 6a. The PILOT — pre-registered as the pricing probe, and it is not waste

```
PILOT = 1 t0 launch + 1 t1 launch + 1 g0 launch + 1 g1 launch
```
Every pilot run is a **pre-registered arm run** at its own arm's spec, so a valid pilot run counts
toward that arm's n. The g0/g1 pilot runs are **half of the mandatory guardrail pair each**. The
pilot also carries the DTU pin proof (§7). **Nothing in the pilot is bought twice.**

### 6b. The stop rule (fixed now; `analyze.py` computes it, the lane does not argue it)

```
p_t = observed mean $/terra LAUNCH (valid and invalid alike), from the pilot
p_a = observed mean $/anthropic LAUNCH
v_t = observed terra validity ; v_a = observed anthropic validity
     (floored at 0.67 for forecasting when the pilot is too small to move it,
      and the flooring is stated wherever the forecast appears)

REQUIRED_REMAINING = (20 - valid_t_so_far)/v_t * p_t  +  (4 - valid_a_so_far)/v_a * p_a

IF  spend_so_far + REQUIRED_REMAINING  >  170.00 :
      the pre-registered n=10/arm is NOT FUNDABLE at this authority.
      -> do NOT shrink n silently and do NOT overspend.
      -> record the affected deliverable NOT-POSSIBLE with this arithmetic (OUTCOME branch B),
         leading its reason with WHAT WAS EXECUTED.
      -> continue buying ONLY purchases that complete a deliverable at its OWN pre-registered n.
```

**Which gates survive a binding cap, and which do not — fixed now, before the numbers:**

- **G5a–G5d** are complete at **n=2/arm**. They are the MANDATORY, blocking, merge-gating pair and
  the goal calls them out by name. They are bought **first**, in full, before any bulk terra spend.
- **G9 / G11 / G4′ / G12** are token- and error-counts whose per-run variance is small; they are
  reportable **at the achieved n**, with the achieved n stated beside every value.
- **G10 and E5-total** genuinely need n=10/arm. If the cap binds, they are recorded
  **NOT-POSSIBLE-at-n** with the arithmetic — never "PASS at a smaller n", never silently shrunk.
- **D2** is reportable at the achieved n **with its n stated**, because a *firing* is decisive
  regardless of n (it is a tripwire, not a power calculation) while a *non-firing* at small n is
  reported as "did not fire at n=X", never as "does not recur".

**Residue rule** (`1ru`): if the remaining budget cannot buy the smallest indivisible purchase that
advances a deliverable, it is **not** available budget. The residue **and** the smallest useful
purchase it could not buy are both stated.

**Ordering of spend, fixed now:** (1) pilot including both guardrail arms → (2) complete the
guardrail pair to n=2/arm → (3) bulk terra t0/t1, interleaved arm-by-arm so a cap that binds
mid-flight leaves the two arms BALANCED rather than one arm complete and the other empty.

---

## 7. The DTU pin, proven ON THE WIRE — not by asserting the profile

The goal requires provider-openai **`702b361`** or newer *"demonstrated by a captured request
carrying the `namespace`/`tool_search` fields — not by asserting the profile"*, and names `mikb`'s
trap: `amplifier update` refreshes the bundle cache while `site-packages` stays at a different sha,
**a split state that silently produces a false arm**.

**Fixed proof procedure, all four legs required before any bulk spend:**

```
P-1  in-container: the installed provider package's own source contains tool_search
     ( grep -c tool_search on the INSTALLED amplifier_module_provider_openai/_tool_search.py )
P-2  in-container: the resolved commit of that install == 702b361... or a descendant
P-3  ON THE WIRE: a captured request body from a t1 run whose `tools` array contains
     BOTH  {"type":"tool_search"}  AND  >=1 entry with "defer_loading": true
P-4  ON THE WIRE: a captured request from turn >= 2 of a t1 run whose replayed
     `function_call` input item carries a `namespace` field
     (v5co's break-6 second half; its absence is the HTTP 400 in V5)
```

`t0` gets the **mirror-image** proof: the same capture points must show **no** `tool_search` entry
and **no** `defer_loading` key — the control arm must be provably untreated.

---

## 8. Terminal state — chosen ONCE, here, so it cannot be re-decided later

Per the goal's Procedure 5 and the `1ru` churn precedent (BLOCKED → REJECT → BLOCKED with no number
ever changing):

- The prerequisite is **present** (`702b361` is an ancestor of `origin/main`, verified at $0 before
  this file was written), so `cal`'s P0 does not fire and branch C is not reachable through it.
- **Terminal state is `work_resolve`** — OUTCOME **A** if every deliverable lands, OUTCOME **B**
  (still `work_resolve`) if the cap makes one NOT-POSSIBLE. A cap that binds is a **RESULT**.
- `BLOCKED.md` + `work_release` is used **only** if the outcome becomes unreachable for a reason
  **other than the cap** — a refused claim, a broken dependency that also blocks §6's guardrail
  purchase, or a defect in another component that no spend can route around.
- **Verdict vocabulary: BUILD / DON'T-BUILD / NOT-POSSIBLE (with arithmetic).** A **DON'T-BUILD is
  a PASS of this item.** No default is shipped here either way.

---

## 9. What this lane will NOT do (fixed now, so it cannot drift)

1. Not ship a default. PR 83's revert is not retired by a BUILD.
2. Not re-derive what `cal` measured — the granularity band `[2,002 , 3,006]`, the reserved
   namespace names, the 14.8%-net-worse population, the +18-token split cost. Those are cited.
3. Not use the flat table. T-5NS only (which is the shipped default — MADE CHOICE 2).
4. Not re-introduce the `web` namespace.
5. Not discharge G5a–G5d with a static hash comparison.
6. Not edit `ai-notes/00-what-we-know.md` or `probes/INDEX.md` — proposed diffs travel in the
   DONE-NOTE, named after this lane, for the manager to apply.
7. Not run `infra_ledger.sh sweep`. Teardown is `lane_teardown.sh` with the FULL lane name.
