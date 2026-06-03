"""Assembled evaluation harness entry point.

This file is intentionally short. It is the "example" wiring of the bricks
in the rest of `harness/`: loaders, the trial runner, the scheduler, and
the progress UI. Consumers that need different behaviour can either pass
overrides to `run()` or copy this file and edit it directly.

Usage from Python:

    from amplifier_evaluation.harness.run import run

    result = await run(
        agents_dir="amplifier-benchmark/agents",
        tasks_dir="amplifier-benchmark/tasks",
        selection=[("amplifier-foundation", "cpsc_recall_monitor")],
        output_dir="results/2026-05-26",
        max_parallel=2,
    )

From the command line, use the installable ``amplifier-evaluation run`` CLI
(``cli.py``), which wraps this ``run()``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from amplifier_evaluation.ai_user import AIUser
from amplifier_evaluation.extractor import Extractor
from amplifier_evaluation.grader import Grader

from amplifier_evaluation.harness import loaders
from amplifier_evaluation.harness.dtu import cli_available
from amplifier_evaluation.harness.events import render_events
from amplifier_evaluation.harness.scheduler import run_trials
from amplifier_evaluation.harness.schema import RunResult, TrialSpec


logger = logging.getLogger(__name__)


def _setup_logging(
    output_dir: Path,
    *,
    file_level: str = "INFO",
    console_level: str = "WARNING",
) -> Path:
    """Configure logging so detail goes to a file and the console stays quiet.

    All harness / DTU / bundle chatter is routed to ``<output_dir>/harness.log``
    at ``file_level``. The console (stderr) only receives ``console_level``
    and above so the event-log printer can own stdout without being drowned
    out by INFO chatter.

    Returns the path to the log file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "harness.log"

    root = logging.getLogger()
    # Wipe any pre-existing handlers (e.g. from a previous run() call in the
    # same process, or from a third-party basicConfig).
    for h in list(root.handlers):
        root.removeHandler(h)
    root.setLevel(logging.DEBUG)  # lowest; per-handler levels filter

    fmt = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(getattr(logging, file_level.upper(), logging.INFO))
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(getattr(logging, console_level.upper(), logging.WARNING))
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # Quiet the noisy bundle/load chatter; still visible at WARNING+ in the file.
    logging.getLogger("amplifier_foundation").setLevel(logging.WARNING)

    return log_path


def _build_trial_specs(
    agents: dict,
    tasks: dict,
    selection: list[tuple[str, str]],
    trials_per_pair: int,
    launch_variables: dict[str, str] | None = None,
) -> list[TrialSpec]:
    specs: list[TrialSpec] = []
    for agent_id, task_id in selection:
        if agent_id not in agents:
            raise KeyError(f"agent {agent_id!r} not found; available: {sorted(agents)}")
        if task_id not in tasks:
            raise KeyError(f"task {task_id!r} not found; available: {sorted(tasks)}")
        for n in range(1, trials_per_pair + 1):
            specs.append(
                TrialSpec(
                    agent=agents[agent_id],
                    task=tasks[task_id],
                    trial_number=n,
                    # Per-trial copy of the run-level dict so a caller can later
                    # mutate one trial without affecting the others.
                    launch_variables=(
                        dict(launch_variables) if launch_variables else None
                    ),
                )
            )
    return specs


def _is_secret_key(name: str) -> bool:
    upper = name.upper()
    return any(token in upper for token in ("TOKEN", "KEY", "SECRET", "PASSWORD"))


async def run(
    agents_dir: Path | str,
    tasks_dir: Path | str,
    selection: list[tuple[str, str]],
    output_dir: Path | str,
    *,
    trials_per_pair: int = 1,
    max_parallel: int = 2,
    show_progress: bool = True,
    run_id: str | None = None,
    launch_variables: dict[str, str] | None = None,
) -> RunResult:
    """Run a batch of evaluation trials end to end.

    Args:
        agents_dir: Directory containing agent subdirectories.
        tasks_dir: Directory containing task subdirectories.
        selection: Explicit (agent_id, task_id) pairs to evaluate.
        output_dir: Host directory where the run's results land.
        trials_per_pair: How many trials to run per (agent, task) pair.
        max_parallel: Concurrent trial cap.
        show_progress: Emit the high-level per-trial event log to stdout.
        run_id: Optional override for the run id (default: timestamp + uuid).
        launch_variables: Mapping of `KEY=value` pairs threaded to every
            trial as `amplifier-digital-twin launch --var KEY=value`. The
            DTU CLI substitutes ${KEY} in the profile, most commonly inside
            `url_rewrites:` blocks pointing at a local Gitea mirror.
    """
    if not cli_available():
        raise RuntimeError(
            "`amplifier-digital-twin` CLI is not on PATH; install it before running."
        )

    agents = loaders.discover_agents(agents_dir)
    tasks = loaders.discover_tasks(tasks_dir)
    specs = _build_trial_specs(
        agents, tasks, selection, trials_per_pair, launch_variables=launch_variables
    )

    if run_id is None:
        run_id = (
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-")
            + uuid.uuid4().hex[:6]
        )

    out = Path(output_dir).resolve()
    trials_root = out / "trials"
    trials_root.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()

    # Persist the run plan up front so observers can correlate trial dirs.
    # Launch variables are recorded for debuggability; values are redacted
    # when the key name looks like a secret (token/key/secret/password).
    launch_var_record: dict[str, str] = {}
    if launch_variables:
        for k, v in launch_variables.items():
            launch_var_record[k] = "<redacted>" if _is_secret_key(k) else v
    (out / "run.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "agents_dir": str(Path(agents_dir).resolve()),
                "tasks_dir": str(Path(tasks_dir).resolve()),
                "output_dir": str(out),
                "started_at": started_at,
                "max_parallel": max_parallel,
                "trials_per_pair": trials_per_pair,
                "selection": [{"agent": a, "task": t} for a, t in selection],
                "launch_variables": launch_var_record,
                "trials": [s.trial_id for s in specs],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # One AIUser / Grader / Extractor shared across all trials; setup() is
    # expensive (loads + composes bundles) so we pay it once.
    logger.info("preparing AI User, Grader, Extractor bundles...")
    ai_user = AIUser()
    grader = Grader()
    extractor = Extractor()
    await asyncio.gather(ai_user.setup(), grader.setup(), extractor.setup())
    logger.info(
        "bundles ready; starting %d trials (max_parallel=%d)", len(specs), max_parallel
    )

    stop_event = asyncio.Event()
    progress_task: asyncio.Task | None = None
    if show_progress:
        progress_task = asyncio.create_task(
            render_events(specs, trials_root, stop_event),
            name="harness:events",
        )

    try:
        results = await run_trials(
            specs,
            trials_root=trials_root,
            ai_user=ai_user,
            grader=grader,
            extractor=extractor,
            max_parallel=max_parallel,
        )
    finally:
        stop_event.set()
        if progress_task is not None:
            try:
                await asyncio.wait_for(progress_task, timeout=5.0)
            except asyncio.TimeoutError:
                progress_task.cancel()

    finished_at = datetime.now(timezone.utc).isoformat()

    run_result = RunResult(
        run_id=run_id,
        output_dir=out,
        started_at=started_at,
        finished_at=finished_at,
        trials=results,
    )

    # Top-level summary of the whole run.
    summary = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "counts": run_result.summary_counts,
        "trials": [asdict(t) for t in results],
    }
    (out / "summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )

    return run_result
