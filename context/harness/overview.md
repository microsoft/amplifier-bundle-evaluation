# Harness

The bundle ships a Python package, `amplifier_evaluation`, for running pre-defined evaluations against an agent inside a Digital Twin Universe, plus a benchmark dataset under `amplifier-benchmark/` (pre-defined tasks and agent definitions). The package is independent of the `evaluation` mode (which is for designing evaluations) and is consumed as a library.

The intent is one package, four pieces that can be used together or in isolation:

- `ai_user` (implemented): drives an agent in a DTU like a real user would.
- `grader` (implemented): scores agent output against a rubric defined in `amplifier-benchmark/tasks/<task>/grader.yaml`.
- `extractor` (implemented): pulls the agent's work (deliverables + session logs) out of a DTU onto the host so it can be analyzed later. Uses `amplifier-benchmark/agents/<agent>/data.yaml` as a hint.
- `harness` (implemented): orchestrates the three pieces above across many `(agent, task, trial)` combinations, manages DTU lifecycle and parallelism, and persists every state transition to disk for resumability and external observation. See [`harness_modules.md`](harness_modules.md) for the per-module breakdown.

## Layout

```
amplifier-bundle-evaluation/
├── pyproject.toml
├── src/amplifier_evaluation/
│   ├── ai_user/        # AIUser, ConcludeTool, personas, system instruction
│   ├── grader/         # Grader, SubmitRubricTool, schema parser, rubric validation
│   ├── extractor/      # Extractor, SubmitExtractionManifestTool, manifest validation
│   └── harness/        # orchestration: loaders, dtu, install, state, trial, scheduler, events, run
└── amplifier-benchmark/      # benchmark dataset
    ├── agents/         # per-agent definitions: install.yaml, invocation.md, data.yaml, meta.yaml
    └── tasks/          # per-task definitions: task.yaml, profile.yaml, grader.yaml, meta.yaml, grader-data/, workspace/
```

## Tasks

A task describes work to give an agent and how to grade the result. Each task lives in `amplifier-benchmark/tasks/<task-id>/`:

- `meta.yaml`: name, difficulty, categories, timeout.
- `task.yaml`: plain-text instructions handed to the agent.
- `profile.yaml`: DTU profile the task runs in.
- `grader.yaml`: one or more weighted `evaluations`, each with `steps` (how to audit) and a `rubric` (criteria with point values).
- `grader-data/` (optional): files pushed into the DTU after the agent finishes, for the grader to use.
- `workspace/` (optional): files seeded into the agent's working directory at start.

Two tasks ship today: `cpsc_recall_monitor` (easy) and `chiptune_generator` (hard).

## Agents

An agent describes how to install and drive a CLI agent inside a DTU. Each agent lives in `amplifier-benchmark/agents/<agent-id>/`:

- `meta.yaml`: name, description.
- `install.yaml`: DTU setup commands and required env vars.
- `invocation.md`: how to talk to the CLI (first turn, follow-up turns). Read by the AI User as runtime guidance.
- `data.yaml`: where session transcripts and metadata live inside the DTU. Consumed by the extractor.

Two agents ship today: `amplifier-foundation` and `openai-codex-cli`.

## AI User

`AIUser` is a Foundation session that role-plays a user against an agent running in a DTU. It uses `bash` + `amplifier-digital-twin exec` to drive the agent CLI (no Python transport layer), reads the agent's `invocation.md` as runtime instructions, and calls a built-in `conclude` tool when the scenario is done.

Minimal usage:

```python
import asyncio
from pathlib import Path
from amplifier_evaluation.ai_user import AIUser

async def main():
    ai = AIUser()  # defaults to loading foundation + anthropic-sonnet provider from canonical git URLs
    await ai.setup()

    invocation_guide = Path("amplifier-benchmark/agents/amplifier-foundation/invocation.md").read_text()
    result = await ai.run(
        scenario="Say hi. Then ask the agent what the weather is in Boston. Conclude.",
        dtu_id="dtu-xxxxxxxx",  # DTU must already be running with the agent installed
        invocation_guide=invocation_guide,
    )
    print(result.conclude.verdict, result.conclude.summary)

asyncio.run(main())
```

`AIUser(foundation_source=..., provider_source=...)` accepts any string `load_bundle` understands (git URL, local path, etc.), so the AI User can also be pointed at a local Foundation checkout for development.

`AIUser.run()` also accepts a `workspace_dir` parameter (default `/workspace`). Every agent CLI invocation is wrapped with `bash -c 'cd <workspace_dir> && ...'` so the agent's deliverables and session data land in a predictable cwd. This contract lives at the AI User layer so per-agent `invocation.md` files stay workspace-agnostic. Task profiles in this benchmark create `/workspace` at provision time; override `workspace_dir` only for tasks that need a different working directory.

## Grader

`Grader` is a Foundation session that audits an agent's work inside a DTU against a `grader.yaml` rubric. Like the AI User it uses `bash` + `amplifier-digital-twin exec` to explore the DTU (no Python transport layer). For each `evaluation` in the grader.yaml it runs a single multi-turn session with three phases:

1. Explore the DTU and write a free-text initial report.
2. Submit the structured rubric via the `submit_rubric` tool, whose JSON input schema is dynamically generated from the evaluation's rubric (exact criterion keys, per-criterion max points).
3. If validation fails, ask for fixes (max 2 retries).

The final score is the weighted sum of per-evaluation scores. Per-evaluation artifacts (`initial_report.md`, `rubric.json`) land in `output_dir/<evaluation_name>/`, plus a top-level `grader_result.json`.

Minimal usage:

