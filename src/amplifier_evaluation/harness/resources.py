"""Locate the benchmark assets that ship with this package.

The `amplifier-benchmark/` suite (agents + tasks) is shipped two ways:

  - Installed wheel: force-included at ``amplifier_evaluation/benchmark/`` (see
    ``[tool.hatch.build.targets.wheel.force-include]`` in pyproject.toml).
  - Editable / source checkout: the repo-root ``amplifier-benchmark/`` directory.

`builtin_benchmark_dir()` resolves whichever is present so the CLI and library
can run the built-in suite out of the box, with no external path needed.
"""

from __future__ import annotations

from pathlib import Path


def _has_suite(d: Path) -> bool:
    return (d / "agents").is_dir() and (d / "tasks").is_dir()


def builtin_benchmark_dir() -> Path | None:
    """Return the directory holding the bundled benchmark suite, or None.

    The returned directory contains ``agents/`` and ``tasks/`` subdirectories.
    """
    # 1. Packaged location (wheel install / force-included next to the package).
    packaged = Path(__file__).resolve().parent.parent / "benchmark"
    if _has_suite(packaged):
        return packaged

    # 2. Editable / source checkout: walk up to the repo root holding
    #    `amplifier-benchmark/`.
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "amplifier-benchmark"
        if _has_suite(candidate):
            return candidate

    return None


def builtin_agents_dir() -> Path | None:
    """Return the bundled ``agents/`` directory, or None if not shipped."""
    base = builtin_benchmark_dir()
    return (base / "agents") if base is not None else None


def builtin_tasks_dir() -> Path | None:
    """Return the bundled ``tasks/`` directory, or None if not shipped."""
    base = builtin_benchmark_dir()
    return (base / "tasks") if base is not None else None
