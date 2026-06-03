# Example 01: Foundation Explorer Agent Removal

Measures what the `foundation:explorer` agent contributes by running the same
exploration task against `amplifier-foundation` WITH and WITHOUT the explorer,
then comparing token cost (root and total) and answer quality.

The focus of this eval is the metric comparison (`compare.py`): how the explorer
shifts token usage between the root session and a delegated sub-session. The
grader is a lightweight guardrail -- it only confirms answer quality did not
collapse when the explorer was removed; it is not the headline result.

This example is built on the `amplifier_evaluation` library (the agents/tasks
contract + the lower-level harness building blocks). It is the reference shape
for a comparative (A/B) eval.

## Hypothesis

The explorer is a context sink. With it, the root session delegates exploration
to a sub-session and stays lean; without it, the root does the work inline and
its context balloons. Removing the explorer should inflate root-context tokens
and tool calls while answer quality holds roughly steady (faster wall clock is
not the win).

## How it works

The independent variable is the foundation build. Two independent Gitea mirror
repos are stood up, each carrying its state on `main`:

- `amplifier-foundation-with-explorer` -- foundation as-is
- `amplifier-foundation-without-explorer` -- explorer agent + every
  delegation-guidance reference to it removed (see `change.md`)

Two separate repos (not two branches of one repo) so the arms never conflict
and both resolve under Amplifier's default-branch re-resolution at session
start. The shared task profile redirects the foundation clone to one repo or
the other per trial via the `FOUNDATION_REPO` launch variable.

```
run.sh
  -> ensures a Gitea instance + the two foundation mirror repos
  -> harness.py  (custom A/B harness)
       -> one trial per variant via amplifier_evaluation building blocks:
          launch DTU -> install agent -> AIUser runs the prompt
          -> Extractor pulls the session artifacts -> Grader scores quality
       -> compare.py reads both trials' session events.jsonl and writes
          the A/B metric comparison (root context and total)
```

## Layout

```
agents/amplifier-foundation/   the system under test (install + drive + extract)
tasks/01-explorer-context-sink/  the prompt, DTU profile, and quality grader
harness.py    custom A/B harness (two trials of one agent x one task)
compare.py    metric comparator: root and total tokens, tools, delegations, citations
visualize.py  renders a self-contained report.html from a run
run.sh        wrapper: gitea mirrors + harness dispatch
change.md     the exact explorer-removal edits
```

## Run

```bash
cd examples/01-explorer-removal
./run.sh
```

Prerequisites: `amplifier-digital-twin`, `amplifier-gitea`, `git`, `python3`,
`docker` on PATH; Docker running; `ANTHROPIC_API_KEY` set (or in
`~/.amplifier/keys.env`); `amplifier_evaluation` importable (the bundle `.venv`
is auto-activated). To test a local foundation checkout instead of upstream,
set `FOUNDATION_GIT=/path/to/amplifier-foundation`.

## Output

Each run writes `results/<UTC-timestamp>/`:

```
with-explorer/     per-trial state.json, ai_user.json, extraction/, grader/
without-explorer/  same, for the explorer-removed arm
comparison.md      A/B metric diff (the headline result)
comparison.json    machine-readable metrics for both arms + the diff
report.html        self-contained visual report (run `python visualize.py`)
summary.json       per-trial state + grader answer-quality score
```

`comparison.md` reports two token views per arm -- ROOT context (the
context-sink benefit: how lean the root stays) and TOTAL across root +
sub-sessions (the real compute cost) -- plus root tool calls, delegations, and
file:line citations, each with without/with ratios. `visualize.py` renders the
same data as `report.html`.

The grader (`tasks/.../grader.yaml`) is the secondary guardrail, not the
headline: it only checks the answer still identifies the provider abstraction,
explains the switching mechanism, and cites real code, so a token shift can be
read against any quality change.
