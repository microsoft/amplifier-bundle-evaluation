# Evaluations

Bundle-internal meta-evaluations for `amplifier-bundle-evaluation`. These
dogfood the bundle on itself by running it through the `amplifier_evaluation`
harness (shipped in this same bundle, under `src/amplifier_evaluation/`).
User-facing templates live in `examples/`; agent task benchmarks live in
`amplifier-benchmark/`. This directory is just the bundle's own QA suite.

## Layout

```
.amplifier/evaluations/
  run.sh                       wrapper: gitea + harness dispatch
  agents/
    amplifier-evalbundle/      foundation + evaluation
                               (shared by both evals; the bundle under test)
  tasks/
    01-evaluate-amplifier-bundle/
    02-industry-benchmark-routing/
  results/<run-id>/            harness output (gitignored)
```

## Evaluations

| Id | What it checks |
|---|---|
| 01-evaluate-amplifier-bundle | `/evaluation` mode scaffolds a usable harness when handed a new Amplifier bundle |
| 02-industry-benchmark-routing | `/evaluation` mode routes a broad model-swap validation question to the amplifier-benchmark suite (starting with ~5 tasks) instead of suggesting custom one-off tasks |

Both evals exercise the same agent: an amplifier session with
`amplifier-foundation` and `amplifier-bundle-evaluation` composed. They
differ only in prompt, profile, and grader. See each task's `README.md`.

## How to run

From the bundle root, with the bundle's `.venv` active (so the local
editable `amplifier_evaluation` install is on `sys.path`):

```bash
source .venv/bin/activate
.amplifier/evaluations/run.sh           # both evals
.amplifier/evaluations/run.sh 02        # one eval by id prefix
EVAL_BUNDLE_REF=some-branch .amplifier/evaluations/run.sh 02
```

The wrapper discovers a running `amplifier-gitea` instance and deploys the
local ref `EVAL_BUNDLE_REF` (default: the currently checked-out branch)
into the mirror AS the `main` branch, then threads `GITEA_URL`,
`GITEA_TOKEN`, and `EVAL_BUNDLE_REF` to every trial via the harness
`--launch-var` flag. Each task's `profile.yaml` uses `${GITEA_URL}` /
`${GITEA_TOKEN}` in `url_rewrites:` so clones of
`github.com/microsoft/amplifier-bundle-evaluation` resolve to the local
Gitea mirror.

Deploying the local HEAD as `main` simulates the changes being merged and
active. It is also required: Amplifier re-resolves app bundles at session
start by cloning the default branch, so a mirror that only carried a
feature branch would fail that clone and drop `/evaluation` mode. Once the
bundle is public on GitHub, the Gitea mirror becomes optional.

## Direct harness invocation

If you want to bypass the wrapper (no Gitea, or testing a different
combination), invoke the harness directly. Eval 02 (and eval 01 while it
still pulls the bundle from a non-main ref) requires `${GITEA_URL}` and
`${GITEA_TOKEN}` set, but otherwise the harness has no special
dependency.

```bash
python3 -m amplifier_evaluation.harness.run \
    --agents .amplifier/evaluations/agents \
    --tasks  .amplifier/evaluations/tasks \
    --pair   amplifier-evalbundle:02-industry-benchmark-routing \
    --output .amplifier/evaluations/results/$(date -u +%Y%m%dT%H%M%SZ) \
    --launch-var GITEA_URL=http://localhost:10110 \
    --launch-var GITEA_TOKEN=<token> \
    --launch-var EVAL_BUNDLE_REF=feat/v2-integration
```

## Where results land

`results/<run-id>/` per-run:

- `run.json`     -- run plan, selection, launch_variables (secrets redacted)
- `summary.json` -- per-trial state, score, elapsed
- `harness.log`  -- full INFO-level harness log
- `trials/<trial-id>/state.json`  -- per-stage history
- `trials/<trial-id>/grader/`     -- grader artifacts: per-evaluation
                                     `initial_report.md` and `rubric.json`
                                     plus a `grader_result.json` summary
- `trials/<trial-id>/extraction/` -- pulled session files (events.jsonl,
                                     transcript.jsonl, metadata.json)
- `trials/<trial-id>/ai_user.json` -- the AIUser's conclude verdict and
                                      summary of what it saw
