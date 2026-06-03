# 03-cli-run-benchmark

Meta-evaluation: when a user asks to run two of the CLI's **built-in**
amplifier-benchmark tasks against the `amplifier-foundation` agent **using the
`amplifier-evaluation` CLI**, does the `/evaluation` mode drive the CLI to run
them in parallel and produce result artifacts?

This also exercises a packaging property: the `amplifier-evaluation`
CLI/library must actually **ship** the built-in benchmark suite, so the agent
can run the tasks with no checkout and no `--tasks-dir`.

## What the agent under test sees

The same `amplifier-evalbundle` agent as the other meta-evals: an Amplifier
session with `amplifier-foundation` + `amplifier-bundle-evaluation` composed and
the `/evaluation` mode active. The user prompt (`task.yaml`) asks it to run two
built-in tasks for `amplifier-foundation`, in parallel, and write the output
under `/workspace/eval-output/benchmark-results`:

- `arxiv_conclusion_extraction`
- `cpsc_recall_monitor`

## Environment

`profile.yaml` is a DTU **host** (Incus + Docker), like
`01-evaluate-amplifier-bundle`, because the `amplifier-evaluation` harness
launches a nested DTU per benchmark task (two in parallel here). On top of that
infra the profile installs the CLI **from a built wheel** so the run exercises
the shipped package:

- clones `amplifier-bundle-evaluation` (redirected to the Gitea mirror),
- `uv build --wheel` -- the wheel force-includes the `amplifier-benchmark`
  suite at `amplifier_evaluation/benchmark/` (see `pyproject.toml`),
- `uv tool install <wheel> --with amplifier-foundation@git` -- `amplifier-core`
  from PyPI, `amplifier-foundation` from GitHub.

A readiness check confirms the installed CLI can resolve both built-in tasks
with no `--tasks-dir`.

## Grading

`grader.yaml` has a single check, `benchmark-produced-results`: a harness run
directory exists with result artifacts (`summary.json` / `run.json` + `trials/`)
recording the two trials (one per built-in task). A non-passing inner trial
still counts -- the bar is that results were **output**, not that the inner
agent succeeded.

## Run it

From the bundle root with the `.venv` active:

```bash
.amplifier/evaluations/run.sh 03
```

This is a nested-DTU run: outer host provisioning plus two inner benchmark
trials in parallel. Expect it to take a while.
