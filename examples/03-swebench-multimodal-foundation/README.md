# Example 03: Amplifier Foundation on SWE-bench Multimodal

A worked example measuring Amplifier foundation's ability to resolve a single, pinned issue from [SWE-bench Multimodal](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Multimodal) (dev split, 102 instances, all JavaScript repos).

Same overall shape as example 02, but the grading mechanism is fundamentally different: code patch judged programmatically by the official `swebench` harness (Docker test runner) on the host, not by an LLM judge.

## What "resolved" means

The harness runs two test sets against the agent's patch:

- **Fix-verification tests** (`FAIL_TO_PASS` in SWE-bench terms): tests that came with the original PR's `test_patch`. They fail on the base commit and must pass after the fix. These prove the agent actually addressed the bug.
- **Regression tests** (`PASS_TO_PASS` in SWE-bench terms): tests that were already passing before the fix. They must still pass to prove the agent's patch did not break unrelated functionality.

"Resolved" means **both sets pass entirely**. One failing fix-verification test or one broken regression test counts as unresolved.

## Target of evaluation

`amplifier-foundation @ main` (off-the-shelf) running a single SWE-bench Multimodal instance inside a Digital Twin Universe. The repo is cloned at `base_commit` into `/work/swe-task/repo/`, `problem_statement.md` is staged next to it, the agent edits files to fix the issue, and the resulting `git diff` is fed to the official harness for grading.

## Instance selection

Pinned by id in `swebench/PINNED_INSTANCE_ID`. We ship a curated default (`chartjs__Chart.js-10301`, a 2-line legend onLeave fix with 1 FAIL_TO_PASS test) so the first run is fast. SWE-bench instances vary 100x in test-suite size, so we curate instead of randomizing. Delete the file to re-sample with seed=42; write a specific id into it to override.

## Setup

```
Foundation:    git+https://github.com/microsoft/amplifier-foundation@main
Sample source: SWE-bench/SWE-bench_Multimodal parquet (open access, no token)
Grader:        swebench.harness.run_evaluation on the host (Docker-based)
Sample count:  1
```

Solver prompt: see `swebench/prompts.py` — agent edits in `/work/swe-task/repo/`, must not commit, may fetch issue images but not search for the fixing PR.

## How to run

```
./run.sh
```

Samples (or reuses the pin), launches the DTU, clones the repo at `base_commit`, runs the agent, pulls the patch via `git diff`, grades via the host-side harness, writes `meta.json` and `verdict-{resolved|unresolved}.md`.

## How to read results

**Start here:** `verdict-resolved.md` or `verdict-unresolved.md` at the run root — outcome, patch shape, FAIL_TO_PASS/PASS_TO_PASS results, session sizes, timings. Filename signals the verdict.

```
results/<date>/run-1/
  verdict-{resolved|unresolved}.md   rendered summary — start here
  meta.json                          pinned id, SHAs, wall times, verdict
  sample/{instance.json, problem_statement.md}
  solver/{patch.diff, stdout.txt, sessions/sessions/<sid>/{events,transcript}.jsonl}
  grader/{verdict.json, predictions.jsonl, harness_stdout.txt, harness_report.json, summary.json}
```

```
python3 metrics/extract_metrics.py results/<date>/run-1/
python3 metrics/summarize_run.py   results/<date>/run-1/
```

## Shortcuts taken (v1)

- **No Gitea.** Foundation installed straight from GitHub @main. Copy the Gitea block from `01-explorer-removal/run.sh` to evaluate local foundation changes.
- **Curated pin, not seed=42.** SWE-bench instances cost vary 100x; shipping a small fast default keeps the first run sane.
- **Dev split only.** Public test patches grade locally. The 510-instance test split requires submission to swebench.com.
- **`setsid` + sentinel + poll for the solver.** `amplifier-digital-twin exec` has a hard 600s timeout; real SWE-bench attempts run 5–30 min. Per the 20260512 learnings doc.

## Prerequisites

`amplifier-digital-twin`, `amplifier`, `uv`, `git`, `docker` on PATH; Docker running (used by both the DTU and the host-side swebench harness); `ANTHROPIC_API_KEY` in env or `~/.amplifier/keys.env`. The `swebench` package is installed on demand via `uv run --with swebench`.

Typical wall time: ~5 min on the default pin (3.5 min solver + 1.5 min grader). First run pulls a ~2GB Docker image for the grader.
