# `webu` — PREREG ADDENDUM A: how each gate is COMPUTED

**Committed 2026-09-07 UTC, before any run output of this lane had been read.**
Base pre-registration: `PREREG.md` @ `c37ad942822e9c648bdc8b6cb10250950c512a96`.

`PREREG.md` §2 quotes every EVAL-SPEC §3 gate verbatim and changes no threshold. Those gates are
stated in English ("median pinned `cache_read`", "distinct tools actually loaded"). This addendum
fixes the **field-level arithmetic** that turns each one into a number, so the operationalisation
cannot be chosen after the values are visible. **No threshold below differs from `PREREG.md` §2.**

Status when this file was committed: the four pilot runs (`t0-01`, `t1-01`, `g0-01`, `g1-01`) were
**in flight**. No `scorecard.json`, `measure.json`, `driver_record.json` or capture of this lane had
been opened. The pin-proof legs P-1/P-2 **had** been read (they are a prerequisite check with no
threshold a result could bend, and they are recorded in `wire/pin-proof-P1-P2.txt`).

---

## A1. Data sources, per run

| artefact | produced by | used for |
|---|---|---|
| `driver_record.json` | the **fixed** S3 driver, md5 `dc307c50090b11d981eee44382668431` | V1, V2, wall |
| `scorecard.json` | `s3/grader.py` in-container | G10, E5 |
| `measure.json` | `probes/dw_measure.py` over the run tree | G11 cost, G5d share |
| `all-sessions/**/events.jsonl` | foundation `logging.yaml` | everything else |
| `meta.json` | `run_cell.sh` | arm, cell, driver md5, provider pin |

`llm:request.data.raw` carries the **entire request body** actually sent (verified on prior
captures: OpenAI `{instructions, input, tools, tool_choice, …}`; Anthropic `{system, messages,
tools, …}`). Every wire-level gate below reads that object; nothing is reconstructed.

The run **tree** is the root session plus every session whose `parent_id` chain reaches it — the
same contamination-free resolution `dw_measure.py` uses.

---

## A2. G9 — head reduction

Two estimators, both computed, **the first is the verdict**:

```
E-A  pinned_head_tok(run) = the MODAL value of
     llm:response usage cached_tokens (a.k.a. cache_read_tokens) over ROOT-session
     requests with cached_tokens >= 1024   (1024 = OpenAI's cacheable minimum, P4)
     -- the "frozen head" ccA-01 showed as 18,454 for 80 consecutive requests.

E-B  tools_block_tok(run) = len(json.dumps(raw["tools"], separators=(",",":"))) / 4.627
     from the FIRST root request of the run.
     4.627 chars/token is 12v's measured constant; bub/cal reproduce 8,677 and 1,104 with it.
```

```
G9 PASS  iff  median_over_valid_t1(E-A)  <=  median_over_valid_t0(E-A) - 3000
```

**Pre-registered disagreement rule:** if E-A and E-B disagree in **direction** (one says the head
shrank, the other says it grew), **G9 is UNINFORMATIVE** and the disagreement is the reported
finding. A single estimator that quietly contradicts the other is how a wrong number ships.

## A3. G10 and E5 — quality

From `scorecard.json`: `total`, `pass`, `dimensions`, `constraint_breakdown`, `checks[]`.

```
G10 PASS iff  median(total|t1) >= median(total|t0) - 5
         AND  sum(pass|t1) >= sum(pass|t0) - 1

G10 UNINFORMATIVE iff median(total|t0) == median(total|t1) == 100
                  AND sum(pass|t0) == sum(pass|t1) == n      (the ceiling rule; never PASS)
```

E5's six pre-registered constraints map to these exact fields:

| constraint | field |
|---|---|
| C1 stdlib-only | `constraint_breakdown.C1_stdlib_only > 0` |
| C2 exit codes | `constraint_breakdown.C2_exit_codes > 0` |
| C3 under 120 lines | `constraint_breakdown.C3_under_120_lines > 0` |
| turn-2 retention | `dimensions.b_constraints >= 20` |
| turn-3 revision | `dimensions.c_revision >= 10` |
| turn-5 extension | the check whose name contains `--suggest`, `ok == true` |

`E5-constraint FAIL` iff any one of those six has `pass_count(t1) <= pass_count(t0) - 2`.
The **full** per-check table is reported as supplementary evidence; only these six carry a verdict.

