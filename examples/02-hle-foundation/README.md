# Example 02: HLE on foundation (library format)

Measures `amplifier-foundation`'s correctness on a single, pinned
[Humanity's Last Exam](https://huggingface.co/datasets/cais/hle) (HLE) question.
Built on the `amplifier_evaluation` library: an `agents/` + `tasks/` definition
driven by the stock harness (`python -m amplifier_evaluation.harness.run`).

Type: off-the-shelf benchmark, single-variant capability measurement.

## What it measures

The agent (`amplifier-foundation`, installed from GitHub `@main`) answers the
pinned HLE question in one non-interactive turn, writing `answer.txt`. The
grader judges that answer against the dataset's ground-truth answer using HLE's
published judge criteria. Score: 1.0 (correct) or 0.0 (incorrect).

## Layout

```
02-hle-foundation/
  run.sh                       wrapper: sample pinned question -> dispatch harness
  agents/
    amplifier-foundation/      the system under test (meta/install/invocation/data)
  tasks/
    hle/
      meta.yaml                name, difficulty, categories, timeout
      task.yaml                instructions (the solver prompt)
      profile.yaml             DTU profile (ubuntu + uv + git)
      grader.yaml              HLE LLM-judge rubric (one criterion)
      workspace/               question.md (+ image) staged at runtime
      grader-data/             reference.json (ground truth) staged at runtime
  hle/
    sample_hle.py              host sampler (downloads cais/hle, pins one question)
    PINNED_SAMPLE_ID           the pinned question id
  results/<run-id>/            harness output (summary.json, trials/, ...)
```

The ground-truth answer is staged only into `grader-data/` (pushed to the grader
via `grader.yaml` `mounts:`), never into the solver's `workspace/`.

## Prerequisites

- `amplifier-digital-twin`, `uv`, `python3`, `docker` on PATH; Docker running
- `ANTHROPIC_API_KEY` (env or `~/.amplifier/keys.env`)
- `HF_TOKEN` (env or `~/.amplifier/keys.env`) -- cais/hle is gated
- `amplifier_evaluation` importable (activate the bundle `.venv`)

## Run

```
./run.sh
```

The pinned question id lives in `hle/PINNED_SAMPLE_ID`. Delete it to re-sample
with the seed; otherwise subsequent runs reuse the same question.

### Benchmark data is fetched at runtime, never committed

`run.sh` downloads the HLE question from HuggingFace at runtime (cached under
`~/.cache/amplifier-eval-hle/`) and writes it into `tasks/hle/workspace/`
(`question.md`, image) and `tasks/hle/grader-data/` (`reference.json`, the
ground-truth answer). Those directories are gitignored except for their
`.gitkeep`; only the task definitions, the sampler, and the pinned id are
committed. cais/hle is a gated dataset, so set `HF_TOKEN` and never commit the
populated contents.

## Evaluating local foundation changes

This example installs foundation from GitHub `@main`. To test local changes,
add a Gitea mirror + `url_rewrites` to `tasks/hle/profile.yaml` and thread
`GITEA_URL` / `GITEA_TOKEN` launch variables, as in example 01-explorer-removal.
