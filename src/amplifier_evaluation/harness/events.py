"""High-level event-log progress reporter for a harness run.

Polls each trial's ``state.json`` and prints a single line each time a trial
crosses one of a small set of interesting state transitions:

    PENDING      -> LAUNCHING       "trial started"
    LAUNCHING    -> INSTALLING      "dtu launched   dtu_id=<id>"
    *            -> RUNNING_AGENT   "agent running  timeout=<n>s"
    *            -> GRADING         "-> grading     verdict=<v>"
    *            -> COMPLETED       "finished       completed  score=<x>  <elapsed>"
    *            -> FAILED          "finished       failed     error=<head>  <elapsed>"
    *            -> CANCELLED       "finished       cancelled  <elapsed>"

Everything else (SEEDING, EXTRACTING, CLEANING_UP) stays in ``harness.log``.

The watcher reads only ``state.json``; it never touches the scheduler or
trial runner directly. This is the same decoupling the old Rich progress
table used, just rendered as a flat event log.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from amplifier_evaluation.harness import state as state_io
from amplifier_evaluation.harness.schema import TrialSpec, TrialState
from amplifier_evaluation.harness.state import TrialStateRecord

REFRESH_INTERVAL_S = 1.0

# Width to which the "agent x task" label is padded so columns line up.
_LABEL_WIDTH = 50


def _label(spec: TrialSpec) -> str:
    s = f"{spec.agent.id} x {spec.task.id}"
    return s.ljust(_LABEL_WIDTH)[:_LABEL_WIDTH]


def _format_elapsed(seconds: float | None) -> str:
    if not seconds:
        return "0s"
    if seconds < 60:
        return f"{int(seconds)}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m"


def _stamp() -> str:
    return time.strftime("%H:%M:%S")


def _emit(line: str) -> None:
    print(line, flush=True)


def _verdict(rec: TrialStateRecord) -> str:
    ai = rec.ai_user or {}
    v = ai.get("verdict")
    return str(v) if v else "?"


def _score(rec: TrialStateRecord) -> str:
    g = rec.grader or {}
    s = g.get("overall_score")
    if isinstance(s, (int, float)):
        return f"{s:.2f}"
    return "-"


def _error_head(rec: TrialStateRecord) -> str:
    err = rec.error or ""
    head = err.strip().splitlines()[0] if err.strip() else "?"
    if len(head) > 120:
        head = head[:117] + "..."
    return head


def _print_for_state(spec: TrialSpec, rec: TrialStateRecord) -> None:
    """Emit one console line for an interesting state transition."""
    label = _label(spec)
    state = rec.state
    if state == TrialState.LAUNCHING.value:
        _emit(f"[{_stamp()}] {label} trial started")
    elif state == TrialState.INSTALLING.value:
        dtu = rec.dtu_id or "?"
        _emit(f"[{_stamp()}] {label} dtu launched   dtu_id={dtu}")
    elif state == TrialState.RUNNING_AGENT.value:
        timeout = getattr(spec.task, "timeout_s", None)
        suffix = f"timeout={int(timeout)}s" if timeout else ""
        _emit(f"[{_stamp()}] {label} agent running  {suffix}".rstrip())
    elif state == TrialState.GRADING.value:
        _emit(f"[{_stamp()}] {label} -> grading     verdict={_verdict(rec)}")
    elif state == TrialState.COMPLETED.value:
        _emit(
            f"[{_stamp()}] {label} finished       completed  "
            f"score={_score(rec)}  {_format_elapsed(rec.elapsed_s)}"
        )
    elif state == TrialState.FAILED.value:
        _emit(
            f"[{_stamp()}] {label} finished       failed     "
            f"error={_error_head(rec)}  {_format_elapsed(rec.elapsed_s)}"
        )
    elif state == TrialState.CANCELLED.value:
        _emit(
            f"[{_stamp()}] {label} finished       cancelled  "
            f"{_format_elapsed(rec.elapsed_s)}"
        )
    # SEEDING / EXTRACTING / CLEANING_UP / PENDING are intentionally silent.


# States whose first entry should produce a console line. Order matters for
# "first transition into" semantics: we replay every history entry once.
_INTERESTING: set[str] = {
    TrialState.LAUNCHING.value,
    TrialState.INSTALLING.value,
    TrialState.RUNNING_AGENT.value,
    TrialState.GRADING.value,
    TrialState.COMPLETED.value,
    TrialState.FAILED.value,
    TrialState.CANCELLED.value,
}


def _new_interesting_states(prev_seen: set[str], rec: TrialStateRecord) -> list[str]:
    """Return interesting states in `rec.history` that haven't been emitted yet,
    in history order."""
    fresh: list[str] = []
    for stage in rec.history:
        s: Any = stage.state if hasattr(stage, "state") else stage  # tolerate dicts
        if isinstance(s, dict):
            s = s.get("state")
        if not isinstance(s, str):
            continue
        if s in _INTERESTING and s not in prev_seen and s not in fresh:
            fresh.append(s)
    # The "current" state may not yet be in history (it is appended on transition);
    # cover that explicitly.
    if (
        rec.state in _INTERESTING
        and rec.state not in prev_seen
        and rec.state not in fresh
    ):
        fresh.append(rec.state)
    return fresh


async def render_events(
    specs: list[TrialSpec],
    trials_root: Path,
    stop_event: asyncio.Event,
) -> None:
    """Watch every trial's state.json and print high-level event lines.

    Runs until ``stop_event`` is set. Safe to start before any trial has
    written its state file (missing files are silently skipped).
    """
    seen: dict[str, set[str]] = {s.trial_id: set() for s in specs}
    while not stop_event.is_set():
        for spec in specs:
            d = trials_root / spec.trial_id
            rec = state_io.load_state(d)
            if rec is None:
                continue
            fresh = _new_interesting_states(seen[spec.trial_id], rec)
            for s in fresh:
                # Build a thin view of `rec` whose `state` is the transition
                # we are reporting on, so the printer can read the correct
                # payload (verdict, score, error) from the live record.
                rec.state = s  # safe; rec is local to this iteration
                _print_for_state(spec, rec)
                seen[spec.trial_id].add(s)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=REFRESH_INTERVAL_S)
        except asyncio.TimeoutError:
            continue
    # Final sweep so the last transitions land even if the watcher was woken
    # up before the scheduler wrote the terminal state.
    for spec in specs:
        d = trials_root / spec.trial_id
        rec = state_io.load_state(d)
        if rec is None:
            continue
        for s in _new_interesting_states(seen[spec.trial_id], rec):
            rec.state = s
            _print_for_state(spec, rec)
            seen[spec.trial_id].add(s)
