# Example 04: Foundation vs Amplifier-dev demo (library format)

End-to-end demo of the evaluation bundle in the `amplifier_evaluation` library
format: 3 HLE tasks + 3 SWE-bench Multimodal tasks, each run against TWO agent
variants (`amplifier-foundation` and `amplifier-dev`) for 12 total trials,
dispatched through the stock harness with a parallelism cap.

Type: multi-task, two-variant demo, mixed judge + programmatic grading.

## What it measures

- Variant `amplifier-foundation`: `amplifier-foundation @ main`
- Variant `amplifier-dev`: the `amplifier-dev` bundle (`foundation` + the
  `amplifier-dev` behavior + `amplifier-tester` + `bundle-design` context)

Both variants pin Opus via the `opus48` routing matrix, so the only difference
between them is the composed bundle, not the model. (The original demo pinned
`opus47`; `opus48` is the current matrix.)

For each (variant, task):
- HLE tasks reuse example 02's task shape (LLM-judge grading: `correct`).
- SWE-bench tasks reuse example 03's task shape (official swebench Docker
  harness: `resolved`).

## Layout

```
04-foundation-vs-dev-demo/
  run.sh                    wrapper: sample 6 tasks -> dispatch 12 (agent, task) pairs
  agents/
    amplifier-foundation/   variant 1 (opus48-pinned)
    amplifier-dev/          variant 2 (foundation + amplifier-dev bundle, opus48-pinned)
  tasks/
    hle-1/ hle-2/ hle-3/             HLE tasks (example 02 shape)
    swebench-1/ swebench-2/ swebench-3/   SWE-bench tasks (example 03 shape)
  hle/        sample_hle.py, PINNED_SAMPLE_IDS (3 ids)
  swebench/   sample_swebench.py, grade.py, PINNED_INSTANCE_IDS (3 ids)
  results/<run-id>/   harness output (summary.json, trials/, ...)
```

Each `swebench-N` task profile clones its repo via per-index launch variables
(`${SWE_REPO_N}` / `${SWE_COMMIT_N}`) that run.sh sets from the sampled instance,
so all three SWE tasks can run in one harness invocation.

## Prerequisites

- `amplifier-digital-twin`, `uv`, `python3`, `docker` on PATH; Docker running
- `ANTHROPIC_API_KEY` and `HF_TOKEN` (env or `~/.amplifier/keys.env`)
- `amplifier_evaluation` importable (activate the bundle `.venv`)

## Run

```
./run.sh
```

`MAX_PARALLEL` (default 3) caps concurrent trials. 12 trials with SWE-bench
grading is Docker-heavy; 3 is a reasonable default on a developer machine.
Delete the `PINNED_*` files to re-sample with the seed.

### Benchmark data is fetched at runtime, never committed

`run.sh` downloads the 3 HLE questions and 3 SWE-bench instances from HuggingFace
at runtime (cached under `~/.cache/`) and writes them into each task's
`workspace/` (`question.md` / `problem_statement.md`) and `grader-data/`
(`reference.json` / `instance.json`, which hold the answers). Those directories
are gitignored except for their `.gitkeep`; only the task definitions, the
samplers, `grade.py`, and the pinned ids are committed. cais/hle is gated, so set
`HF_TOKEN` and never commit the populated contents.
