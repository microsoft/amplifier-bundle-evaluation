"""On-disk state persistence for trials.

Each trial owns one `state.json` file under its trial directory. Every stage
transition writes a new snapshot via `save_state()`, which uses atomic rename
to avoid torn reads from external observers.

External agents and operators can read these state files at any time. They
can also write `cancel_requested: true` or `retry_requested: true` to a
state.json and the scheduler will honour the flag on its next state check.
This is the harness's course-correction surface.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from amplifier_evaluation.harness.schema import StageRecord, TrialState, utcnow_iso


STATE_FILENAME = "state.json"
LOG_FILENAME = "trial.log"


@dataclass
class TrialStateRecord:
    """The full on-disk shape of state.json for one trial."""

    trial_id: str
    agent_id: str
    task_id: str
    trial_number: int
    state: str  # TrialState value
    history: list[StageRecord] = field(default_factory=list)
    dtu_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    elapsed_s: float = 0.0
    error: str | None = None
    cancel_requested: bool = False
    retry_requested: bool = False
    ai_user: dict[str, Any] | None = None
    extractor: dict[str, Any] | None = None
    grader: dict[str, Any] | None = None


def _atomic_write(path: Path, text: str) -> None:
    """Write text to `path` via tempfile + rename so partial reads can't tear."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def load_state(trial_dir: Path) -> TrialStateRecord | None:
    """Read state.json. Returns None if it doesn't exist."""
    path = trial_dir / STATE_FILENAME
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    history = [StageRecord(**h) for h in raw.get("history", [])]
    return TrialStateRecord(
        trial_id=raw["trial_id"],
        agent_id=raw["agent_id"],
        task_id=raw["task_id"],
        trial_number=int(raw["trial_number"]),
        state=raw["state"],
        history=history,
        dtu_id=raw.get("dtu_id"),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
        elapsed_s=float(raw.get("elapsed_s", 0.0)),
        error=raw.get("error"),
        cancel_requested=bool(raw.get("cancel_requested", False)),
        retry_requested=bool(raw.get("retry_requested", False)),
        ai_user=raw.get("ai_user"),
        extractor=raw.get("extractor"),
        grader=raw.get("grader"),
    )


def save_state(trial_dir: Path, record: TrialStateRecord) -> None:
    """Atomically persist `record` to `state.json` under `trial_dir`."""
    path = trial_dir / STATE_FILENAME
    payload = asdict(record)
    _atomic_write(path, json.dumps(payload, indent=2, default=str))


def transition(
    trial_dir: Path,
    record: TrialStateRecord,
    new_state: TrialState,
    note: str | None = None,
) -> TrialStateRecord:
    """Record a state transition: append history, update state, save atomically."""
    now = utcnow_iso()
    record.state = new_state.value
    record.history.append(StageRecord(state=new_state.value, at=now, note=note))
    if new_state.is_terminal:
        record.finished_at = now
    append_log(
        trial_dir,
        f"[{now}] state={new_state.value}" + (f" note={note}" if note else ""),
    )
    save_state(trial_dir, record)
    return record


def append_log(trial_dir: Path, line: str) -> None:
    """Append a single line to trial.log. Best-effort; never raises."""
    try:
        trial_dir.mkdir(parents=True, exist_ok=True)
        with (trial_dir / LOG_FILENAME).open("a", encoding="utf-8") as f:
            f.write(line.rstrip("\n") + "\n")
    except OSError:
        pass


def check_cancel_requested(trial_dir: Path) -> bool:
    """Read the latest state from disk and return its `cancel_requested` flag.

    Used by long-running stages to bail out gracefully when an external agent
    asks them to stop mid-trial.
    """
    cur = load_state(trial_dir)
    return bool(cur and cur.cancel_requested)
