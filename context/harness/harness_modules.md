# Harness Modules

The harness lives in `src/amplifier_evaluation/harness/` as a flat set of bricks plus one assembled entry point. Each brick has a single responsibility and a small typed contract, so consumers can either call the assembled `run()` to do everything end-to-end, or import individual modules and compose their own flow.

The deterministic per-trial sequence wired by these modules:

```
launching -> installing -> seeding -> running_agent -> extracting -> grading -> cleaning_up
```

## schema

`schema.py` defines the harness's stable surface area. Loaders produce these types, the scheduler consumes them, results land on disk as JSON serializations of them.

Key types:

- `AgentSpec` — one agent loaded from `agents/<id>/`. Carries `install` (parsed `install.yaml`), `meta`, and `invocation_md`.
- `TaskSpec` — one task loaded from `tasks/<id>/`. Exposes `timeout_s`.
- `TrialSpec` — `(agent, task, trial_number)` plus optional `launch_variables` forwarded to the DTU launch. The atomic unit of work.
- `TrialState` — Enum: `pending`, `launching`, `installing`, `seeding`, `running_agent`, `extracting`, `grading`, `cleaning_up`, `completed`, `failed`, `cancelled`. The `is_terminal` property flags the last three.
- `TrialResult` — the final outcome handed back to callers. Mirrors the final `state.json`.
- `RunSpec` / `RunResult` — top-level inputs and outputs.

## loaders

`loaders.py` turns benchmark directories into typed specs. Pure I/O + schema validation, no DTU, no LLM.

```python
from amplifier_evaluation.harness import loaders

agents = loaders.discover_agents("amplifier-benchmark/agents")
tasks = loaders.discover_tasks("amplifier-benchmark/tasks")
agent = loaders.load_agent("amplifier-benchmark/agents/amplifier-foundation")
task = loaders.load_task("amplifier-benchmark/tasks/cpsc_recall_monitor")
```

Agents may omit `data.yaml` (extractor stage will be skipped for them). Tasks may omit `workspace/` and `grader-data/`.

## dtu

`dtu.py` is an async wrapper around the `amplifier-digital-twin` CLI. The harness shells out to the CLI rather than importing the engine, which keeps the dependency surface tiny and lets the backend be swapped by replacing this one file.

```python
from amplifier_evaluation.harness.dtu import DTU, cli_available

assert cli_available()
dtu = await DTU.launch("amplifier-benchmark/tasks/cpsc_recall_monitor/profile.yaml")
await dtu.file_push("local/file.txt", "/workspace/file.txt")
result = await dtu.exec_cmd(["bash", "-lc", "ls /workspace"], timeout_s=30)
await dtu.file_pull("/workspace/output.csv", "host/output.csv")
await dtu.destroy()
```

All operations are async so many trials can run concurrently without blocking each other.

## install

`install.py` installs an agent into a running DTU.

Agents declare `setup_cmds`: a list of `bash -lc` commands run inside the task's DTU after launch. There is no parallel "agent profile" path; agents always compose onto the task's profile.

```python
from amplifier_evaluation.harness.install import (
    install_agent, compose_launch_profile, verify_env,
)

missing = verify_env(agent)  # checks install.yaml requires.env[]
profile_path = compose_launch_profile(
    agent, task.profile_path, trial_dir / "launch_profile.yaml"
)
# Adds passthrough.services entries for agent.install.requires.env so the
# agent's required env vars reach the DTU without the task profile having
# to enumerate every possible API key. Task entries always win on conflict.
await install_agent(agent, dtu, log_to=Path("install.log"))
```

## state

`state.py` is the on-disk state persistence layer. Every trial has one `state.json` written atomically (tempfile + rename) at every stage transition.

```python
from amplifier_evaluation.harness import state as state_io

record = state_io.load_state(trial_dir)            # None if absent
state_io.save_state(trial_dir, record)
state_io.transition(trial_dir, record, TrialState.RUNNING_AGENT)
state_io.append_log(trial_dir, "free-form note")
cancelled = state_io.check_cancel_requested(trial_dir)
```

The `state.json` schema is the harness's external observation surface. An operator (human or agent) can read it at any time to see exactly where a trial is, and can set two flags on it to course-correct a long-running batch:

- `cancel_requested: true` — the trial stops at the next stage boundary, destroys its DTU, and transitions to `cancelled`.
- `retry_requested: true` — a terminal trial (`failed` or `cancelled`) resets to `pending` on the next harness invocation and re-runs through the full lifecycle.

## trial

`trial.py` runs one trial end to end. This is the only place that knows the full stage sequence.

```python
from amplifier_evaluation.harness.trial import run_trial

result = await run_trial(
    spec=trial_spec,
    trial_dir=Path("results/run-1/trials/<id>"),
    ai_user=ai_user,
    grader=grader,
    extractor=extractor,
)
```

Properties of `run_trial`:

- Idempotent: writes the final state to disk on completion, failure, or cancellation.
- DTU always destroyed in a `finally` block, even on exceptions.
- Reloads any existing `state.json` on entry. Terminal trials are skipped unless `retry_requested` is set.
- Honours `cancel_requested` at every stage boundary.
- `meta.yaml.timeout` is enforced around the AI User call via `asyncio.wait_for`. Timeout transitions the trial to `failed` and still destroys the DTU.
- Per-stage outcomes are recorded in `state.json` as small JSON-safe summaries (`ai_user`, `extractor`, `grader`), with full artifacts on disk next to it.
- Extractor failure or grader failure inside a trial does not fail the trial. Both record `{"status": "failed", "error": ...}` and the trial proceeds.

