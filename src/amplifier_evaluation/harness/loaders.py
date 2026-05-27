"""Load benchmark tasks and agents from disk into typed specs.

Each loader is pure I/O + schema validation. No DTU, no LLM, no side effects
beyond reading files. This means downstream code (the trial runner, the
scheduler) never has to touch the filesystem layout convention.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from amplifier_evaluation.harness.schema import AgentSpec, TaskSpec


def _read_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at the top level")
    return data


def load_agent(agent_dir: Path | str) -> AgentSpec:
    """Load an agent from a directory like `agents/<id>/`.

    Required files: `meta.yaml`, `install.yaml`, `invocation.md`.
    Optional file: `data.yaml` (the Extractor needs one but a few agents may
    not ship one yet).
    """
    d = Path(agent_dir).resolve()
    if not d.is_dir():
        raise FileNotFoundError(f"agent directory not found: {d}")

    meta_path = d / "meta.yaml"
    install_path = d / "install.yaml"
    invocation_path = d / "invocation.md"
    data_path = d / "data.yaml"

    for p in (meta_path, install_path, invocation_path):
        if not p.is_file():
            raise FileNotFoundError(f"missing required agent file: {p}")

    meta = _read_yaml(meta_path)
    install = _read_yaml(install_path)
    invocation_md = invocation_path.read_text(encoding="utf-8")

    return AgentSpec(
        id=str(meta.get("name", d.name)),
        dir=d,
        meta=meta,
        install=install,
        invocation_md=invocation_md,
        data_yaml_path=data_path if data_path.is_file() else None,
    )


def load_task(task_dir: Path | str) -> TaskSpec:
    """Load a task from a directory like `tasks/<id>/`.

    Required files: `task.yaml`, `profile.yaml`, `meta.yaml`, `grader.yaml`.
    Optional dirs: `workspace/` (seeded into the DTU before the agent starts),
    `grader-data/` (sources for grader `mounts:` entries).
    """
    d = Path(task_dir).resolve()
    if not d.is_dir():
        raise FileNotFoundError(f"task directory not found: {d}")

    task_yaml = d / "task.yaml"
    profile_yaml = d / "profile.yaml"
    meta_yaml = d / "meta.yaml"
    grader_yaml = d / "grader.yaml"

    for p in (task_yaml, profile_yaml, meta_yaml, grader_yaml):
        if not p.is_file():
            raise FileNotFoundError(f"missing required task file: {p}")

    task_data = _read_yaml(task_yaml)
    meta = _read_yaml(meta_yaml)

    instructions = task_data.get("instructions")
    if not isinstance(instructions, str) or not instructions.strip():
        raise ValueError(f"{task_yaml}: `instructions:` must be a non-empty string")

    workspace_dir = d / "workspace"
    grader_data_dir = d / "grader-data"

    return TaskSpec(
        id=str(meta.get("name", d.name)),
        dir=d,
        meta=meta,
        instructions=instructions,
        profile_path=profile_yaml,
        grader_yaml_path=grader_yaml,
        workspace_dir=workspace_dir,
        grader_data_dir=grader_data_dir if grader_data_dir.is_dir() else None,
    )


def discover_agents(agents_root: Path | str) -> dict[str, AgentSpec]:
    """Load all agents under a root directory, keyed by agent id."""
    root = Path(agents_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"agents root not found: {root}")
    agents: dict[str, AgentSpec] = {}
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "meta.yaml").is_file():
            agent = load_agent(child)
            agents[agent.id] = agent
    return agents


def discover_tasks(tasks_root: Path | str) -> dict[str, TaskSpec]:
    """Load all tasks under a root directory, keyed by task id."""
    root = Path(tasks_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"tasks root not found: {root}")
    tasks: dict[str, TaskSpec] = {}
    for child in sorted(root.iterdir()):
        if child.is_dir() and (child / "task.yaml").is_file():
            task = load_task(child)
            tasks[task.id] = task
    return tasks
