# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
"""Amplifier Evaluation CLI.

Installable console entry point for the evaluation bundle. Exposes the
amplifier-benchmark runner as ``amplifier-evaluation run``.

The benchmark assets (agents and tasks) live in an ``amplifier-benchmark/``
directory. When invoked from a checkout of this repo the defaults resolve
automatically; otherwise pass ``--agents-dir`` and ``--tasks-dir``.

Selection is either implicit (the cartesian product of ``--agent`` x ``--task``
filters, defaulting to everything discovered) or explicit (one or more
``--pair agent:task``). ``--launch-var KEY=VALUE`` forwards values to every
trial's DTU launch; ``--run-id`` pins the output subdirectory name.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import click

from amplifier_evaluation.harness import loaders
from amplifier_evaluation.harness.resources import builtin_agents_dir, builtin_tasks_dir
from amplifier_evaluation.harness.run import _setup_logging
from amplifier_evaluation.harness.run import run as run_trials

# Default benchmark asset locations. Prefer the benchmark suite that ships with
# the package (wheel force-include, or the repo-root `amplifier-benchmark/` in a
# source checkout) so `amplifier-evaluation run` works out of the box with no
# flags. Fall back to a CWD-relative path if the bundled suite is somehow absent.
DEFAULT_AGENTS_DIR = builtin_agents_dir() or Path("amplifier-benchmark/agents")
DEFAULT_TASKS_DIR = builtin_tasks_dir() or Path("amplifier-benchmark/tasks")


def _parse_pairs(raw: tuple[str, ...]) -> list[tuple[str, str]]:
    """Parse ``agent:task`` strings into (agent, task) tuples, order preserved."""
    pairs: list[tuple[str, str]] = []
    for value in raw:
        agent, sep, task = value.partition(":")
        agent, task = agent.strip(), task.strip()
        if not sep or not agent or not task:
            raise click.BadParameter(f"--pair must be agent:task, got {value!r}")
        pairs.append((agent, task))
    return pairs


def _parse_launch_vars(raw: tuple[str, ...]) -> dict[str, str]:
    """Parse ``KEY=VALUE`` strings into a dict. Later keys win on conflict."""
    out: dict[str, str] = {}
    for value in raw:
        key, sep, val = value.partition("=")
        key = key.strip()
        if not sep or not key:
            raise click.BadParameter(f"--launch-var must be KEY=VALUE, got {value!r}")
        out[key] = val
    return out


@click.group()
@click.version_option(package_name="amplifier-bundle-evaluation")
def main() -> None:
    """Amplifier Evaluation: run benchmarks across the Amplifier ecosystem."""


@main.command(name="run", context_settings={"show_default": True})
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
    help="Parent directory for run output. A subdirectory named after the run id is created inside it.",
)
@click.option(
    "--agent",
    "agent_filter",
    multiple=True,
    help="Restrict to these agents (repeatable). Default: all discovered agents. Mutually exclusive with --pair.",
)
@click.option(
    "--task",
    "task_filter",
    multiple=True,
    help="Restrict to these tasks (repeatable). Default: all discovered tasks. Mutually exclusive with --pair.",
)
@click.option(
    "--pair",
    "pair_raw",
    multiple=True,
    help="Explicit agent:task pair to evaluate (repeatable). Mutually exclusive with --agent/--task.",
)
@click.option(
    "--launch-var",
    "launch_var_raw",
    multiple=True,
    help=(
        "KEY=VALUE forwarded to `amplifier-digital-twin launch --var KEY=VALUE` "
        "for every trial (repeatable). Used to inject e.g. a Gitea URL/token for "
        "profile url_rewrites substitution."
    ),
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
    "--run-id",
    default=None,
    help="Run id, also used as the output subdirectory name. Default: UTC timestamp.",
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
def run(
    agents_dir: Path,
    tasks_dir: Path,
    output_dir: Path,
    agent_filter: tuple[str, ...],
    task_filter: tuple[str, ...],
    pair_raw: tuple[str, ...],
    launch_var_raw: tuple[str, ...],
    max_parallel: int,
    trials_per_pair: int,
    run_id: str | None,
    quiet: bool,
    verbose: bool,
    log_level: str,
    dry_run: bool,
) -> None:
    """Run the amplifier-benchmark over a selection of (agent, task) pairs."""
    agents = loaders.discover_agents(agents_dir)
    tasks = loaders.discover_tasks(tasks_dir)

    # Selection: explicit --pair, or the product of --agent x --task filters.
    if pair_raw:
        if agent_filter or task_filter:
            raise click.BadParameter("--pair cannot be combined with --agent/--task")
        selection: list[tuple[str, str]] = _parse_pairs(pair_raw)
    else:
        selected_agents = list(agent_filter) if agent_filter else sorted(agents)
        selected_tasks = list(task_filter) if task_filter else sorted(tasks)
        selection = list(product(selected_agents, selected_tasks))

    unknown_agents = sorted({a for a, _ in selection if a not in agents})
    unknown_tasks = sorted({t for _, t in selection if t not in tasks})
    if unknown_agents:
        raise click.BadParameter(
            f"unknown agent(s): {unknown_agents}; available: {sorted(agents)}"
        )
    if unknown_tasks:
        raise click.BadParameter(
            f"unknown task(s): {unknown_tasks}; available: {sorted(tasks)}"
        )

    launch_variables = _parse_launch_vars(launch_var_raw)

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

    run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
        run_trials(
            agents_dir=agents_dir,
            tasks_dir=tasks_dir,
            selection=selection,
            output_dir=run_output,
            trials_per_pair=trials_per_pair,
            max_parallel=max_parallel,
            show_progress=not quiet,
            run_id=run_id,
            launch_variables=launch_variables or None,
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
