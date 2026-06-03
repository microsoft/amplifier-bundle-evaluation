# Harness Automation

Once a scenario is decided, wrap it in an automation so anyone can run it, re-run it, and get comparable results: stand up a fresh environment, run the scenario, capture everything for analysis, and tear down cleanly.

In most cases, you should not start by handrolling it. The amplifier-evaluation library is the automation mechanism: AI User, Grader, Extractor, and a harness `run()` that, per trial, launches a Digital Twin Universe, installs the agent, seeds the workspace, runs the agent, extracts artifacts, grades, and destroys the environment. It writes a structured run tree (`run.json`, `summary.json`, and per-trial `state.json`, `ai_user.json`, `extraction/`, `grader/`). Read the library reference for how to run it:

```
read_file file_path="@evaluation:context/harness/overview.md"
```

You can see what the worked examples do: `examples/01-explorer-removal` drives the library bricks directly from a custom `harness.py` for a before/after comparison; `examples/02`, `03`, and `04` run off-the-shelf tasks through the harness from their own `run.sh` scripts.

The library handles the lifecycle. The guardrails below are the expertise it does not enforce for you.

## Where output goes, and never commit it

A run directory captures `events.jsonl`, `transcript.jsonl`, stdout, profiles, and grader output. These can hold provider keys, full prompts and responses (including private repo content), absolute host paths, and the agent's complete reasoning trace. By default they must not be source controlled.

Decide where output lands before the first run:

- If the project already has a pattern, match it: an existing evaluation output directory in the workspace, or a location defined in `AGENTS.md` or another context file.
- Otherwise, ask the user where they want evaluation outputs, noting that by default these should not be source controlled.
- Default suggestion: a sortable, per-project directory in the workspace root rather than inside an individual repo, e.g. `.amplifier/evaluation/<project>/<sortable-datetime>/` (such as `.amplifier/evaluation/explorer-removal/20260603T135349Z/`).

Make sure the chosen location is git-ignored before the first run. Sanity check before any commit: `git status` should never list captured run output.

## Make a comparison vary exactly one dimension

For before/after (A/B) evaluations, the two variants must differ in exactly one dimension (the foundation branch, the model, the prompt). Everything else (CLI version, other bundles, target repo, provider config) stays identical, or the diff is uninterpretable. The DTU profile is the source of truth for the environment: redirect any repos the scenario depends on to a local Gitea mirror with `url_rewrites` so you can pin a branch or work-in-progress code, and pass secrets like `GITEA_TOKEN` at launch via `--var`, never baked into the profile.

## Capture enough to reconstruct the run later

The harness records most of this automatically; hold to these principles for anything you add or for a custom harness:

- Snapshot the config that produced the run (the profile content or its hash), not a path to it.
- Inline the grader rubric with the results, not just a reference. If the rubric changes later, old verdicts become uninterpretable without it.
- Capture cost, tokens, and a dependency inventory (bundle list, core and foundation SHAs) per run.
- Surface failures structurally (stage, message, exit code), never only as buried stdout text.
- Keep raw capture separate from metrics extraction, so metrics can be re-derived over old runs without re-running them.

## Tips

- Iterate on a profile by launching it and exec-ing a shell in to verify the environment before wiring it into the run.
- Never modify the user's local code or files. Push all code and changes into the DTU and Gitea.

## Next

With the harness running, look at what came back. See the **Analysis** step in `modes/evaluation.md` for reading the output and deciding whether the scenario needs iteration.
