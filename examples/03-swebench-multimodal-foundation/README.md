# Example 03: SWE-bench Multimodal on foundation (library format)

Measures `amplifier-foundation`'s ability to resolve a single, pinned
[SWE-bench Multimodal](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Multimodal)
GitHub issue (dev split). Built on the `amplifier_evaluation` library: an
`agents/` + `tasks/` definition driven by the stock harness via the `amplifier-evaluation` CLI (`python -m amplifier_evaluation run`).

Type: off-the-shelf benchmark, single-variant, code-patch task, programmatic grading.

## What it measures

The agent (`amplifier-foundation`, installed from GitHub `@main`) edits a cloned
repo to fix the issue in one non-interactive turn. The grader extracts the patch
via `git diff` and runs the official `swebench` Docker harness, which applies the
patch plus the dataset's hidden `test_patch` and runs the project test suite.
Score: 1.0 (resolved) or 0.0 (unresolved). Resolved means every `FAIL_TO_PASS`
test passes AND every `PASS_TO_PASS` test still passes.

## Layout

```
03-swebench-multimodal-foundation/
  run.sh                       wrapper: sample instance -> set repo/commit vars -> dispatch
  agents/
    amplifier-foundation/      the system under test (meta/install/invocation/data)
  tasks/
    swebench/
      meta.yaml                name, difficulty, categories, timeout
      task.yaml                instructions (the solver prompt)
      profile.yaml             DTU profile; clones ${SWE_REPO} @ ${SWE_COMMIT} into /workspace/repo
      grader.yaml              runs the official swebench harness via swebench/grade.py
      workspace/               problem_statement.md staged at runtime
      grader-data/             instance.json (incl. gold/test patch) staged at runtime
  swebench/
    sample_swebench.py         host sampler (downloads the dataset, pins one instance)
    grade.py                   official-harness driver used by the grader
    PINNED_INSTANCE_ID         the pinned instance id
  results/<run-id>/            harness output (summary.json, trials/, ...)
```

The grader runs the swebench harness on the HOST (it needs the host Docker
daemon), launching it in the background and polling because a harness run can
take 5-20 minutes. `grade.py` and `grader-data/instance.json` are resolved
relative to the example directory (run.sh `cd`s there before dispatch).

## Prerequisites

- `amplifier-digital-twin`, `uv`, `python3`, `docker` on PATH; Docker running
  (used by BOTH the DTU and the swebench grader harness)
- `ANTHROPIC_API_KEY` (env or `~/.amplifier/keys.env`)
- `amplifier_evaluation` importable (activate the bundle `.venv`)

The dataset is open access (no `HF_TOKEN` needed).

## Run

```
./run.sh
```

The pinned instance id lives in `swebench/PINNED_INSTANCE_ID`. Delete it to
re-sample with the seed; otherwise subsequent runs reuse the same instance.

### Benchmark data is fetched at runtime, never committed

`run.sh` downloads the SWE-bench instance from HuggingFace at runtime (cached
under `~/.cache/amplifier-eval-swebench-mm/`) and writes it into
`tasks/swebench/workspace/` (`problem_statement.md`) and
`tasks/swebench/grader-data/` (`instance.json`, which holds the gold patch and
test_patch -- i.e. the answers). The repo itself is cloned inside the DTU by the
profile, and the grader pulls a per-instance Docker image. Those data directories
are gitignored except for their `.gitkeep`; only the task definitions, the
sampler, `grade.py`, and the pinned id are committed. Never commit the populated
contents.
