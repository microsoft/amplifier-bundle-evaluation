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
    render_html.py       # Renders a per-run self-contained HTML report at the run root
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
        verdict.html         # Self-contained visual report — share/email this
      after/run-1/
        (same shape)
```

Keep the `results/` shape identical across scenarios. That way the same metrics extraction script (or any downstream analysis) works against any run directory without modification.

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

At minimum:

- `meta.json` for wall time, exit code, prompt, profile path, DTU id, SHAs of every repo installed, and pointers to session files
- `stdout.txt` for the full agent output as the user would see it
- `sessions/sessions/<session_id>/events.jsonl` for structured event data
- `sessions/sessions/<session_id>/transcript.jsonl` for the LLM conversation and the final answer

Pin every SHA you can in `meta.json`. The DTU mirrors moving targets (Gitea branch heads, GitHub clones); without pinned SHAs you cannot reproduce a result later.

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

## Visual report

Every captured run should also produce a self-contained HTML report at the run root (`verdict.html`). The runner generates it as the last step. The HTML is for humans — shareable, emailable, no setup required to view.

The five things every report should do:

1. **Lead with a verdict banner.** Color-coded green/red, with one plain-English sentence explaining what the outcome means. Don't assume the reader knows the benchmark's jargon.
2. **Show the headline numbers as cards.** 5–8 key numbers (pass rates, wall time, tool calls, etc.), each color-coded by whether it's good or bad.
3. **Use plain-English section headings.** "How the agent worked", "What the agent changed" — not "Solver session (raw)". Keep the technical name in parentheses if the reader needs it.
4. **Inline the narrative.** If there's a post-run analyzer, inline its rendered markdown as the primary content of the page.
5. **Hide the long stuff.** Wrap problem statements, raw stdout, gold patches, and full metadata in expandable `<details>` blocks so the page is scannable.
6. Generally be concise and focus on the important parts.

See `@evaluation:examples/03-swebench-multimodal-foundation/metrics/render_html.py` as a working reference.

<details>
<summary>Implementation notes</summary>

- **Self-contained.** Inline all CSS. One CDN dependency is acceptable (e.g. `marked` for rendering inlined markdown); more than one defeats the "share this single file" point.
- **Wiring.** One line in `run.sh` after `summarize_run.py`:

  ```bash
  python3 "$EXAMPLE_DIR/metrics/render_html.py" "$RESULTS"
  ```

- **User pointer.** Add the path to the final log block so the user knows to open it:

  ```bash
  log "  visual report:      $RESULTS/verdict.html (open in a browser)"
  ```

- **Side-by-side artifacts.** For code-patch scenarios, show the agent's diff next to the gold diff. For other scenarios, show output vs. expected. Make differences obvious.

</details>

## Sample count

The directory shape supports multiple runs (`run-1/`, `run-2/`, etc.). For guidance on how many runs to do, see the Measurement section of `custom-scenarios.md`. As a practical starting point, get one run per variant working end-to-end before adding more.

## Tips

- When iterating on a profile, launch it first (`amplifier-digital-twin launch profiles/before.yaml --var ...`), exec a shell in, verify the environment works, then wire it into the runner.
- Log generously to stderr in `run.sh`. The `log()` and `die()` helpers in the example are worth copying as is.
- Never modify the user's local code or files. Always push all code and changes directly into the DTU and Gitea


## Next

With the harness in place, run it once and look at what came back. See the **Analyze the results** and **Analyze the Patterns** steps in `modes/evaluation.md` for guidance on reading the output and deciding whether the scenario needs more iteration.
