# `webu` — PREREG ADDENDUM B: the G9 estimator, superseded IN THE OPEN

**Committed 2026-09-07 UTC, AFTER the pilot pair (`t0-01`, `t1-01`) returned and BEFORE any bulk
run.** Same shape, and for the same reason, as `cal`'s W3 addendum (`PREREG.md` §5 of that lane):
*"the honest move is to say so and report the measured rate, **not** to widen the band after seeing
the number."*

Base: `PREREG.md` `c37ad942822e9c648bdc8b6cb10250950c512a96` ·
Addendum A: `ce4add33a29da9f80c81ff8d848ee06e1498d907`.

---

## B0. What the pilot showed, before anything below was written

Two runs, one per terra arm, both VALID (5/5 turns, continuity true, fixed driver
`dc307c50090b11d981eee44382668431`):

| | `t0-01` (control) | `t1-01` (treatment) |
|---|---:|---:|
| root request 0 — `input` chars | 1,974 | 1,974 (**byte-identical**) |
| root request 0 — `instructions` chars | 47,240 | 47,240 (**byte-identical**) |
| tools array entries | 14 flat functions | 6 + `{"type":"tool_search"}` |
| **request-0 total prompt = `input_tokens` + `cache_write_tokens`** | **18,727** | **14,111** |
| modal `cached_tokens` over the root session (**E-A as pre-registered**) | 18,724 | 73,981 |
| locally serialised tools-array tokens (**E-B as pre-registered**) | 8,117 | 8,324 |

## B1. E-A, as I wrote it, is DEFECTIVE — and that defect is recorded, not repaired

`PREREG-ADDENDUM-A` §A2 fixed E-A as *"the MODAL value of `cached_tokens` over root-session
requests with `cached_tokens >= 1024`"*, on the strength of `00-what-we-know.md`'s observation that
the pinned head *"froze at 18,454 for 80 consecutive requests"*.

**That reasoning does not survive contact with a 5-turn S3 session.** In `ccA-01` the head froze
because the conversation itself was not being cached. Under `persist` mode plus OpenAI's grow-only
cache, the conversation IS cached, `cached_tokens` climbs monotonically with the transcript, and the
mode lands on whatever conversation length recurred most — **73,981 in `t1-01`, which is a
transcript measurement wearing a head measurement's name.**

Worse, the defect is **arm-asymmetric**: `t1-01`'s transcript grew to 262,186 `input` chars against
`t0-01`'s 78,725, so the modal value is inflated *more* in the treatment arm. An estimator that is
biased in the direction of the arm under test is not a weak estimator; it is a wrong one.

**E-A therefore stands, permanently, as a defect in this lane's own gate.** Its value is reported
in `FINDINGS.md` beside the corrected one, labelled `DEFECTIVE-BY-CONSTRUCTION`, exactly as `cal`
left W1's out-of-band verdict standing. It is **not** silently replaced and **not** dropped.

## B2. E-B measures the WIRE, not the BILLED PROMPT — and that is a finding, not a defect

