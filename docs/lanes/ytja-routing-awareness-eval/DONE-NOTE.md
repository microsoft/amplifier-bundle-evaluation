# DONE-NOTE — `ytja-routing-awareness-eval` (`model_performance-ytja`)

**OUTCOME: branch B — RESOLVED AT THE CAP.** Every deliverable below is DONE except the item's
own decision rule, which is **NOT-POSSIBLE (cap-bound)**. That is the normal end state for a
capped measurement lane, and it is a **result**, not a blocker.

**WHAT WAS EXECUTED, first, because a bare refusal reads as "nothing ran":**
**480 launches · 480 valid (validity 1.000) · 15 prompts × n=8 × 2 arms × 2 providers ·
$130.60 of a $200 authority · 666 session trees captured · 2 DTUs, both destroyed, ledger 0 open
rows.** The item's registered n was 5; **n=8 was bought and delivered.** What could not be bought
is the *rule*, which needs 3,240 launches / $1,022.22.

---

## THE THREE FINDINGS

### 1. Reaching did not change. Not by one run, on any aggregate.

| scope | measure | stock | lean | diff | 95% CI |
|---|---|---:|---:|---:|---|
| claude-opus-5 | hidden-reach | 24/80 = 0.300 | 24/80 = 0.300 | **+0.00 pp** | [−13.99, +13.99] |
| claude-opus-5 | control-pass | 40/40 = 1.000 | 40/40 = 1.000 | **+0.00 pp** | [−8.76, +8.76] |
| gpt-5.6-terra | hidden-reach | 42/80 = 0.525 | 42/80 = 0.525 | **+0.00 pp** | [−15.12, +15.12] |
| gpt-5.6-terra | control-pass | 39/40 = 0.975 | 39/40 = 0.975 | **+0.00 pp** | [−10.58, +10.58] |

Per prompt: **26 of 30 cells identical**; the 4 that differ, differ by ≤1 run. **Zero** hidden
prompts regressed and **zero** controls over-reached more (one-sided Fisher, p < 0.05, per
provider). No `webu`-shaped collapse anywhere. **This is a null, and it is a clean one.**

### 2. But WHAT the model reaches for changed materially — on terra only, at p < 1e-6.

The pass/fail metric hides this completely.

| provider | signal | stock | lean | Fisher p |
|---|---|---:|---:|---:|
| terra | `mode` called anywhere in the run | **0/120** | **21/120** | **< 1e-6** |
| terra | `recipes` called anywhere in the run | **0/120** | **21/120** | **< 1e-6** |
| terra | first reach = `load_skill:per-repo-conventions` (H1/H6/H7/H8/H9) | 33/40 | 15/40 | 0.000077 |
| terra | first reach = `mode:list` (same five) | **0/40** | **18/40** | 0.000001 |
| opus | `mode` / `recipes` anywhere | 0/120 | 0/120 | 1.0 |

**The mechanism is one line of `bundles/anchors/context/system.md`, located in the text, not
inferred:**

- stock: *"Skills, modes, and recipes are available. Use `load_skill(list=true)`,
  `mode(operation="list")`, or `recipes(operation="list")` to discover them."*
- lean: *"Discover skills, modes, recipes via `load_skill(list=true)`,
  `mode(operation="list")`, `recipes(operation="list")`."*

Every fact survives — all three tools, all three operations, `list` in each. **A fidelity check
passes.** What changed is the **mood**: a declarative statement of availability became an
**imperative**. terra obeyed it and started executing all three discovery calls; opus did not
move at all.

**This is the exact class of failure the item was filed to catch, arriving with the opposite
sign.** The item's worry was *"a description can keep every fact and stop triggering."* What was
measured is a description that kept every fact and **started triggering something else.**
Fidelity checking cannot see either direction.

### 3. The item's decision rule was unsatisfiable — and by ~9× more than even the best case implied.

Registered before any run: at 10 prompts × n=5 (50 hidden obs/arm) and 5 × n=5 (25 control
obs/arm), the **best attainable** bound under *perfect agreement between the arms* is
**−7.13 pp** hidden and **+13.32 pp** control. Both clauses fail with **no regression present**.
The best case needs **73 obs/arm/provider** — independently reproducing `8rugb`'s published
`n=73 → −5.00 pp`.

