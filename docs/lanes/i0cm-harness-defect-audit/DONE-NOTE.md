# DONE-NOTE — lane `i0cm-harness-defect-audit`

Work item: `model_performance-i0cm` (project `model_performance`).
**Terminal outcome: (A) RESOLVED.** Every deliverable is **DONE**. Nothing is NOT-POSSIBLE.
**Spend: $0.00** of a **$15.00** authority — the $0 path settled it, which is what the goal said to
expect.

---

## The answer in five lines

> **The defect is REAL. The blast radius claim is REFUTED. It voids nothing.**
> `session_continuity_ok` is `false` in **151 of 151** driver records ever produced by this driver,
> across **9 capture roots**. A flag that is constant across every run of every arm carries **zero
> information** — it cannot have moved a comparison, and any lane that gated on it would have had
> 0 valid runs and published nothing. **All 9 roots published. No lane ever gated on it.**
> Re-run with the corrected check, **148/151** are continuous — and the 3 exceptions contain
> **one genuine break nobody saw**, because the flag was crying wolf on the other 150.
> **The real cost is the inverse of the claim: not voided valid runs, but a masked invalid one.**

---

## Deliverables

| # | Deliverable (from the goal) | State |
|---|---|---|
| D1 | The defect quoted **VERBATIM** with the exact driver path and 8rugb's own evidence | **DONE** — §1 |
| D2 | **Reproduced at $0** on ONE captured run: the `Session ID:` vs `Resuming session:` mismatch in a real `turn*.out`, and the `prompt:complete` count that contradicts the flag | **DONE** — §2, `evidence/repro-one-run.txt` |
| D3 | **BLAST RADIUS, enumerated not estimated** — every lane importing/copying the driver, and the published conclusions resting on them | **DONE** — §3, `evidence/blast-radius.txt` |
| D4 | Each affected conclusion classified **VOID / STANDS / NEEDS-RERUN**, reasoning per item, NEEDS-RERUN priced | **DONE** — §4. **VOID 0 · STANDS 5 · NEEDS-RERUN 0** |
| D5 | **THE DECIDING QUESTION: did any lane ever ACT on the bad flag?** | **DONE** — §5. **No. Real but inert.** |
| D6 | If real: **fix the driver with a FAIL-BEFORE test** covering the `--resume` phrasing AND the empty-stdout case | **DONE** — §6. Fails 3/6 before, passes 6/6 after. Shipped as a lane artifact + a `git apply --check`-clean patch, because **the driver is not in a repo this lane owns** (§8, goal defect) |
| D7 | A proposed `ai-notes/00-what-we-know.md` diff **in my own directory**, shared file untouched | **DONE** — `i0cm-00-what-we-know.diff` |

---

## §1 — The defect, verbatim, with the path

**Driver (canonical):**
`/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/scenarios/s3/scripted_driver.py`
(145 lines, `md5 a5c14242df801eabe776e742724177da`) — **71 byte-identical copies**, one canonical +
70 lane-worktree copies.

**8rugb's claim, verbatim** (`.../8rugb-delegation-split-eval/amplifier-foundation/docs/lanes/8rugb-delegation-split-eval/DONE-NOTE.md`, Finding 3):

