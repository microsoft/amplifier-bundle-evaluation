# 02-industry-benchmark-routing

Meta-evaluation of the `amplifier-bundle-evaluation` bundle: does the
`/evaluation` mode route a broad model-swap validation question to the
amplifier-benchmark suite (starting with a small ~5 task sample) instead of
suggesting custom one-off tasks?

## Prompt (single user turn)

> /evaluation I am testing changes to Amplifier CLI where I am setting the
> default model from Opus 4.8 to gpt-5.5. How could I validate these changes?
> Don't actually do anything just give me the plan

This is a broad regression/comparison question (a default-model swap, not
tied to any one workflow). The desired behavior is to propose validating
with amplifier-benchmark, starting with about ~5 tasks, and to NOT propose
inventing custom one-off tasks.

## What the grader checks

| Evaluation | Weight | Type | Criteria |
|---|---|---|---|
| recommends-amplifier-benchmark | 0.7 | semantic | P1 recommends amplifier-benchmark; P2 proposes starting with ~5 tasks |
| avoids-custom-tasks | 0.3 | semantic | N1 does NOT suggest creating custom one-off tasks/scenarios |

Both evals score strictly against the solver's final assistant text.

## How to run

From the bundle root, via the wrapper:

```
.amplifier/evaluations/run.sh
```

The wrapper discovers the running `amplifier-gitea` instance and deploys the
local branch HEAD into the mirror AS the `main` branch, then threads
`GITEA_URL` + `GITEA_TOKEN` to the harness via `--launch-var`. The DTU
profile's `url_rewrites:` block redirects clones of
`github.com/microsoft/amplifier-bundle-evaluation` to that mirror, so the
agent under test composes the user's local changes exactly as if they were
the deployed, active `main` branch.

Deploying as `main` (rather than a feature branch) is required: Amplifier
re-resolves app bundles at session start by cloning the default branch. If
the mirror only carried a feature branch, that clone fails and the
`/evaluation` mode silently disappears from the composed session.
