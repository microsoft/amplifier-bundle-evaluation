# Harness Automation

Once a scenario is decided, wrap it in an automation so anyone can run it, re-run it, and get comparable results. The goal is a single script (per scenario) that stands up a fresh environment, runs the scenario, captures everything needed for analysis, and tears down cleanly. If necessary, later steps can consolidate scenarios into one script or come up with smarter ways to speed it up. Also, note that some of these steps are specific to Amplifier - adjust as needed.

Use `@evaluation:examples/01-explorer-removal/` as the prescribed template. It is a working comparison evaluation (foundation with vs without the `foundation:explorer` agent), and every new scenario should start by copying its structure.

## Directory layout

```
evaluations/<NN-short-name>/
  README.md          # What this scenario evaluates and why
  change.md          # (Comparison only) what changes between before and after
  profiles/
    before.yaml      # DTU profile for the baseline (single profile if not A/B)
    after.yaml       # DTU profile for the variant
  run.sh             # Runner: preflight, launch, run, capture
  metrics/
    extract_metrics.py   # Pulls structured metrics from a captured run
    summarize_run.py     # Renders a per-run markdown summary at the run root
  results/
    <YYYY-MM-DD>/
      report.md            # (Optional) summary
      before/run-1/
        meta.json
        stdout.txt
        sessions/sessions/<session_id>/events.jsonl
        sessions/sessions/<session_id>/transcript.jsonl
        analysis/            # (Optional) Post-run analyzer's narrative + classification
        verdict-{outcome}.md # Rendered markdown summary — start here
      after/run-1/
        (same shape)
```

Keep the `results/` shape identical across scenarios. That way the same metrics extraction script (or any downstream analysis) works against any run directory without modification.

## Treat `results/` as potentially sensitive

A `results/` directory captures `events.jsonl`, `transcript.jsonl`, `stdout.txt`, `meta.json`, and any analyzer output. These can contain provider keys (if a key ever leaks into a log line or event payload), full prompts and responses (which may include private repo content or user-specific data), absolute host paths, and the agent's complete reasoning trace. Never commit them.

This bundle's `.gitignore` already covers `examples/*/results/` and `.amplifier/evaluations/*/results/` so any scenario added under those paths is safe by default. When adding a scenario in a different repo, do ONE of the following before the first run:

- Add a matching pattern to that repo's `.gitignore` (e.g. `results/` or `evaluations/*/results/`), OR
- Point the runner at a path outside the repo entirely, such as `~/.cache/amplifier-eval/<scenario>/<date>/`, and pass that path into the scenario's metrics scripts as an argument.

Sanity check before any commit: `git status` should never list files under a `results/` path. If it does, stop and update `.gitignore` before staging anything.

## The DTU profile

The profile is the source of truth for the environment. At a minimum it includes:

- Base image (`ubuntu:24.04` is a safe default)
- `url_rewrites` redirecting any repos the scenario depends on to your local Gitea mirror, so you can pin specific branches or work-in-progress code
- `passthrough` for any provider keys the agent will need (`ANTHROPIC_API_KEY`, etc.)
- `provision.setup_cmds` that install the CLI, configure providers, add the required bundles, and clone any target repos the scenario operates on
- `readiness` checks that prove the environment is actually usable before the scenario runs

For comparison evaluations, the before and after profiles should differ in exactly one dimension. In example 01 that is the foundation branch (`@main` vs `@remove-explorer`). Everything else (CLI version, other bundles, target repo, provider config) is identical.

Pass secrets like `GITEA_TOKEN` at launch time via `--var ...`, never baked into the profile.

## The runner script

`run.sh` orchestrates the full lifecycle. The example follows this shape:

1. **Preflight.** Verify required tools are on PATH (`amplifier-gitea`, `amplifier-digital-twin`, `gh`, `git`, `docker`) and that the provider key is set. Fail loudly if anything is missing.
2. **Reuse or create the Gitea instance.** Start a stopped container if one already exists, otherwise create one. Capture its id, port, and token.
3. **Mirror the upstream repos** the scenario depends on to Gitea. Skip if already mirrored.
4. **Build any custom branches** the scenario needs (e.g. the "after" branch with the local change applied). Do this in a throwaway clone of the Gitea mirror. Never touch the user's workspace submodules.
5. **For each variant**:
   - Destroy any prior DTU with the same name (idempotent re-runs)
   - Launch the DTU from its profile, passing `GITEA_URL` and `GITEA_TOKEN` as vars
   - Time the scenario and run it (`amplifier-digital-twin exec ... -- amplifier run "<prompt>"`)
   - Extract the session id from stdout, then `file-pull` the session directory out of the DTU
   - Write a `meta.json` capturing wall time, exit code, prompt, repo SHAs, and pointers to session files