> - **`scripted_driver.py`'s `session_continuity_ok` is a false negative by construction** — it greps
>   each turn's stdout for `Session ID: <sid>`, but `amplifier run --resume` prints
>   `Resuming session: <sid>`. **False for 14/14 runs of both arms** while every container's root
>   session carried exactly **5 `prompt:complete` events**. Taken at face value it voids 100 % of
>   runs of any lane using this driver — including, potentially, `h7n`'s.
> - **Turn stdout capture returns empty on large turns** — `B-oai-01` turns 4 and 5 came back
>   `out_len == 0` on the host while the container had executed both. Grading is nearly unaffected
>   (90 of 100 points read the container filesystem; only `d_evidence`'s 10 use the transcript) but
>   any transcript-based judge would silently score a truncated artifact.

**The mechanism, in the source.** `scripted_driver.py:80-82`:

```python
def capture_sid(out: str) -> str | None:
    m = re.search(r"Session ID:\s*([0-9a-f-]{8,})", out)
    return m.group(1) if m else None
```

and `scripted_driver.py:133-135`:

```python
    # continuity check: every turn after 1 should carry the SAME session id
    sids = [x["session_id"] for x in rec["turns"] if x["session_id"]]
    rec["session_continuity_ok"] = len(set(sids)) == 1 and len(sids) == len(rec["turns"])
```

Turn 1 prints `Session ID: <sid>`; every `--resume` turn prints `Resuming session: <sid>` instead.
So `sids` has exactly **1** element and `len(rec["turns"])` is **5** ⇒ `1 == 5` ⇒ **False, always,
by construction.** 8rugb's diagnosis is exactly right.

## §2 — Reproduced at $0 on a captured run

`20260906-8rugb/runs/A-anth-01` (full transcript: `evidence/repro-one-run.txt`, reproducible with
`evidence/reproduce_on_one_run.sh`):

```
--- 1. what the driver RECORDED
  session_continuity_ok : False
  root_session_id       : ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  turn1: done=True marker=DONE EXIT:0 session_id=ca74aafb-... out_len=158054
  turn2: done=True marker=DONE EXIT:0 session_id=None       out_len=16233
  turn3: done=True marker=DONE EXIT:0 session_id=None       out_len=6262
  turn4: done=True marker=DONE EXIT:0 session_id=None       out_len=33421
  turn5: done=True marker=DONE EXIT:0 session_id=None       out_len=6875

--- 2. what each turn ACTUALLY printed
  turn1: Session ID: ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  turn2: Resuming session: ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  turn3: Resuming session: ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  turn4: Resuming session: ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  turn5: Resuming session: ca74aafb-50f7-4d17-b1ef-b01f0c012a34

--- 3. what the CONTAINER's own session file says
  root session ca74aafb-50f7-4d17-b1ef-b01f0c012a34
  prompt:complete events: 5
```

Five turns, one session, five completions on disk — and a flag that says continuity failed.
**Confirmed across all 14 of 8rugb's runs**: flag False 14/14, root `prompt:complete` = 5 in 14/14,
turns_done = 5 in 14/14.

## §3 — Blast radius, enumerated (`evidence/blast-radius.txt`)

**Copies of the driver: 71**, all `md5 a5c14242df801eabe776e742724177da` — 1 canonical in the evals
repo + 70 in `hw-model-performance/lanes/*/evaluation/scenarios/s3/`.

**Capture roots that used it, and how the flag came out:**

| capture root | driver records | flag True | corrected check True |
|---|---|---|---|
| `20260830-dialin` | 18 | 0 | 18 |
| `20260901-rebaseline` | 16 | 0 | 14 |
| `20260901-threeknob` | 64 | 0 | 63 |
| `20260902-161-presets` | 19 | 0 | 19 |
| `20260902-j0u-knobrouting` | 10 | 0 | 10 |
| `20260902-ytg-presets-revision` | 8 | 0 | 8 |
| `20260903-h7n-knobanth` | 1 | 0 | 1 |
| `20260906-8rugb` | 14 | 0 | 14 |
| `20260906-otr-armb` | 1 | 0 | 1 |
| **total** | **151** | **0** | **148** |

The "corrected" column is produced by the **patched driver's own `continuity_ok`**, imported by path
and replayed over each run's real `turn*.out` — not by a second implementation of the same idea
(`evidence/replay_corpus_continuity.py`, output in `evidence/corpus-continuity-replay.txt`).

**Consumers of the flag (code/docs, capture dirs excluded) — 11 distinct, none of them a gate:**

```
WRITER   scenarios/s3/scripted_driver.py                        sets it                             (x71 copies)
DOC      scenarios/s3/RESULTS.md  "Honest caveats"              already calls it a REPORTING ARTIFACT (x71, 1 distinct)
REPORT   20260901-rebaseline/REPORT.md                          "reports continuity_ok=False falsely"
REPORT   20260901-threeknob/LEG-B-REPORT.md                     "Driver continuity false-negative"
ROW      20260901-threeknob/run_s3_cell.sh                      copies it into a row; does NOT gate
ROW+FIX  20260901-threeknob/remeasure_s3.sh                     renames it continuity_flag_driver AND computes resume_sid_consistent
PRINT    20260901-threeknob/summarize.py                        prints it; does NOT gate
FIX      20260906-8rugb/summarize_run.py                        ignores it; reads both phrasings + prompt:complete
DASH     _dashboard/campaign-data.md                            repeats the "reporting artifact" caveat
NOTES    ai-notes/00-what-we-know.md                            8rugb's paragraph (the claim under audit)
PROBE    probes/62pg-system-prompt-audit/FINDINGS.md            cites the field's PRESENCE, never its value
```

**`s5-crac` and `s7-retention-headroom` are NOT affected.** They carry the same `Session ID:` regex
but compute **no** continuity flag, and take the sid from **turn 1 only** — which does print
`Session ID:`. Their `--resume` targeting, grader `--root-sid`, and boundary/compaction counting are
all correct. Checked in source, not assumed.

## §4 — Every affected conclusion classified

**VOID: 0 · STANDS: 5 · NEEDS-RERUN: 0.**

| `00-what-we-know` section | verdict | reasoning |
|---|---|---|
| **(c)** three-knob frontier — 16 cells, 127 runs `[3K]` | **STANDS** | 63/64 continuous. The one break (`val-tk-sol-xhigh-s3-02`) is in the `sol-xhigh` S3 cell; dropping it leaves the cell median at **90 either way** (100/90/80 → 100/80), recomputed at $0. No headline claim in (c) rests on `sol-xhigh` S3 — the S3 Pareto is terra-medium / sonnet5-medium / haiku-high, and (c)'s `sol` counter-example is stated on **S1**. Honest residue: that cell's pass count moves **2/3 → 1/2**. |
| **(m)** knob-consistent preset ENGAGES at a MEDIUM anthropic root `[otr]` | **STANDS** | `h7n` 1/1 and `otr-armb` 1/1 continuous under the corrected check. 8rugb explicitly worried about `h7n`; it is clean. |
| **(p)** delegation-context split `[8rugb]` | **STANDS** | 14/14 continuous. The flag was false for **both arms equally**, so a relative comparison could never have depended on it. This is the `62pg` distinction applied: both arms equally affected ⇒ relative claim stands. There was no absolute claim resting on the flag to void. |
| `#55`'s basis, re-derived from `20260902-j0u-knobrouting/wire/` | **STANDS** | 10/10 continuous. |
| baselines: `rebaseline`, `dialin`, `161-presets`, `ytg` | **STANDS** | 18/18, 19/19, 8/8 continuous. `rebaseline`'s 2 exceptions are **TIMEOUTs** (`turns_done` 5→4 and 4→3), already excluded by every harness's `turns_done != 5` check — a different, already-handled invalidity. |

**Nothing is priced for re-run** because nothing needs one: the single genuine break was re-analysed
at **$0** and moves no published number. Had it moved one, the price would have been **1 run ×
~$4.94 = ~$4.94**.

**The second defect (empty turn stdout) is also real and also inert — and broader than reported.**
Corpus-wide: **6 runs / 10 turns**, every one **openai**. 8rugb named only `B-oai-01`; it actually
hit `A-oai-01` (t4,t5), `A-oai-02` (t4,t5), `A-oai-03` (t4), `B-oai-01` (t4,t5), `B-oai-02` (t4,t5)
and `threeknob/val-tk-sol-high-s3-03` (t4). It can only touch `d_evidence` — the single 10-point
dimension of 100 that reads the transcript (`grader.py:195-209`; a–c read the container filesystem).
**Every affected run scored `d_evidence` 10/10.** The 16 runs in the corpus that scored `d_evidence`
**0** all have full, non-empty transcripts (checked: `j0u` ×7, `threeknob` ×9) — a different cause,
not this one. **It has never cost a single point.** The exposure is forward-looking: any future
LLM-judge that reads `transcript.txt` would silently score a truncated artifact, on openai runs
preferentially — an **arm-asymmetric** risk if a future A/B splits by provider.

## §5 — The deciding question: did any lane ever ACT on the bad flag?

**No. Not once. The defect is REAL BUT INERT.**

Two independent proofs:

1. **By construction.** The flag is True in **0/151** records. A lane that gated on it would have
   discarded **100 %** of its runs and published nothing. All 9 capture roots published results.
2. **By the record.** The artifact was already documented — before 8rugb found it — in the S3
   scenario's own `RESULTS.md` "Honest caveats" (present in all 71 copies):
   *"**`continuity_ok=false` in the driver record is a reporting artifact, not a continuity
   failure.** … The flag is my regex expecting every turn's stdout to re-print the session id;
   `amplifier run --resume` doesn't."* — and again in `20260901-rebaseline/REPORT.md`
   (*"reports `continuity_ok=False` falsely"*) and `20260901-threeknob/LEG-B-REPORT.md`
   (*"Driver continuity false-negative … Reported as `resume_ok=✅`"*). Two harnesses independently
   routed around it: `remeasure_s3.sh` (2026-09-01) renamed it `continuity_flag_driver` and computed
   its own `resume_sid_consistent`; `8rugb`'s `summarize_run.py` (2026-09-06) matched both phrasings
   and cross-checked `prompt:complete`.

**But "inert" is not "harmless", and this is the finding that was not in 8rugb's report.**

`20260901-threeknob/runs/val-tk-sol-xhigh-s3-02`:

```
turn1: Session ID:       1f19b7ad-8e07-40a7-87a2-9c1513e95552
turn2: Resuming session: 1f19b7ad-8e07-40a7-87a2-9c1513e95552
turn3: Resuming session: 1f19b7ad-8e07-40a7-87a2-9c1513e95552
turn4: Resuming session: 1f19b7ad-8e07-40a7-87a2-9c1513e95552
turn5: Resuming session: 8839b22c-e8bf-4ae0-91b7-fe92a8d109d5   <-- DIFFERENT SESSION
root session 1f19b7ad...  prompt:complete events: 4             <-- not 5
```

Session `8839b22c` (`Messages: 87`, bundle `anchors-amp-dev`) **appears nowhere in the capture** —
only in `turn5.out` and `transcript.txt`. The pulled `sessions/` directory holds `1f19b7ad` and four
sub-agent dirs, and nothing else. **Turn 5's work landed in a session that was never captured**, and
the run was scored **90/100, pass=True**, and counted in the frontier.

**A flag that fires on every run cannot flag anything.** The defect's real cost was not the 151 valid
runs it "voided" — it voided none — but the **1 invalid run it hid**, at 0.66 % of the corpus. The
"voids 100 %" reading is refuted; the opposite reading is the true one, and it is smaller but
sharper.

## §6 — The fix, with a fail-before test

Shipped as lane artifacts (see §8 for why they are not applied in-place):

- `i0cm-scripted-driver-continuity.patch` — `git apply --check` **clean** against the pristine driver
  from the evals repo root (dry run only; nothing was written there).
- `test_scripted_driver_continuity.py` — 6 tests, driver loaded by path via `S3_SCRIPTED_DRIVER`,
  **skips** (never fails) when the driver is absent, so it is inert in this repo's CI.

The fix, in three parts:

1. `capture_sid` matches **both** phrasings (`Session ID:` **or** `Resuming session:`).
2. Continuity moves into a named `continuity_ok(turns)` function: same session across every
   **observed** turn, with an **empty** capture (`out_len == 0`) counted as *unobserved*, not as a
   break — while `turn_captures_empty` is added to `driver_record.json` and to the driver's stdout
   summary so it is **surfaced, never silently absorbed**.
3. A turn that produced output but **no** session line (a TIMEOUT stub) still reads as a break.

```
FAIL-BEFORE  — pristine driver, md5 a5c14242df801eabe776e742724177da
  FAILED  test_capture_sid_reads_resume_phrasing
  FAILED  test_continuity_true_for_a_real_five_turn_resume_run
  FAILED  test_continuity_survives_an_empty_turn_capture
  3 failed, 3 passed

PASS-AFTER   — same test, patch applied, md5 dc307c50090b11d981eee44382668431
  6 passed
```

(full transcript: `evidence/fail-before-pass-after.txt`)

**The two tests that pass in both states are load-bearing, not filler.**
`test_continuity_false_when_a_turn_ran_in_a_different_session` replays the real
`val-tk-sol-xhigh-s3-02` id sequence and `test_continuity_false_when_a_turn_never_ran` replays the
`rebaseline` TIMEOUT shape. Before the patch they pass **vacuously** (everything is False); after it
they pass **meaningfully**. They exist so the flag cannot be "fixed" by making it constant the other
way — which would be the same defect with the sign flipped, and would have hidden the one real break
just as thoroughly.

## §7 — Spend

| item | amount |
|---|---|
| API / LLM spend | **$0.00** |
| DTU spend | **$0.00** (no DTU created; nothing registered in `infra.tsv`; `infra_ledger.sh sweep` never run) |
| **Total against the $15.00 authority** | **$0.00** |

**Why $0 was enough, stated before any spend was considered.** The goal's authority is
`2 runs × 1 arm × ~$4.94 observed = ~$9.88, slack to $15` — it shows its arithmetic and it closes.
It was to be spent only if *"the $0 path genuinely cannot settle it"*, on a live 2-run repro. The $0
path settled every question:

- the defect is visible in the **source** (§1) — a live run cannot make it more true;
- it is visible in **151 captured records** (§3) — a 2-run repro would have added n=2 to n=151;
- the fix is demonstrated **fail-before / pass-after** against the real driver (§6);
- the blast-radius question is answered by **captured data plus grep** (§5), not by new runs.

Buying runs would have bought no evidence not already in hand. **Residue: $15.00, unspent, with
nothing it could have bought that would change a single line above.**

**Reported separately and NOT netted against the authority** (following `8rugb`'s convention, and for
the same reason — the authority's arithmetic is `launches × per-run price`, which structurally cannot
include the driving session): this lane's own driving session cost is **not measured**. It bought no
runs and created no infrastructure.

## §8 — Goal defect reported: the fix has no target inside the paths this lane owns

The goal's deliverable *"If real: fix the driver with a FAIL-BEFORE test"* **cannot be satisfied
inside this lane's worktree.** This lane's worktree is `amplifier-bundle-evaluation`
(`github.com/microsoft/amplifier-bundle-evaluation`, branch `lane/i0cm-harness-defect-audit`). The
driver lives in `/home/bkrabach/dev/openai-evals-team-ci` — a **different, remote-less** git repo —
and in 70 other lanes' worktrees. `amplifier-bundle-evaluation` contains **no** `scripted_driver.py`
and no `scenarios/` tree at all (`git ls-files | grep -c scripted_driver` → 0).

Per the goal's own instruction (*"If the only way to satisfy a deliverable is to write a file outside
your worktree … that is a DEFECT IN THIS GOAL, not a task. Report it against the goal, ship the patch
as an artifact under your ARTIFACT ROOT, and resolve"*) — that is exactly what was done:

- the fix ships as `i0cm-scripted-driver-continuity.patch`, verified `git apply --check` clean;
- the fail-before test ships as `test_scripted_driver_continuity.py`, demonstrated 3-fail → 6-pass;
- **no file outside this worktree was modified.** The evals repo, the shared
  `ai-notes/00-what-we-know.md`, and all 70 sibling lane worktrees are byte-untouched. Every
  `git apply` run against them used `--check` (dry run).

**What the manager must decide (not this lane):** whether to apply the patch to the canonical driver
only, or to refresh the 70 lane copies too. All 71 are currently byte-identical, so a canonical-only
fix breaks that invariant — which is worth knowing before choosing.

## §9 — Deviations and choices recorded

1. **The test lives under the lane artifact root, not `tests/`.** This repo's CI runs
   `pytest tests/ -q` and lints `src tests`; a test whose subject-under-test is a file in a different
   repo does not belong in this library's suite. It is written to **skip** when the driver is absent,
   so adding it to `tests/` later would be safe — but that is the manager's call, not a decision to
   smuggle in here.
2. **No re-scoring of `val-tk-sol-xhigh-s3-02` beyond its own cell.** The run is *reported* as a
   genuine break and its cell recomputed; it was not excised from `threeknob`'s published tables.
   Editing another lane's published capture analysis is outside this lane's paths (0rg hazard).
3. **The empty-capture case is tolerated by the continuity check but counted in a new field.**
   The alternative — treating an empty capture as a break — would have made the flag False for the
   6 openai-heavy runs and reintroduced an arm-asymmetric false alarm. Surfacing the count instead
   keeps the signal honest without inventing a failure.
4. **"Both arms equally affected ⇒ relative claim stands" is applied as `62pg` established it**, and
   is stated per conclusion in §4 rather than asserted once globally.
5. **The `8839b22c` session's *cause* is not diagnosed.** What is proven is what the artifacts show:
   turn 5 resumed a different id, the root carries 4 completions not 5, and that session is absent
   from the capture. Why the CLI resumed a different session is a separate question and is left open
   rather than guessed at.

## §10 — What remains open

- **Why did `val-tk-sol-xhigh-s3-02` turn 5 resume a different session?** The driver passes the
  turn-1 sid to every turn, so a different id in turn 5's output is unexplained by the driver alone.
  Worth one cheap probe — it may be a CLI `--resume` fallback path.
- **Are the 70 lane copies refreshed, or does the canonical fix stand alone?** Manager's call (§8).
- **The forward-looking exposure of defect 2**: any future transcript-reading LLM judge would score
  truncated artifacts on openai runs preferentially. Inert today; arm-asymmetric the moment a judge
  reads `transcript.txt`.
- **The empty-capture *cause*** (host-side `cat` of a large `t.out` returning nothing) is not fixed
  here — only made non-fatal to the continuity flag and visible in the record.

## Artifacts

```
docs/lanes/i0cm-harness-defect-audit/
├── DONE-NOTE.md                              (this file)
├── i0cm-00-what-we-know.diff                 proposed ai-notes diff — git apply --check clean
├── i0cm-scripted-driver-continuity.patch     the fix — git apply --check clean
├── test_scripted_driver_continuity.py        fail-before test (3 fail -> 6 pass)
└── evidence/
    ├── reproduce_on_one_run.sh               $0 single-run repro, read-only
    ├── repro-one-run.txt                     its output: A-anth-01 + the one real break
    ├── replay_corpus_continuity.py           replays the PATCHED logic over all 151 records
    ├── corpus-continuity-replay.txt          its output: 0/151 flag True, 148/151 corrected
    ├── fail-before-pass-after.txt            the test transcript, both driver md5s
    └── blast-radius.txt                      71 copies, 11 consumers, 9 capture roots
```

## Capture root

**None created.** This lane read existing captures only; it produced no new runs and no new capture
root. Primary source read:
`/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/` (77 roots, 9
of which carry S3 driver records).