## scheduler

`scheduler.py` is intentionally tiny: an `asyncio.Semaphore` caps concurrency, each trial runs in its own task, results return in input order.

```python
from amplifier_evaluation.harness.scheduler import run_trials

results = await run_trials(
    specs,
    trials_root=Path("results/run-1/trials"),
    ai_user=ai_user,
    grader=grader,
    extractor=extractor,
    max_parallel=2,
)
```

Failures inside one trial never propagate to others. The scheduler also catches anything that escapes `run_trial` itself and converts it into a synthetic `failed` `TrialResult`, so a multi-day batch survives individual trial crashes.

The scheduler emits no events. Progress observation is via the `state.json` files instead, which means external observers see exactly the same data the built-in UI does.

## events

`events.py` polls each trial's `state.json` and prints a flat event log to stdout. It runs as a separate `asyncio.Task` alongside the scheduler, so headless runs can skip it without changing anything else. No third-party UI dependency: it is plain `print()` lines.

```python
import asyncio
from amplifier_evaluation.harness.events import render_events

stop_event = asyncio.Event()
ui_task = asyncio.create_task(render_events(specs, trials_root, stop_event))
# ...run the scheduler...
stop_event.set()
await ui_task
```

One line is emitted on the first transition into each interesting state:

```
PENDING      -> LAUNCHING       "trial started"
LAUNCHING    -> INSTALLING      "dtu launched   dtu_id=<id>"
*            -> RUNNING_AGENT   "agent running  timeout=<n>s"
*            -> GRADING         "-> grading     verdict=<v>"
*            -> COMPLETED       "finished       completed  score=<x>  <elapsed>"
*            -> FAILED          "finished       failed     error=<head>  <elapsed>"
*            -> CANCELLED       "finished       cancelled  <elapsed>"
```

`SEEDING`, `EXTRACTING`, `CLEANING_UP`, and `PENDING` are intentionally silent on the console; full detail still lands in `harness.log`. Each line is prefixed with a `[HH:MM:SS]` timestamp and a fixed-width `agent x task` label so output from concurrent trials stays readable.

## run

`run.py` is the assembled entry point and the "example" wiring of every other module: load, build trial specs, share one AIUser/Grader/Extractor across all trials (expensive `setup()` called once), schedule, optionally render the event log, write `run.json` + `summary.json`. It also configures logging so detail goes to `<output_dir>/harness.log` while the console stays quiet enough for the event log to own stdout.

```python
from amplifier_evaluation.harness.run import run

result = await run(
    agents_dir="amplifier-benchmark/agents",
    tasks_dir="amplifier-benchmark/tasks",
    selection=[("amplifier-foundation", "cpsc_recall_monitor")],
    output_dir="results/my-run",
    trials_per_pair=1,
    max_parallel=2,
    launch_variables={"SWE_REPO": "owner/name"},  # optional, forwarded to launch --var
    run_id=None,  # optional; defaults to a timestamped id
)
```

The only command-line front end is the installable `amplifier-evaluation` CLI (`cli.py`), available on PATH after `uv tool install` and as `python -m amplifier_evaluation run` from any environment where the package is importable. It wraps this same `run()`:

```bash
amplifier-evaluation run \
  --agents-dir amplifier-benchmark/agents \
  --tasks-dir amplifier-benchmark/tasks \
  --output-dir results \
  --agent amplifier-foundation \
  --task cpsc_recall_monitor \
  --max-parallel 2 \
  --trials-per-pair 1
```

Selection is either the cartesian product of `--agent` × `--task` (both repeatable; default: everything discovered) or explicit `--pair agent:task` (repeatable; mutually exclusive with `--agent`/`--task`). `--launch-var KEY=VALUE` (repeatable) is how examples 03 and 04 inject `SWE_REPO`/`SWE_COMMIT`; `--run-id` pins the output subdirectory name (the form the example `run.sh` scripts use); `--dry-run` previews the selection. See `amplifier-evaluation run --help` for the full list.

Consumers that need different behaviour can either pass overrides to `run()` or copy `run.py` and edit it directly. Bricks are stable; the example is meant to be replaced.

## On-disk layout

One harness invocation produces:

```
<output_dir>/
  run.json                 plan: agents, tasks, selection, started_at
  summary.json             final counts + per-trial summaries (written at end)
  trials/<trial-id>/
    state.json             state machine + history + per-stage summaries
    trial.log              human-readable transition log
    launch_profile.yaml    task profile merged with the agent's required env (compose_launch_profile)
    install.log            agent install output (setup_cmds)
    instructions.txt       task instructions pushed into the DTU
    ai_user.json           AI User result (conclude verdict, session id, full text)
    extraction/            Extractor output: extraction_report.md + manifest.json + pulled artifacts
    grader/<eval>/         Grader output: initial_report.md + rubric.json per evaluation
    grader/grader_result.json   weighted overall + per-evaluation scores
```

Everything needed to analyze a trial is in its trial directory. Re-runs reuse the same layout: terminal trials are skipped, in-flight ones restart cleanly because the DTU is gone.
