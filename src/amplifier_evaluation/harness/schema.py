"""Dataclasses for the evaluation harness.

These types form the harness's stable surface area. Loaders produce them
(`AgentSpec`, `TaskSpec`); the scheduler consumes them (`TrialSpec`) and
emits `TrialResult` after each trial finishes. `TrialState` is the on-disk
state-machine vocabulary.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class TrialState(str, Enum):
    """States in a trial's lifecycle.

    Persisted to disk as the `state` field in `state.json`. Terminal states
    (`completed`, `failed`, `cancelled`) are not advanced further by the
    scheduler unless `retry_requested` is set by an external operator.
    """

    PENDING = "pending"
    LAUNCHING = "launching"
    INSTALLING = "installing"
    SEEDING = "seeding"
    RUNNING_AGENT = "running_agent"
    EXTRACTING = "extracting"
    GRADING = "grading"
    CLEANING_UP = "cleaning_up"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (TrialState.COMPLETED, TrialState.FAILED, TrialState.CANCELLED)


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentSpec:
    """One agent loaded from disk (a directory under `agents/`)."""

    id: str
    dir: Path
    meta: dict[str, Any]
    install: dict[str, Any]
    invocation_md: str
    # data.yaml is optional (openai-codex-cli currently ships without one).
    data_yaml_path: Path | None


@dataclass
class TaskSpec:
    """One task loaded from disk (a directory under `tasks/`)."""

    id: str
    dir: Path
    meta: dict[str, Any]
    instructions: str
    profile_path: Path
    grader_yaml_path: Path
    workspace_dir: Path  # `<task.dir>/workspace`
    grader_data_dir: Path | None  # `<task.dir>/grader-data` if it exists

    @property
    def timeout_s(self) -> int:
        """Per-trial timeout in seconds. Defaults to 1 hour."""
        return int(self.meta.get("timeout", 3600))


@dataclass
class TrialSpec:
    """One trial: a (agent, task, trial_number) tuple ready to run."""

    agent: AgentSpec
    task: TaskSpec
    trial_number: int
    # Variables to pass through to `amplifier-digital-twin launch --var k=v`.
    # The DTU CLI substitutes `${KEY}` references in the profile (most
    # commonly inside `url_rewrites:` blocks pointing at a local Gitea
    # mirror). Set per-trial so different tasks can launch with different
    # variables; the run-level value in `RunSpec.launch_variables` is the
    # default applied to every trial.
    launch_variables: dict[str, str] | None = None

    @property
    def trial_id(self) -> str:
        return f"{self.agent.id}__{self.task.id}__trial-{self.trial_number}"


@dataclass
class StageRecord:
    """One stage transition entry in a trial's history."""

    state: str
    at: str  # ISO8601 UTC
    note: str | None = None


@dataclass
class TrialResult:
    """Outcome of one trial. Mirrors the final state.json."""

    trial_id: str
    agent_id: str
    task_id: str
    trial_number: int
    state: str
    dtu_id: str | None
    started_at: str | None
    finished_at: str | None
    elapsed_s: float
    error: str | None
    # Per-stage outcomes. Each is a small JSON-safe summary; the full
    # artifacts live next to state.json on disk.
    ai_user: dict[str, Any] | None = None
    extractor: dict[str, Any] | None = None
    grader: dict[str, Any] | None = None
    history: list[StageRecord] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


@dataclass
class RunSpec:
    """Inputs to one harness run."""

    agents_dir: Path
    tasks_dir: Path
    output_dir: Path
    selection: list[tuple[str, str]]  # explicit (agent_id, task_id) pairs
    trials_per_pair: int = 1
    max_parallel: int = 2
    show_progress: bool = True
    # Variables threaded through to every trial's `DTU.launch(variables=...)`,
    # i.e. `amplifier-digital-twin launch --var KEY=VAL ...`. The DTU CLI
    # substitutes `${KEY}` references in the profile, most commonly in
    # `url_rewrites:` blocks pointing at a local Gitea mirror. Empty by
    # default; populated from `--launch-var KEY=VAL` on the CLI or from
    # callers using the Python API.
    launch_variables: dict[str, str] | None = None


@dataclass
class RunResult:
    """Outcome of one harness run."""

    run_id: str
    output_dir: Path
    started_at: str
    finished_at: str
    trials: list[TrialResult]

    @property
    def summary_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for t in self.trials:
            counts[t.state] = counts.get(t.state, 0) + 1
        return counts