**The measurement then showed the best case was the wrong yardstick.** Interval width is widest
near p = 0.5, and the observed reach rates are **0.300 (opus)** and **0.525 (terra)**:

| clause | observed rate | obs/arm/provider actually needed |
|---|---:|---:|
| hidden-reach ≥ −5 pp (opus) | 0.300 | **650** |
| hidden-reach ≥ −5 pp (terra) | 0.525 | **770** |
| over-reach ≤ +5 pp | 0.0125 | **100** |

**2 arms × 2 providers = 3,240 launches = $1,022.22** at this lane's own observed prices —
**5.1× the $200 authority.** Three arms: 4,860 launches, $1,533.33.

**Fourth instance of a family the program has already paid for three times** (S2a's vacuous
Gate 3, `1ru`, `8rugb`'s unsatisfiable success condition): *price a rule against its own power
before freezing it — and price it at the reach rate you expect, not at 1.0.*

---

## DELIVERABLES

| deliverable | state |
|---|---|
| Pre-registration committed BEFORE the first run, SHA quoted | **DONE** — `c6be08d5320e81c987a7a1150d95e8a77829c669`; scenarios, per-prompt expected target + equivalence set, decision rule, pooled-vs-per-provider, all fixed there. Amendment A1 `1e9bc229480aee4e934ba14d3ca5a646a7fafc69`; observed price + stopping rule `1480c0b`. |
| **THE DECISION RULE, applied verbatim** | **NOT-POSSIBLE (cap-bound)** — applied and reported in `RESULTS.md`; both clauses fail on both providers, and both fail *at the interval width*, not on a measured regression. Needs 3,240 launches / $1,022.22 vs $200. No CLEAR / NOT-CLEAR verdict is issued, because none is supportable. |
| Name which prompts regressed | **DONE — none did.** Zero hidden prompts and zero controls flagged at one-sided Fisher p < 0.05 on either provider. Holm-adjusted p = 1.0000 on both evaluable hidden cells. |
| Reach-rate + over-reach rate, per provider AND pooled, with n and intervals | **DONE** — table above and in `RESULTS.md`; pooled reported and explicitly **not decisive** (`njpd`). |
| Per-prompt results, not just aggregates; degenerate cells marked UNEVALUABLE | **DONE** — all 30 cells tabulated; **24 marked UNEVALUABLE** rather than verdicted (`otr`). |
| DTUs ≤ 4, every one destroyed, ledger 0 open rows verified | **DONE** — 2 DTUs + 1 Gitea (3 ≤ 4); both DTUs `VERIFIED GONE / probe-after=ABSENT`; **0 open rows owned by this lane**. Gitea caveat below. |
| Spend arithmetic to the cent, per-run price stated BEFORE the bulk spend | **DONE** — price registered at `1480c0b` before the sweep; full arithmetic below. |
| Learning deliverable, no default ships | **DONE** — no default proposed, in either direction. |
| Proposed `ai-notes` diff in this lane's artifact root | **DONE** — `proposed-ai-notes-ytja.md`. `ai-notes/00-what-we-know.md` and `probes/INDEX.md` untouched. |
| Arm 3 (stage-1) recorded as a re-run item WITH ITS PRICE | **DONE** — see below. Nothing substituted. |

---

## SPEND — to the cent

**Registered before the bulk spend** (`1480c0b`), from a 6-launch probe on this eval's own
single-prompt profile, because the item's reference prices were quoted for multi-turn S5/S7 runs
and an authoring rule forbids reusing a price across run shapes:

```
per rep = 2 arms x [ terra(10 x 0.3145 + 5 x 0.0547) + opus(10 x 0.4838 + 5 x 0.1431) ]
        = $17.94 per rep of 60 launches
target n=8 -> $143.54 ; stop at n=8 or when the next rep would pass $185 of $200
```

**Actual:**

| item | launches | cost |
|---|---:|---:|
| discarded pilot (amendment A1) | 4 | $0.10 |
| graded sweep (probe folded into rep 1) | **480** | **$130.6017** |
| **TOTAL** | **484** | **$130.70** |

Predicted $143.54, actual $130.60 — **9.0% under**. Mean **$0.2721 / launch**. Validity
**480/480 = 1.000**; no run was paid for and discarded except the 4 disclosed pilot launches.
Measured means over all 480: terra hidden $0.2287 / control $0.0565; opus hidden $0.4834 /
control $0.1520.

**RESIDUE: $69.30.** The smallest purchase that would advance the one open deliverable is the
**arm-3 re-run at $65.30** (120 launches) — the residue *would* cover the third arm alone, but
**not** the **$195.90** three-arm re-run a clean comparison needs, and **arm 3 has no code to
point at** in any case. Nothing was spent that could not be used.

**No overspend. Nothing shrunk silently: n went UP from the registered 5 to 8, and the one thing
that shrank — the primary rule's evaluability — is reported as the finding, not absorbed.**

---

## ARM 3 (stage-1) — NOT RUN, priced

At run time **`mse0` and `6f80` have no branch at all** (queued behind zc6t landing);
**`kp79`/`kv98` are a different workstream** — per-bundle catalog diets in bundle repos
(browser-tester, dot-graph, context-intelligence, work-tracker) **outside this container's mount
set**, only partially pushed. There is no stage-1 tree to pin, and **nothing was substituted for
it**, per the item's instruction.

**Price at this lane's own observed prices:** third arm alone, same design (15 × n=8 × 2
providers) = **120 launches = $65.30**. Clean 3-arm comparison = **360 launches = $195.90**
(arms 1–2 are reusable as-is only if container, CLI SHA and prompt set stay byte-identical).

