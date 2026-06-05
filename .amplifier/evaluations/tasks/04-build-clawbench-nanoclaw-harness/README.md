# 04-build-clawbench-nanoclaw-harness

Meta-evaluation of the `amplifier-bundle-evaluation` bundle: hand the
`/evaluation` mode a realistic "adapt an easy claw-bench task into a custom
harness that evaluates the nanoclaw-claude DTU profile" prompt, and measure
whether it builds a correct, working harness from scratch.

Where `01-evaluate-amplifier-bundle` only checks that *some* harness
artifacts exist, this task grades whether the mode gets the hard,
app-specific details right.

## The task (first user turn)

> Can you take a look at https://github.com/claw-bench/claw-bench and try to
> adapt one of the easy tasks into a custom harness that will evaluate
> /workspace/amplifier-app-nanoclaw/.amplifier/digital-twin-universe/profiles/nanoclaw-claude.yaml
> running in a DTU?
>
> Once it's built, run it end to end so we get a real evaluation result.
> Then, after the run comes back, create a "unique looking", self-contained
> HTML dashboard of those results.
>
> Put every file you produce under /workspace/eval-output/. ...

The full prompt is in `task.yaml`, with only the profile path pointed at
the in-DTU clone and the eval-output instruction added. The AIUser follows
up across turns when the agent returns early or asks for confirmation.

## What a passing harness does

There is no answer key in the environment -- the agent must build the
harness from scratch. A harness that earns full marks:

- vendors a real, easy claw-bench task (its `instruction.md`, its input
  data, and its original pytest `verifier/`) rather than re-implementing the
  checks by hand;
- launches the `nanoclaw-claude` DTU, seeds the task input into the nanoclaw
  agent's working directory (discovered at runtime, not hard-coded), drives
  the nanoclaw agent, and harvests the file it produces;
- detects completion by polling for that deliverable -- nanoclaw's chat
  client returns almost immediately, long before the agent finishes, so
  treating the chat call's return as "done" produces a wrong result;
- grades the harvested output by running claw-bench's own pytest verifier
  and computing its weighted score; and
- actually runs end to end against a fresh DTU (or a cleared workspace), so
  the score cannot be a false positive off a stale, leftover deliverable.

The grader's rubric checks for exactly these properties (see `grader.yaml`).

Beyond the harness, the scenario also asks the agent to run it and then, once
the results are back, produce a "unique looking", self-contained HTML
dashboard of those results -- the final rubric check covers that.

## What the grader checks

Five substantive checks. Build quality (the first three) carries 0.65, the
end-to-end run 0.20, and the results dashboard 0.15 -- so an
excellent-but-unexecuted harness still scores well, while a real run and a
dashboard of it are each rewarded. Weights sum to 1.0.

| Evaluation | Weight | Pass condition |
|---|---|---|
| vendored-clawbench-task | 0.20 | adapts a real claw-bench task, including its input data AND its original pytest verifier (weight markers), not a hand-rolled approximation |
| drives-nanoclaw-correctly | 0.25 | seeds input into and harvests the deliverable from the nanoclaw agent's workspace, and detects completion by polling for the produced file -- NOT by treating the chat call's return as completion |
| programmatic-grading | 0.20 | scores the harvested output with claw-bench's own pytest verifier (deterministic, weighted), not an ad-hoc re-implementation or an LLM judge |
| ran-end-to-end-trustworthy | 0.20 | actually launched a real nanoclaw-claude DTU, ran the harness, and produced a trustworthy score -- with a guard against grading a stale deliverable (fresh DTU / cleared workspace) |
| produced-results-dashboard | 0.15 | after the run, produced a self-contained HTML dashboard that accurately presents the real results with a deliberate, distinct visual design (not a generic template, raw dump, or placeholder numbers) |

These criteria encode the real pitfalls of this task: nanoclaw's chat
client returns long before the agent finishes (so naive completion
detection produces a wrong score), and a leftover deliverable in the agent
workspace can yield a false 100%. A harness that ignores these scores
lower -- which is the point.

## DTU shape

A DTU *host*: Ubuntu 24.04 with Incus + Docker + uv + tmux (the same
nested-DTU host stack as `01-evaluate-amplifier-bundle`), plus a clone of
`amplifier-app-nanoclaw` in `/workspace` so the `nanoclaw-claude.yaml`
profile the prompt references actually exists. The nested host lets the
agent launch a nanoclaw DTU and actually run the harness it builds.

claw-bench is intentionally **not** pre-cloned: fetching and exploring it
from GitHub is part of the task being graded.

> Feasibility note: the `ran-end-to-end-trustworthy` check requires the
> nanoclaw DTU to launch *inside* the eval DTU (nested Incus), and nanoclaw
> itself runs Docker inside that. That is deep nesting and may not succeed
> in all host environments; it is weighted as a stretch (0.2) for exactly
> this reason. The build-quality checks (0.8) do not require execution.

## How to run

From the bundle root:

```
.amplifier/evaluations/run.sh 04
```

The wrapper mirrors the current `EVAL_BUNDLE_REF` to the local Gitea
instance, threads `GITEA_URL` / `GITEA_TOKEN` / `EVAL_BUNDLE_REF` to the
harness, and the task's `profile.yaml` `url_rewrites:` resolves the bundle
to the user's local branch HEAD.

Typical wall time per trial is long: nested-DTU host provision + bundle
install + a continuous multi-turn build session + extraction + grading,
plus (if it gets there) an actual nanoclaw run. Budget up to ~90 minutes
(see `meta.yaml` timeout).
