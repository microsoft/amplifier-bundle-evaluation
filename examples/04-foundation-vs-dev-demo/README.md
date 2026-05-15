# Example 04: Foundation vs Amplifier Dev demo

End-to-end demo of the evaluation bundle: 3 HLE tasks and 3 SWE-bench
tasks (Multimodal by default, or Verified via `AMPLIFIER_DEMO_SWE_DATASET`),
each run against TWO bundle variants (`foundation` and `amplifier-dev`)
for 12 total runs. Jobs run in parallel with a configurable concurrency
cap (default 5 DTUs at once). A single self-contained HTML report
aggregates the results.

## What this measures

- Variant `foundation`: `amplifier-foundation@main`
- Variant `amplifier-dev`: the `amplifier-dev` bundle (`foundation` +
  `amplifier-dev` behavior + `amplifier-tester` + `bundle-design` context)

For each (variant, benchmark, task) combination:

- HLE: solver runs in DTU; answer judged by a fresh `amplifier run` on the
  host using HLE's reference judge prompt. Outcome: `correct` (true/false).
- SWE-bench (Multimodal dev split by default, Verified test split via
  `AMPLIFIER_DEMO_SWE_DATASET=verified`): solver edits the repo in the
  DTU; patch extracted via `git diff` and graded by the official
  `swebench.harness.run_evaluation` on the host. Outcome: `resolved`
  (true/false). Multimodal is JavaScript with image assets and requires
  strong vision capabilities; Verified is Python and a broader code-fix
  signal. Either is a reasonable choice.

## Prerequisites

- `amplifier-digital-twin`, `amplifier`, `uv`, `git` on PATH
- Docker daemon running (both the DTU and the SWE-bench grader use Docker)
- `ANTHROPIC_API_KEY` (env or `~/.amplifier/keys.env`)
- `HF_TOKEN` (env or `~/.amplifier/keys.env`) - cais/hle is gated

## Run

```
./run.sh
```

The runner takes 60-180 minutes wall time depending on host load and how
long SWE-bench harness Docker pulls take on first run.

### Environment overrides

```
AMPLIFIER_DEMO_MAX_PARALLEL=5         # max concurrent DTUs (default 5)
AMPLIFIER_DEMO_NUM_HLE=3              # number of HLE tasks (default 3)
AMPLIFIER_DEMO_NUM_SWE=3              # number of SWE-bench tasks (default 3)
AMPLIFIER_DEMO_SEED=42                # random seed for task selection
AMPLIFIER_DEMO_SWE_DATASET=multimodal # 'multimodal' (JS, image-heavy, needs
                                      # strong vision) or 'verified' (Python,
                                      # broader code-fix signal). Default
                                      # 'multimodal'.
```

### Pinning the task set

The samplers write the chosen task ids to:

```
hle/PINNED_SAMPLE_IDS
swebench/PINNED_INSTANCE_IDS
```

Delete those files to re-sample with the seed; otherwise subsequent runs
reuse the same task set.

## Layout

```
04-foundation-vs-dev-demo/
  README.md
  run.sh                              # parallel orchestrator
  scripts/run_one_job.sh              # per-job worker (one variant+bench+task)
  profiles/
    foundation.yaml                   # DTU profile for the foundation variant
    amplifier-dev.yaml                # DTU profile for the amplifier-dev variant
  hle/
    sample_hle.py                     # multi-task host sampler (N tasks at once)
    prompts.py                        # solver + judge prompts (same as example 02)
    judge.py                          # single-task judge (called per-job)
    PINNED_SAMPLE_IDS                 # written on first run
  swebench/
    sample_swebench.py                # multi-instance host sampler
    prompts.py                        # solver prompt (same as example 03)
    grade.py                          # single-instance grader (called per-job)
    PINNED_INSTANCE_IDS               # written on first run
  metrics/
    extract_metrics.py                # JSON shaper (handles both benchmarks)
    build_html_report.py              # self-contained HTML aggregator
  results/<date>/
    _samples/{hle,swebench}/task-N/   # samples shared across both variants
    _logs/                            # per-job log files + jobs.txt
    {foundation,amplifier-dev}/
      {hle,swebench}/
        task-N/run-1/
          meta.json
          sample/                     # per-job copy or symlink of the sample
          solver/
            answer.txt OR patch.diff
            stdout.txt
            sessions/sessions/<sid>/  # events.jsonl, transcript.jsonl
          judge/ OR grader/
            verdict.json
    report.html                       # the aggregated report
```

## Notes

- Each job gets its own DTU (12 DTUs total). DTUs are destroyed at the end
  of each job to free Docker resources.
- The solver uses the `setsid` + sentinel + poll pattern for both HLE and
  SWE-bench tasks so jobs survive past the `amplifier-digital-twin exec`
  600s hard timeout. HLE caps at 20 min, SWE-bench at 45 min.
- The SWE-bench harness runs on the host (not in the DTU) and uses Docker
  to apply the patch and run the project's test suite. Running 5
  graders in parallel is heavy on the Docker daemon and may slow first-run
  image pulls.
- The HTML report (`results/<date>/report.html`) is self-contained with
  inlined CSS, so it can be opened directly or attached to a message.