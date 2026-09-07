# PROPOSED `ai-notes/00-what-we-know.md` DIFF — lane `ytja-routing-awareness-eval`

**This is a proposal in this lane's own artifact root.** Per the lane rules this lane does NOT
edit `ai-notes/00-what-we-know.md` or `probes/INDEX.md`; the program owner merges.

Two insertions are proposed: a new §2 subsection, and one new row in §3.

---

## INSERT INTO §2 (new subsection, after the last existing one)

```markdown
### (t) The lean head does NOT change what the model reaches for — and the item's own
### decision rule was unsatisfiable at its registered n **[ADDED 2026-09-07 [ytja]]**

`ytja` bought the routing-behaviour measurement Stage 1 ships without. **Fidelity proves a rule
is PRESENT; it does not prove the rule is FOUND** — `webu` passed every pre-registered gate and
still returned DON'T-BUILD because three tools went to ZERO executed calls. This is the FOUND
question, asked directly.

**THE INSTRUMENT FINDING COMES FIRST, AND IT COST $0.** The item's decision rule — *"CLEAR if
hidden-reach >= stock -5 pp AND over-reach <= stock +5 pp, both on the LB"* — is **UNSATISFIABLE
at its own registered n**. At the registered 10 prompts x n=5 (50 hidden obs/arm) and 5 x n=5
(25 control obs/arm), the BEST ATTAINABLE bound under *perfect agreement between the arms* is
**-7.13 pp** hidden and **+13.32 pp** control. Both clauses fail with no regression present.
Satisfying either needs **73 obs/arm/provider** — 155 launches/arm/provider, **620 launches,
$1,197.29** at the item's own reference prices, against a **$200** authority (**5.99x short**).
This independently reproduces `8rugb`'s published `n=73 -> -5.00 pp`. **Fourth instance of the
family** after S2a's vacuous Gate 3, `1ru`, and `8rugb`: *price a rule against its own power
before freezing it.* The primary rule is therefore recorded **NOT-POSSIBLE (cap-bound)**; no
CLEAR/NOT-CLEAR verdict is issued from this lane.

**WHAT THE TREATMENT ACTUALLY IS, measured on the container wire before any graded run.** Arms:
foundation `ed64999d` (stock) vs `7771ad22` (`lane/zc6t-lean-head-ship`), both fetched through a
Gitea mirror + `url_rewrites` — **necessary, because `bundles/anchors/bundle.md` sources
`tool-delegate` from a hardcoded `@main`, so settings-level SHA pinning would have produced two
BYTE-IDENTICAL arms and a void comparison.**

| quantity | stock | lean | delta |
|---|---:|---:|---:|
| head (system + tools JSON) | 84,336 ch | 83,722 ch | **-614 (-0.73%)** |
| `delegate` PREAMBLE (before `Available agents:`) | 1,192 ch | 940 ch | **-252 (-21.1%)** |
| agents in catalog | 12 | 12 | **0, byte-identical** |
| other 13 tool descriptions | — | — | **byte-identical** |

**The agent catalog does not change at all.** The treatment is confined to the `delegate`
preamble (where stock's *"Why delegate: Every tool call YOU make consumes YOUR context window
permanently … Delegation = longer, more effective sessions"* lived), `anchors/context/system.md`
(1,358 -> 1,142 B) and `amplifier-ecosystem.md`. **So any measured change in reaching is
attributable to the delegation FRAMING, not to catalog trimming** — a cleaner causal claim than
the item anticipated.

**RESULT: REACHING DID NOT CHANGE. 480 launches, 480 valid (validity 1.000), $130.60 of $200,
15 prompts x n=8 x 2 arms x 2 providers.** Every aggregate is IDENTICAL: claude-opus-5
hidden-reach **24/80 vs 24/80**, gpt-5.6-terra **42/80 vs 42/80**; control-pass **40/40 vs 40/40**
(opus) and **39/40 vs 39/40** (terra). **+0.00 pp on all four**, CI widths 17.5-30.2 pp. 26 of 30
per-prompt cells identical; the other 4 differ by <=1 run. **Zero hidden prompts regressed and
zero controls over-reached more** (one-sided Fisher p<0.05, per provider; Holm-adjusted p=1.0000
on both evaluable cells). No `webu`-shaped collapse anywhere.

**BUT WHAT IT REACHES FOR CHANGED, on terra, at p < 1e-6 -- and the pass/fail metric hides it
completely.** `mode` **0/120 -> 21/120** and `recipes` **0/120 -> 21/120** (both p<1e-6); first
capability reach `load_skill:per-repo-conventions` **33/40 -> 15/40** (p=0.000077) displaced by
`mode:list` **0/40 -> 18/40** (p=0.000001). **claude-opus-5 did not move at all** (0/120 -> 0/120)
-- another instance of the rule that a single-provider result does not generalise.

**MECHANISM, located in the text, not inferred.** One line of `anchors/context/system.md`:
*"Skills, modes, and recipes are available. Use `load_skill(list=true)`, `mode(operation="list")`,
or `recipes(operation="list")` to discover them."* became *"Discover skills, modes, recipes via
`load_skill(list=true)`, `mode(operation="list")`, `recipes(operation="list")`."* Every fact
survives -- all three tools, all three operations, `list` in each -- so **a fidelity check
passes**. What changed is the MOOD: a declarative statement of availability became an
**IMPERATIVE**, and terra obeyed it. **The item's worry was "a description can keep every fact
and stop triggering"; what was measured is a description that kept every fact and STARTED
triggering something else. Fidelity checking cannot see either direction.**

**BASELINE FINDING, both arms, both providers: claude-opus-5 does not route to the specialist
catalog for ordinary engineering asks.** On 7 of 10 hidden prompts it made **zero capability
reaches at all** -- not a wrong reach, no reach -- identically in both arms (a debugger ask, an
explorer ask, a git-ops ask, an architect ask, a DTU ask, a session-repair ask, an ecosystem-order
ask). It reached only on the three CLI/meta prompts (cli-expert, gitea, provider), 8/8 each.
terra reached on 80/80 but frequently outside the equivalence set.

**COST/WALL moved in the lean arm's DISFAVOUR but NOT significantly:** opus **+13.5%**
($0.3494 -> $0.3965/run) and +20.9% wall; terra +2.9%/+7.2%. Paired-by-prompt bootstrap (20,000
samples) **CI spans zero on both providers** (opus `[-0.0166,+0.1304]` USD). **This is NOT a `B`
result and must not be cited as one**, notwithstanding that (o) names +16.6% as the Anthropic
wash point.

**AND THE RULE WAS ~9x MORE UNDERPOWERED THAN THE BEST CASE IMPLIED.** Interval width is widest
near p=0.5 and the observed reach rates are **0.300 (opus) / 0.525 (terra)**, so the clauses need
**650 / 770** hidden obs and **100** control obs per arm per provider -- **3,240 launches,
$1,022.22 at this lane's OWN observed prices, 5.1x the authority.** Price such a rule at the reach
rate you expect, never at 1.0.

**Incidental defect, found on the stock wire and fixed by zc6t:** stock's `delegate` description
emits the `- agent="self": Spawn yourself as a sub-agent` line **TWICE** (once hardcoded in
`base_description`, once from the feature registry), so every stock session shipped it twice.

**A method finding worth more than the verdict.** A hidden-capability prompt with **no referent**
("make sure this works the way a real user would hit it") ends a single-shot run with a
**clarifying question and ZERO tool calls** — correct model behaviour, and a **degenerate cell
uninformative in BOTH arms**. Caught in a $0.10 pilot and fixed by amendment before the spend
(disclosed as amendment A1). `otr` paid for the same lesson after the fact.
```

---

## INSERT INTO §3 (new row)

```markdown
| The lean head is routing-neutral (t) | A scenario family where the delegation FRAMING is load-bearing in a way 15 short prompts are not: multi-turn work where the "delegation buys you context" argument has to survive several turns, or a catalog large enough that the preamble is doing selection work. This lane measured n=8/prompt/arm/provider on single-shot prompts against a 12-agent catalog, and its intervals are 17.5-30.2 pp wide — wide enough that a real effect smaller than that is invisible here. |
```

---

## What this lane deliberately does NOT propose

- **No default ships.** The item says so, and the measurement does not support one either way.
- **No re-tuning of any gate inside a comparison.** `g7h3` measured that S7-17's `>=5-boundary`
  validity gate rejects ~80% of opus-5 runs in BOTH arms; this eval wrote its own gate for its own
  single-prompt profile rather than inheriting that one (SPEC.md 9.1 / `5zp`).
- **No extrapolation across providers.** Reported per-provider and decisive per-provider, because
  `njpd`'s COND2 failed per-provider at 0.4737 and would have passed pooled at 1.1131.
