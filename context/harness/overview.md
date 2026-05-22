# Harness

The bundle ships a Python package, `amplifier_evaluation`, for running pre-defined evaluations against an agent inside a Digital Twin Universe, plus a benchmark dataset under `amplifier-benchmark/` (pre-defined tasks and agent definitions). The package is independent of the `evaluation` mode (which is for designing evaluations) and is consumed as a library.

The intent is one package, four pieces that can be used together or in isolation:

- `ai_user` (implemented): drives an agent in a DTU like a real user would.
- `grader` (placeholder): scores agent output against a rubric defined in `amplifier-benchmark/tasks/<task>/grader.yaml`.
- `extractor` (placeholder): pulls session artifacts out of a DTU using paths declared in `amplifier-benchmark/agents/<agent>/data.yaml`.
- `orchestrator` (placeholder): wires DTU launch, agent install, AI User run, extraction, and grading into one run.

Only `ai_user` is implemented today. The other three are empty modules that will be filled in incrementally.

## Layout

```
amplifier-bundle-evaluation/
├── pyproject.toml
├── src/amplifier_evaluation/
│   ├── ai_user/        # AIUser, ConcludeTool, personas, system instruction
│   ├── grader/         # placeholder
│   ├── extractor/      # placeholder
│   └── orchestrator/   # placeholder
└── amplifier-benchmark/      # benchmark dataset
    ├── agents/         # per-agent definitions: install.yaml, invocation.md, data.yaml, meta.yaml
    └── tasks/          # per-task definitions: task.yaml, profile.yaml, grader.yaml, meta.yaml, grader-data/, workspace/
```

## Tasks

A task describes work to give an agent and how to grade the result. Each task lives in `amplifier-benchmark/tasks/<task-id>/`:

- `meta.yaml`: name, difficulty, categories, timeout.
- `task.yaml`: plain-text instructions handed to the agent.
- `profile.yaml`: DTU profile the task runs in.
- `grader.yaml`: rubric (stages, weights, criteria with point values).
- `grader-data/` (optional): files pushed into the DTU after the agent finishes, for the grader to use.
- `workspace/` (optional): files seeded into the agent's working directory at start.

Two tasks ship today: `cpsc_recall_monitor` (easy) and `chiptune_generator` (hard).

## Agents

An agent describes how to install and drive a CLI agent inside a DTU. Each agent lives in `amplifier-benchmark/agents/<agent-id>/`:

- `meta.yaml`: name, description.
- `install.yaml`: DTU setup commands and required env vars.
- `invocation.md`: how to talk to the CLI (first turn, follow-up turns, what "broken" looks like). Read by the AI User as runtime guidance.
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

## Dependencies

The package depends on `amplifier-core` and `amplifier-foundation`. For local development those are resolved from sibling submodules via `[tool.uv.sources]` in `pyproject.toml`. `uv sync` builds them from source the first time (amplifier-core has a Rust extension and takes a minute or two).
