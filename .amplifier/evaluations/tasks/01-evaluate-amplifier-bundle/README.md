# 01-evaluate-amplifier-bundle

Meta-evaluation of the `amplifier-bundle-evaluation` bundle: hand the
`/evaluation` mode a realistic "I have a new bundle, help me validate it"
prompt, and check whether it produces a usable evaluation harness.

## Inner artifact

`workspace/amplifier-bundle-crusty-reminder/` is a thin foundation
wrapper that adds one hook reminding the agent to consult
`crusty-old-engineer` after implementation work. The harness pushes this
to `/workspace/amplifier-bundle-crusty-reminder/` inside the DTU before
the agent starts.

## Prompt (first user turn)

> I have a new bundle at /workspace/amplifier-bundle-crusty-reminder.
> I want to validate that it behaves as intended. Help me set up an
> evaluation.
>
> Put every file you produce under /workspace/eval-output/. This
> includes scenario writeups, DTU profiles, runner scripts, and any
> notes.

The full prompt is in `task.yaml`. The AIUser follows up across turns
when the agent returns early or asks for confirmation.

## What the grader checks (v2, substantive)

Three bigger checks on what the `/evaluation` mode actually produced.
Basic liveness signals (reached eval mode, session completed, "wrote some
file") were dropped: they fail any broken run and say nothing about
evaluation quality. Weights sum to 1.0.

| Evaluation | Pass condition |
|---|---|
| created-dtu-profile | at least one real DTU profile under eval-output (a YAML defining an isolated environment: base image + provisioning) |
| created-evaluation-task | at least one concrete evaluation task: a scenario with a specific input AND a measurable success criterion |
| created-run-script | a script (run.sh or a Python runner) that actually executes the evaluation end to end |

Out of scope: quality scoring of the produced artifacts, LLM-as-judge for
design choices, A/B comparison.

## DTU shape

A DTU *host*: Ubuntu 24.04 with Incus + Docker + uv + tmux, so the agent
under test can launch nested DTUs (DTU-in-DTU) and actually **run** the
evaluation it designs, not just write files. The Incus host stack is
adapted from amplifier-bundle-digital-twin-universe's
`dtu-host-in-incus.yaml`. The profile installs the OS infra; the agent's
`install.yaml` adds the amplifier-digital-twin / amplifier-gitea CLIs and
bundles on top. Expect longer provisioning than a lean profile.

## How to run

From the bundle root:

```
.amplifier/evaluations/run.sh 01
```

The wrapper mirrors the current `EVAL_BUNDLE_REF` to the local Gitea
instance, threads `GITEA_URL` / `GITEA_TOKEN` / `EVAL_BUNDLE_REF` to the
harness, and the task's `profile.yaml` `url_rewrites:` resolves the
bundle to the user's local branch HEAD.

Typical wall time per trial: 15 to 30 min (DTU provision + bundle
install + a continuous multi-turn agent session driven via a persistent
tmux TUI + extraction + grading).