E-B (`len(json.dumps(tools))/4.627`, 12v's method) returns **8,324 tok for `t1-01` vs 8,117 for
`t0-01`** — the treatment looks 207 tokens *worse*. It is not. The namespace entries carry every
member's full `description` **and** full `parameters` schema inline (`files` alone is 10,389 chars),
because the server needs them in order to serve `tool_search`. What `defer_loading: true` buys is
that the server does **not** bill those bytes into the prompt: the same request that ships a
38,516-char tools array is charged a **14,111-token** total prompt against the control's 18,727.

**This is a genuinely new measurement and it invalidates a method, not just a number.**
`12v`'s chars/4.627 rule is sound for a flat tools block, where wire bytes and billed prompt are the
same population. **Under `tool_search` they are different populations, and any local byte-count
analysis of a namespaced block will read the saving as a small LOSS.** Recorded loudly so the next
lane does not re-derive it the expensive way. E-B is retained in `FINDINGS.md` **as the wire-payload
measurement it actually is**, renamed accordingly, and is no longer an estimator of the head.

## B3. E-A′ — the corrected estimator, fixed HERE, before the bulk runs

```
E-A'   head_tok(run) = input_tokens + cache_write_tokens
                       of the FIRST root-session llm:response whose request carried a
                       non-empty `tools` array (root request index 0).
```

Why this one, stated before it is used at n>1:

1. **It is the whole prompt, server-counted.** The harness normalisation is
   `input_tokens` excludes `cache_write_tokens` (`_harness/README.md`), so their sum is the full
   billed prompt for that request. No local byte estimate enters it.
2. **Everything except the tools block is held byte-identical at that request.** Request 0 is turn 1
   of a scripted scenario: `input` is 1,974 chars and `instructions` is 47,240 chars in **both**
   arms, measured. The arms therefore differ at exactly one place, which is the definition of the
   quantity G9 asks for.
3. **It cannot drift with the transcript**, which is precisely what broke E-A.
4. **It has no free parameter.** There is nothing in it to tune after seeing a result.

**G9's threshold is UNCHANGED** — it is EVAL-SPEC's, quoted in `PREREG.md` §2 and not this lane's
to move:

```
G9 PASS iff  median_over_valid_t1(E-A')  <=  median_over_valid_t0(E-A') - 3000
```

**The disagreement rule survives, re-pointed.** If E-A′ and the **first cached read**
(`cached_tokens` of the first root response reporting `>= 1024`, an independent server-side figure)
disagree in direction, **G9 is UNINFORMATIVE** and the disagreement is the reported finding.
Two independent server-side quantities must agree before a head saving is banked.

## B4. Disclosure, in full

The pilot values in §B0 were visible when this file was written. That is stated rather than hidden,
and it is why:

- **no threshold anywhere is changed** — 3,000 tok is EVAL-SPEC's number and stays;
- **the defective estimator is still reported**, with its value, in the findings;
- **E-A′ was chosen on structural grounds** (§B3 1–4) that can be checked without reference to
  whether it happens to make G9 pass;
- **n is still 10 per arm as pre-registered**, and 18 of the 20 terra runs had not been bought when
  this was committed, so nothing here is a post-hoc selection over a completed sample.

## B5. Second item found by the pilot — a HARNESS DEFECT, reported not worked around

`_harness/configure_cell.py --max-tokens` **silently fails to apply on the current foundation
layout.** `find_bundle_md()` returns `bundles/anchors-amp-dev/bundle.md`, but the
`context.config.max_tokens: 300000` line lives in `bundles/anchors/bundle.md` (measured in all four
containers of this lane). `patch_max_tokens()` then exits **non-zero on stderr** — and every caller
in this programme pipes only **stdout** (`| tail -2` / `| tail -3`), so the failure is invisible and
the run proceeds at the default 300k budget with **no compaction boundary at all**.

Consequences, fixed here before the remaining guardrail runs:

- `g0-01` / `g1-01` ran at the **default** budget. They are valid runs and they discharge the
  byte-identity gates (G5a, G5b′, G5c) and G5d's share and `ID_ONLY` clauses; they cannot discharge
  G5d's **re-warm-at-a-boundary** clause, because they cross no boundary.
- `g0-02` / `g1-02` are run with the budget patched **directly** (`bundles/anchors/bundle.md`
  `max_tokens: 300000 -> 45000`, plus the `_calculate_budget` cap `configure_cell.py` would have
  applied), so the pair satisfies EVAL-SPEC §3's *"multi-turn with >=3 compaction boundaries"*.
  Both arms of pair 2 get the identical patch, so the arm remains the one variable **within a pair**.
- The pairing is recorded in `meta.json` per run; `analyze.py` compares g0/g1 **within a pair**,
  never across pairs.
- The defect itself is reported as a proposed correction in the DONE-NOTE for the manager to apply.
  This lane does not edit `_harness/configure_cell.py` — it is outside the paths this lane owns.
