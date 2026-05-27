#!/usr/bin/env python3
"""Run the amplifier-benchmark.

By default, runs every permutation of (agent, task) discovered under
``amplifier-benchmark/agents`` and ``amplifier-benchmark/tasks``, and writes
results to ``results/<run-id>/`` in the current working directory.

Examples:

    # Run the full matrix (foreground; safe for interactive sessions)
    uv run scripts/run_benchmark.py

    # Restrict to a subset
    uv run scripts/run_benchmark.py --agent amplifier-foundation --task chiptune_generator

    # Bump parallelism and trial count
    uv run scripts/run_benchmark.py --max-parallel 4 --trials-per-pair 3

How to launch this script in the background safely
--------------------------------------------------

A full matrix run takes 20+ minutes and you will usually want to background
it so you can poll progress. The combination that actually survives a parent
shell going away or being signaled is::

    setsid nohup uv run scripts/run_benchmark.py \\
        > scripts/_run.out 2>&1 < /dev/null &
    disown

What each piece does and why each is necessary:

- ``setsid``  -- runs the script in a fresh session and process group.
  Without this, signals sent to the launching shell's process group
  (for example, SIGTERM when an outer tool times out and kills its
  group) will reach the script even if it is backgrounded.
- ``nohup``   -- ignores SIGHUP so the script survives the launching
  shell exiting normally. nohup alone is NOT enough: it does not
  protect against SIGTERM/SIGKILL sent to a shared process group,
  which is the real failure mode this script has been bitten by.
- ``> scripts/_run.out 2>&1 < /dev/null`` -- detach all stdio. The
  script keeps writing event lines to that file; the launching
  terminal can come and go.
- ``&`` then ``disown`` -- background and remove from the shell's
  job table, so the shell does not try to clean it up on exit.

A bare ``nohup uv run ... &; disown`` is NOT sufficient. It was tried
in this codebase and the script was killed mid-flight by a sibling
tool invocation's process-group cleanup. ``setsid`` is what isolates
the run.

If you forget all of this and run it foreground, that also works. The
hazard only appears when you background it and then run other commands
that share the same process group lineage.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import click

from amplifier_evaluation.harness import loaders
from amplifier_evaluation.harness.run import _setup_logging, run

# This script lives at <repo>/scripts/run_benchmark.py. The benchmark assets
# live at <repo>/amplifier-benchmark/{agents,tasks}.
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AGENTS_DIR = REPO_ROOT / "amplifier-benchmark" / "agents"
DEFAULT_TASKS_DIR = REPO_ROOT / "amplifier-benchmark" / "tasks"


@click.command(context_settings={"show_default": True})
@click.option(
    "--agents-dir",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=DEFAULT_AGENTS_DIR,
    help="Directory containing agent subdirectories.",
)
@click.option(
    "--tasks-dir",
    type=click.Path(file_okay=False, exists=True, path_type=Path),
    default=DEFAULT_TASKS_DIR,
    help="Directory containing task subdirectories.",
)
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("results"),
    help="Parent directory for run output. A timestamped subdirectory is created inside it.",
)
@click.option(
    "--agent",
    "agent_filter",
    multiple=True,
    help="Restrict to these agents (repeatable). Default: all discovered agents.",
)
@click.option(
    "--task",
    "task_filter",
    multiple=True,
    help="Restrict to these tasks (repeatable). Default: all discovered tasks.",
)
@click.option(
    "--max-parallel",
    type=int,
    default=2,
    help="Concurrent trial cap.",
)
@click.option(
    "--trials-per-pair",
    type=int,
    default=1,
    help="How many trials to run per (agent, task) pair.",
)
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Suppress per-trial event lines on the console (run header/footer only).",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Echo INFO logs to the console in addition to the per-trial event lines.",
)
@click.option(
    "--log-level",
    default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Log level written to <output_dir>/<run_id>/harness.log.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print the selection that would be run and exit.",
)
def main(
    agents_dir: Path,
    tasks_dir: Path,
    output_dir: Path,
    agent_filter: tuple[str, ...],
    task_filter: tuple[str, ...],
    max_parallel: int,
    trials_per_pair: int,
    quiet: bool,
    verbose: bool,
    log_level: str,
    dry_run: bool,
) -> None:
    """Run the amplifier-benchmark over every (agent, task) permutation."""
    agents = loaders.discover_agents(agents_dir)
    tasks = loaders.discover_tasks(tasks_dir)

    selected_agents = list(agent_filter) if agent_filter else sorted(agents)
    selected_tasks = list(task_filter) if task_filter else sorted(tasks)

    unknown_agents = [a for a in selected_agents if a not in agents]
    unknown_tasks = [t for t in selected_tasks if t not in tasks]
    if unknown_agents:
        raise click.BadParameter(
            f"unknown agent(s): {unknown_agents}; available: {sorted(agents)}"
        )
    if unknown_tasks:
        raise click.BadParameter(
            f"unknown task(s): {unknown_tasks}; available: {sorted(tasks)}"
        )

    selection: list[tuple[str, str]] = list(product(selected_agents, selected_tasks))

    click.echo(
        f"Discovered {len(agents)} agent(s) and {len(tasks)} task(s). "
        f"Will run {len(selection)} pair(s) x {trials_per_pair} trial(s) "
        f"= {len(selection) * trials_per_pair} trials."
    )
    for agent_id, task_id in selection:
        click.echo(f"  - {agent_id} x {task_id}")

    if dry_run:
        click.echo("Dry run; exiting before launching trials.")
        return

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_output = (output_dir / run_id).resolve()
    run_output.mkdir(parents=True, exist_ok=True)

    log_path = _setup_logging(
        run_output,
        file_level=log_level,
        console_level="INFO" if verbose else "WARNING",
    )

    click.echo(
        f"benchmark run {run_id}\n"
        f"  {len(set(a for a, _ in selection))} agent(s) x "
        f"{len(set(t for _, t in selection))} task(s) x "
        f"{trials_per_pair} trial(s) = {len(selection) * trials_per_pair} trials, "
        f"max_parallel={max_parallel}\n"
        f"  output: {run_output}\n"
        f"  logs:   {log_path}\n"
    )

    result = asyncio.run(
        run(
            agents_dir=agents_dir,
            tasks_dir=tasks_dir,
            selection=selection,
            output_dir=run_output,
            trials_per_pair=trials_per_pair,
            max_parallel=max_parallel,
            show_progress=not quiet,
            run_id=run_id,
        )
    )

    counts = result.summary_counts
    click.echo(f"\nRun {result.run_id} finished.")
    click.echo(f"  output: {result.output_dir}")
    click.echo(f"  counts: {counts}")
    failed = counts.get("failed", 0) + counts.get("cancelled", 0)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