## A4. G11 — cost and cadence

`cost_usd` from `measure.json` (the audited `ANALYZER_FORMULA.md` arithmetic — not re-derived here).
`boundaries(run)` = count of root-session events whose event name contains `compact`.

```
G11 PASS iff mean(cost|t1) <= mean(cost|t0)
        AND  |mean(boundaries|t1) - mean(boundaries|t0)| <= 0.15 * mean(boundaries|t0)
G11 is ADVISORY (cost means are noisy -- 00-what-we-know.md:129).
If mean(boundaries|t0) == 0 the cadence clause is UNDEFINED, reported as such, never as PASS.
```

## A5. G4′ — the real loaded set (tripwire T4)

```
loaded(run) = union over ROOT-session requests of
              { function-shaped entries in raw["tools"] }        (name key present, type != namespace)
            U { every tool name appearing in any tool_search_output item }
G4' PASS iff median(|loaded|) over valid t1 runs <= 10
```
Computed for **both** arms; the verdict is read on `t1` (t0 is 14 by construction and is the
control reading, not a failure).

## A6. G12 — tool-pair atomicity

```
g12_hits(run) = occurrences of  "No tool call found for function call output"
                OR "InvalidRequestError"
                across turn*.out, driver.log, run.log and every events.jsonl of the tree
G12 PASS iff sum(g12_hits) over ALL t1 runs == 0
```

## A7. G13 — compaction survival (dependency declared in `PREREG.md` §3)

Reported, never PASS:
- `boundaries(t1) == 0` → **UNINFORMATIVE — no boundary crossed**, dependency still named.
- `boundaries(t1) > 0` → **NOT-POSSIBLE — `context-simple` break 5 unlanded** (v5co patch artifact,
  no home), with the observed post-boundary tool availability reported as an *observation*.

## A8. G5a / G5b′ / G5c / G5d — the Anthropic guardrail, LIVE

Population: every `llm:request` in the `g0`/`g1` run trees whose provider is `provider-anthropic`,
indexed per session in wire order.

```
G5a   tools_sha(req) = sha256(json.dumps(raw["tools"], sort_keys=True, separators=(",",":")))
      PASS iff, comparing g0 and g1 at every request index i that BOTH arms reached,
      tools_sha differs at 0 indices.  N of N identical. No tolerance band.

G5b'  per request, over raw["tools"]:
      B1 exactly one entry carries cache_control
      B2 that marker exists at all (breakpoint used)
      B3 it sits on the LAST entry of the array that can carry one
      B4 total cache_control markers across the array <= 4
      PASS iff B1-B4 hold in EVERY arm at EVERY request index. FAIL if any violation in EITHER
      arm, even when the two arms AGREE.  (cal's re-scope: a RELATIVE gate cannot see identical drift.)

G5c   system_sha(req) = sha256(json.dumps(raw["system"], sort_keys=True, separators=(",",":")))
      PASS iff distinct system_sha per run == 1 in every g0 and g1 run
      AND system BYTE LENGTH is identical between g0 and g1 (delta == +0 B).

G5d   share    = cache_read_share_pct from measure.json; PASS iff |share(g1) - share(g0)| <= 10.0
      re-warm  = at every compaction boundary in g1, the number of requests until cache_read
                 returns to >= 50% of its pre-boundary value; PASS iff <= 1 at every boundary
      ID_ONLY  = consecutive-request pairs whose serialized `messages` prefixes differ ONLY inside
                 an "id" key; PASS iff == 0
      G5d PASS iff all three clauses PASS.
```

**A live run is required.** If the `g0`/`g1` arms do not produce Anthropic requests, G5a–G5d are
recorded **NOT-POSSIBLE**, never discharged by the static hash comparison `cal` already has.

## A9. D2 and validity

Exactly as `PREREG.md` §1a and §5. The surrogate regex is applied to the `command` argument of a
`bash` `tool:pre` event after stripping leading `cd <path> && ` segments; the file-domain tool set
is `{read_file, write_file, edit_file, glob, grep, apply_patch}`.

## A10. Spend

```
spend(run)     = measure.json cost_usd  (0.0 and flagged if measure.json is unreadable)
spend(arm)     = sum over ALL launches of that arm, valid and invalid alike
achieved_validity(arm) = valid_runs / launches
```
`analyze.py` recomputes every table in `FINDINGS.md` from the captures and **spends nothing**
(12v's convention).