Make the runner idempotent. Re-running on the same day either replaces or extends `results/<date>/`. On a new day it creates a fresh directory.

## What to capture per run

A run is the unit of replayable evidence. Capture enough that six months from now you (or any downstream consumer) can reconstruct what happened without re-running.

The guidance here is deliberately generic — most of what you capture is the same whether you are evaluating an Amplifier session, a script, a third party agent, or a CLI tool.

### Minimum artifacts

- `meta.json` — the structured record of the run (fields below)
- `stdout.txt` — the full output as the user would see it
- Full execution record. *Amplifier:* `sessions/sessions/<session_id>/events.jsonl` + `transcript.jsonl`. *Generic:* whatever your system emits — logs, traces, transcripts, structured events.

### Fields in `meta.json`

- **`scenario_description`** — the plain-English description of what this run tests. *Generic:* "the goal of this run, in one sentence." *Amplifier:* often the eval mode name plus a short version of the prompt.
- **`prompt`** — the verbatim input handed to the system under test, byte-for-byte. *Amplifier:* the text passed to `amplifier run --prompt ...`. *Generic:* whatever your system received — prompt, query, payload, request body.
- **`judge_rubric`** — if a separate evaluator scored the run, inline its criteria (not just a path). *Amplifier:* judge LLM system prompt + `rubric.md` content. *Generic:* the rule set, the test code, or the scoring criteria — inlined or copied into the run directory. If the rubric evolves later, today's verdicts become uninterpretable without this.
- **`failure: {stage, message, traceback, exit_code}`** — populated whenever anything errors. Never let errors survive only as buried text in stdout. *Amplifier:* solver exit code, hook failures, mode-gate denials, judge errors. *Generic:* whatever structured error your system can surface — process exit, exception, HTTP status, validation failure.
- **`cost_usd` + `tokens`** — structured cost data, not stdout-grep. *Amplifier:* derive from `llm:response` events; store `cost_usd`, `model`, and input/output/cache token counts. *Generic:* whatever your provider returns — currency, billable units, model id. If there is no cost, omit the field rather than zero-fill.
- **Profile / config snapshot** — the configuration that produced the run, not a path to it. *Amplifier:* copy `profiles/<variant>.yaml` into the run directory as `profile.snapshot.yaml`, or store its sha256 in `meta.json`. *Generic:* the config file content, or a sha256 plus a copy. Paths alone are useless if the file changes after the run.
- **Dependency inventory** — every version of every component active during the run. *Amplifier:* `amplifier bundle list` output saved to `bundles.txt`, plus core/foundation SHAs. *Generic:* `pip freeze` / `npm ls --depth=0` / `go mod graph` / equivalent, saved into the run directory.
- **Existing fields**: wall time, exit code, DTU/instance id, profile path, SHAs of every repo installed, pointers to session/execution files.

## Metrics extraction

The runner captures raw evidence. A separate script turns that evidence into numbers. This separation matters because:

- Metrics can be re-extracted over old runs without re-running the scenario
- Multiple scenarios can share the same extraction script
- New questions about old runs are answerable from the same captured data

The example's `extract_metrics.py` pulls:

- Wall time from `meta.json`, cross-checked against event timestamps
- Root-session input, output, and cache token counts from `llm:response` events
- Tool call counts and tool mix from `tool:pre` events
- Delegation targets from `delegate:agent_spawned` events
- The final assistant message text from `transcript.jsonl`
- File-line citations via regex over the final answer

For a new scenario, edit the script to add scenario-specific extractions (did the agent invoke a particular tool, did the output match an expected pattern, etc.). The token, event, and delegation extraction is general and worth reusing as is.

## Sample count

The directory shape supports multiple runs (`run-1/`, `run-2/`, etc.). For guidance on how many runs to do, see the Measurement section of `custom-scenarios.md`. As a practical starting point, get one run per variant working end-to-end before adding more.

## Tips

- When iterating on a profile, launch it first (`amplifier-digital-twin launch profiles/before.yaml --var ...`), exec a shell in, verify the environment works, then wire it into the runner.
- Log generously to stderr in `run.sh`. The `log()` and `die()` helpers in the example are worth copying as is.
- Never modify the user's local code or files. Always push all code and changes directly into the DTU and Gitea


## Next

With the harness in place, run it once and look at what came back. See the **Analyze the results** and **Analyze the Patterns** steps in `modes/evaluation.md` for guidance on reading the output and deciding whether the scenario needs more iteration.
