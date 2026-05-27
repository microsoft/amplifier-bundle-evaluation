# Harness Modules

The harness lives in `src/amplifier_evaluation/harness/` as a flat set of bricks plus one assembled entry point. Each brick has a single responsibility and a small typed contract, so consumers can either call the assembled `run()` to do everything end-to-end, or import individual modules and compose their own flow.

The deterministic per-trial sequence wired by these modules:

```
launching -> installing -> seeding -> running_agent -> extracting -> grading -> cleaning_up
```

## schema

`schema.py` defines the harness's stable surface area. Loaders produce these types, the scheduler consumes them, results land on disk as JSON serializations of them.

Key types:

- `AgentSpec` — one agent loaded from `agents/<id>/`. Exposes `install_mode` (`setup_cmds` or `dtu_profile`).
- `TaskSpec` — one task loaded from `tasks/<id>/`. Exposes `timeout_s`.
- `TrialSpec` — `(agent, task, trial_number)`. The atomic unit of work.
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

Two patterns are supported:

- `setup_cmds`: list of `bash -lc` commands run inside an already-launched DTU. Used by agents that compose onto a task's profile (e.g. `amplifier-foundation`).
- `dtu_profile`: a Digital Twin Universe profile that already has the agent baked in. Nothing to install post-launch; the harness uses this profile to launch instead of the task's profile.

```python
from amplifier_evaluation.harness.install import (
    install_agent, select_profile_path, verify_env,
)

missing = verify_env(agent)  # checks install.yaml requires.env[]
profile_path = select_profile_path(agent, task.profile_path)
# walks up all ancestors of agent.dir to find dtu_profile paths
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

## progress

`progress.py` polls each trial's `state.json` and renders a Rich live table. It runs as a separate `asyncio.Task` alongside the scheduler, so headless runs can skip it without changing anything else.

```python
import asyncio
from amplifier_evaluation.harness.progress import render_progress

stop_event = asyncio.Event()
ui_task = asyncio.create_task(render_progress(specs, trials_root, stop_event))
# ...run the scheduler...
stop_event.set()
await ui_task
```

If Rich is not installed, a plain-text fallback prints a one-line summary every refresh interval.

## run

`run.py` is the assembled entry point and the "example" wiring of every other module. It is intentionally short (around 100 lines): load, build trial specs, share one AIUser/Grader/Extractor across all trials (expensive `setup()` called once), schedule, optionally render progress, write `run.json` + `summary.json`.

```python
from amplifier_evaluation.harness.run import run

result = await run(
    agents_dir="amplifier-benchmark/agents",
    tasks_dir="amplifier-benchmark/tasks",
    selection=[("amplifier-foundation", "cpsc_recall_monitor")],
    output_dir="results/my-run",
    trials_per_pair=1,
    max_parallel=2,
)
```

Also runnable as a module for testing:

```bash
python -m amplifier_evaluation.harness.run \
  --agents amplifier-benchmark/agents \
  --tasks amplifier-benchmark/tasks \
  --output results/my-run \
  --max-parallel 2 \
  --pair amplifier-foundation:cpsc_recall_monitor \
  --pair openai-codex-cli:cpsc_recall_monitor
```

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
    install.log            agent install output (setup_cmds path only)
    instructions.txt       task instructions pushed into the DTU
    ai_user.json           AI User result (conclude verdict, session id, full text)
    extraction/            Extractor output: extraction_report.md + manifest.json + pulled artifacts
    grader/<eval>/         Grader output: initial_report.md + rubric.json per evaluation
    grader/grader_result.json   weighted overall + per-evaluation scores
```

Everything needed to analyze a trial is in its trial directory. Re-runs reuse the same layout: terminal trials are skipped, in-flight ones restart cleanly because the DTU is gone.