---

## WHAT WAS UNDER TEST — measured on the wire, before any graded run

Arms: `amplifier-foundation` **`ed64999d`** (stock) vs **`7771ad22`** (`lane/zc6t-lean-head-ship`).
CLI pinned identically: **`28588b93`** (`2026.09.06-be25afd`, core 1.6.1).

**Ref-pinning alone would have produced two byte-identical arms and a void comparison.**
`bundles/anchors/bundle.md:54` sources `tool-delegate` from a hardcoded
`amplifier-foundation@main`, and `anchors-amp-dev/bundle.md` includes `anchors` at `@main`. Both
arms therefore fetch foundation through a **Gitea mirror + `url_rewrites`**, identical code path,
differing only in the mirrored tree. **G-ARM verified before spending:** `grep -c 'Why delegate'`
**1 / 0**; `system.md` **1358 / 1142 B**; cache HEAD = the arm SHA in each container.

| quantity | stock | lean | Δ |
|---|---:|---:|---:|
| head (system + tools JSON) | 84,336 ch | 83,722 ch | **−614 (−0.73%)** |
| `delegate` preamble | 1,192 ch | 940 ch | **−252 (−21.1%)** |
| agents in catalog | 12 | 12 | **0, byte-identical** |
| other 13 tool descriptions | — | — | **byte-identical** |

**The agent catalog does not change at all**, so any change in reaching is attributable to the
**delegation framing and `system.md`**, not to catalog trimming — a cleaner causal claim than the
item anticipated.

---

## OTHER MEASURED RESULTS, stated with their limits

- **claude-opus-5 does not route to the specialist catalog for ordinary engineering asks.**
  On 7 of 10 hidden prompts it made **zero capability reaches at all** (not a wrong reach — no
  reach), identically in both arms: H1, H2, H6, H7, H8, H9, H10. It reached only on the three
  CLI/meta prompts (H3 cli-expert, H4 gitea, H5 provider), 8/8 each. **terra reached on 80/80**
  hidden runs but frequently to a target outside the equivalence set. *(measured · both providers
  · n=80/arm/provider · confidence: measured · `RESULTS.md`, `graded.jsonl`)*
- **Cost/wall moved in the lean arm's DISFAVOUR but NOT significantly.** opus **+13.5%**
  ($0.3494 → $0.3965/run) and **+20.9%** wall; terra +2.9% / +7.2%. **Paired-by-prompt bootstrap
  (20,000 samples) CI spans zero on both providers** — `[−0.0166, +0.1304]` USD on opus. **This is
  NOT a `B`-term result** and must not be cited as one, notwithstanding that `skw3` names +16.6%
  as the Anthropic wash point. A single-prompt workload at n=8/prompt cannot settle that.
  *(measured · confidence: measured-but-not-significant)*