```python
import asyncio
from pathlib import Path
from amplifier_evaluation.grader import Grader

async def main():
    g = Grader()  # defaults to loading foundation + anthropic-sonnet provider from canonical git URLs
    await g.setup()

    task_context = Path("amplifier-benchmark/tasks/cpsc_recall_monitor/task.yaml").read_text()
    result = await g.run(
        grader_yaml_path="amplifier-benchmark/tasks/cpsc_recall_monitor/grader.yaml",
        task_context=task_context,
        dtu_id="dtu-xxxxxxxx",  # DTU must already be running with the agent's work in it
        output_dir="./grader_output",
    )
    print(f"overall_score: {result.overall_score:.3f}")
    for ev in result.evaluations:
        print(f"  {ev.name}: {ev.points_awarded}/{ev.points_possible}")

asyncio.run(main())
```

`Grader(foundation_source=..., provider_source=...)` accepts the same sources as `AIUser`.

## Extractor

`Extractor` is a Foundation session that pulls the agent's work out of a DTU onto the host so it can be analyzed later. Like the AI User and Grader it uses `bash` + `amplifier-digital-twin` (no Python transport layer), but with two host-side commands: `amplifier-digital-twin exec` to inspect inside the DTU, and `amplifier-digital-twin file-pull` to copy files onto the host.

The Extractor is framed by goal, not by paths. It runs a single multi-turn session with three phases:

1. Given the original task context and the agent's `data.yaml` (as a hint), explore the DTU and pull (a) the agent's DELIVERABLES wherever they actually live and (b) the agent's SESSION LOGS. Final assistant message is a free-text extraction report.
2. Submit a structured manifest via the `submit_extraction_manifest` tool. Each entry has a `category` of `workspace` (deliverables), `session_data` (transcripts/events/metadata), or `other` (auxiliary state worth keeping, with a `note`).
3. If validation fails (host destinations missing on disk or outside `output_dir`), ask for fixes (max 2 retries).

The `data.yaml` is treated as a hint, not a strict spec. If the paths in `data.yaml` do not exist (slug drift, agent wrote elsewhere), the Extractor walks the directory tree to find what is actually there. Artifacts (`extraction_report.md`, `manifest.json`, `extraction_result.json`) land at the root of `output_dir`; pulled files land under sensible subdirectories (`sessions/<id>/`, `workspace/`, `other/<name>/`).

Minimal usage:

```python
import asyncio
from pathlib import Path
from amplifier_evaluation.extractor import Extractor

async def main():
    e = Extractor()  # defaults to loading foundation + anthropic-sonnet provider from canonical git URLs
    await e.setup()

    task_context = Path("amplifier-benchmark/tasks/cpsc_recall_monitor/task.yaml").read_text()
    result = await e.run(
        dtu_id="dtu-xxxxxxxx",  # DTU must already be running with the agent's work in it
        task_context=task_context,
        data_yaml_path="amplifier-benchmark/agents/amplifier-foundation/data.yaml",
        output_dir="./extractor_output",
    )
    print(f"session_dirs:   {result.session_dirs}")
    print(f"workspace_dir:  {result.workspace_dir}")
    for entry in result.manifest.extracted:
        print(f"  [{entry.category}] {entry.destination}")

asyncio.run(main())
```

`ExtractionResult` exposes `session_dirs`, `workspace_dir`, and `workspace_paths` helper properties so the orchestrator can find artifacts without inspecting categories itself. `Extractor(foundation_source=..., provider_source=...)` accepts the same sources as `AIUser`.

## Harness

The harness in `src/amplifier_evaluation/harness/` is a flat set of modular pieces: `loaders`, `dtu`, `install`, `state`, `trial`, `scheduler`, and `events`. Each has a single responsibility and a small typed contract, so consumers compose what they need: load tasks and agents from disk, wrap the DTU CLI from Python, install an agent into a running DTU, run one trial end to end, schedule many trials in parallel, print a flat per-trial event log, or persist trial state for resumability. Together they orchestrate AI User, Extractor, and Grader across many `(agent, task, trial)` combinations: per trial they launch a Digital Twin Universe instance, install the agent, seed the workspace, drive the agent through the AI User, extract artifacts to the host, run the grader, and destroy the DTU. Parallelism is capped by a semaphore so a batch of trials can run concurrently without saturating the host. Every state transition is written atomically to a per-trial `state.json`, so a crashed harness can be re-run and resume, an external observer can read live progress without the harness emitting events, and an operator can write `cancel_requested` or `retry_requested` to that file to course-correct a multi-day run.

As one worked example, the package ships an assembled `run()` entry point that wires every brick together with sensible defaults. It is intentionally short and meant to be copied and edited; consumers with different needs should treat it as a template, not a fixed API.

Minimal usage:

```python
import asyncio
from amplifier_evaluation.harness.run import run

async def main():
    result = await run(
        agents_dir="amplifier-benchmark/agents",
        tasks_dir="amplifier-benchmark/tasks",
        selection=[
            ("amplifier-foundation", "cpsc_recall_monitor"),
            ("openai-codex-cli", "cpsc_recall_monitor"),
        ],
        output_dir="results/my-run",
        max_parallel=2,
    )
    print(result.summary_counts)

asyncio.run(main())
```

For the per-module breakdown, contracts, course-correction surface, and on-disk layout, see [`harness_modules.md`](harness_modules.md).

## Dependencies

The package depends on `amplifier-core` and `amplifier-foundation`. For local development those are resolved from sibling submodules via `[tool.uv.sources]` in `pyproject.toml`. `uv sync` builds them from source the first time (amplifier-core has a Rust extension and takes a minute or two).