- **G-INSTRUMENT passed cleanly.** `events.jsonl tool:post` and `transcript.jsonl role:"tool"`
  disagreed on **0 / 480** runs. Runs with a thinking-text mention of a reach tool but **zero
  executed** reach: **0** — so on this corpus a thinking-text grader would not have been fooled,
  unlike `webu`'s first recompute. The discriminator was still applied throughout.
- **Incidental defect on the stock wire, already fixed by zc6t:** stock's `delegate` description
  emits the `- agent="self": Spawn yourself as a sub-agent` line **twice** (hardcoded in
  `base_description` *and* from the feature registry). Confirms zc6t's own code comment against a
  value read off the wire.

---

## DEVIATIONS AND INCIDENTS — disclosed, not buried

1. **Amendment A1** (`1e9bc22`, committed before any graded run). A $0.10 4-launch pilot showed
   that a hidden prompt with **no referent** ends a single-shot run with a **clarifying question
   and zero tool calls** — correct model behaviour, and a degenerate cell uninformative in both
   arms. Six hidden prompts gained a concrete referent (`/root/work`). **No expected target or
   equivalence set changed**; the capability is still never named. Made from stock-arm data only,
   with no lean-arm run in existence, so it cannot favour an arm. The 4 pilot launches were
   **discarded** and counted toward n for nothing; their spend is still charged above.
2. **The item's five given prompts were kept.** All five capabilities were verified present in the
   arm catalog before registration. H6–H10 were lane-designed against catalog entries' own
   `USE WHEN` lines, per the item.
3. **No validity gate was inherited.** `g7h3` measured that S7-17's `≥5-boundary` gate is
   calibrated for terra and rejects ~80% of opus-5 runs in **both** arms; SPEC.md 9.1 freezes
   profiles and `5zp` established that moving one makes runs incomparable. This eval wrote its own
   gate for its own single-prompt profile (root session exists · `prompt:complete` present · at
   least one executed tool or LLM response). It rejected **0 / 480**.
4. **Ledger: the Gitea row could not be closed by the sanctioned tool.** `amplifier-gitea destroy`
   is not idempotent (rc=1, *"Environment not found"*, so `teardown` recorded FAILED), and
   `reconcile` reports gitea rows *"NOT PROBEABLE — use teardown"* — neither verb closes it.
   Absence was proved three independent ways: `amplifier-gitea list` → `[]`; `incus list` showing
   only the two unrelated foreign containers; port 10240 not listening. The single row matching
   **both** this lane's id **and** this lane's owner was then flipped `open → swept` by a script
   that asserts exactly one row matched, with `infra.tsv` backed up first. **No other lane's row
   was read or written; `sweep` was never run.** Filed as **`model_performance-xv25`**.
5. **Both DTUs were destroyed and independently probed ABSENT** (`probe-after=ABSENT`), and
   `amplifier-digital-twin list` afterwards shows only the two foreign containers that were
   already running.

---

## REPRODUCE AT $0

```
docs/lanes/ytja-routing-awareness-eval/
  PRE-REGISTRATION.md            the design, the rule, the power verdict, amendment A1, the price
  RESULTS.md                     every table in this note, regenerated from graded.jsonl
  scenarios/prompts.json         15 prompts, expected targets, equivalence sets, prompt_v1 history
  scenarios/work-seed/           the fixed workspace the control prompts act on
  tools/run_cell.py              driver (session identified by dir-diff, never by stdout)
  tools/grade.py                 grader (executed tool:post; transcript cross-check; thinking-text counted separately, never graded on)
  tools/analyze.py               primary + secondary rules, per-prompt, per-provider, pooled
  tools/analyze_extra.py         reach-target shift, failure-mode split, cost/wall bootstrap
  tools/power_ytja.py            the $0 power computation
  evidence/arm-wire-census.txt   both arms' head census, captured from the containers
  evidence/power-analysis.txt    power table + the n=73 reproduction of 8rugb
```

Captures (480 runs, 666 session trees, ~1.4 GB):
`/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260907-ytja-routing-awareness/`

```bash
python3 tools/analyze.py --graded <CAP>/graded.jsonl --prompts scenarios/prompts.json --out RESULTS.md
```
