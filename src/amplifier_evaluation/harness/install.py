"""Install an agent into a running Digital Twin Universe instance.

Agents declare one of two install patterns in `install.yaml`:

- `setup_cmds`: a list of shell commands to run inside an already-running DTU
  launched from the task's profile. Each command is run via `bash -lc` so
  heredocs and `$VAR` expansion work. Used by agents that install on top of
  a generic task environment (e.g. `amplifier-foundation`).

- `dtu_profile`: a path to a Digital Twin Universe profile that already has
  the agent baked in. In this mode there is nothing for `install_agent` to
  do; the caller (the trial runner) is responsible for launching with that
  profile instead of the task's profile.

Either way, `install.yaml` may declare `requires.env: [...]` — host env vars
that must be present before installation begins. We validate them up front so
trials fail loudly instead of silently producing a broken DTU.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from amplifier_evaluation.harness.dtu import DTU
from amplifier_evaluation.harness.schema import AgentSpec

logger = logging.getLogger(__name__)


class InstallError(RuntimeError):
    pass


def verify_env(agent: AgentSpec) -> list[str]:
    """Return the list of `requires.env` vars that are missing from `os.environ`."""
    requires = agent.install.get("requires") or {}
    needed = requires.get("env") or []
    if not isinstance(needed, list):
        return []
    return [v for v in needed if not os.environ.get(v)]


def select_profile_path(agent: AgentSpec, task_profile: Path) -> Path:
    """Pick the DTU profile to launch with for this (agent, task) pair.

    If the agent declares `dtu_profile:`, that path wins; otherwise the task's
    profile is used. Agent profile paths can be:

      - absolute, or
      - relative to the current working directory, or
      - relative to the agent's own directory.

    Anything else is a configuration error. We intentionally do NOT walk
    arbitrary ancestor directories: an unrelated file with the same name
    several levels up would be silently picked, which is surprising and
    unsafe. If the agent's profile lives outside its own directory, the
    agent author should declare an absolute path.
    """
    raw = agent.install.get("dtu_profile")
    if not raw:
        return task_profile

    raw_path = Path(raw)
    if raw_path.is_absolute():
        if raw_path.is_file():
            return raw_path.resolve()
        raise InstallError(
            f"agent {agent.id} declares dtu_profile={raw!r} but no file "
            f"exists at that absolute path."
        )

    # Relative path: try cwd, then the agent's own directory. Nothing else.
    candidates = [Path(raw), agent.dir / raw]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    raise InstallError(
        f"agent {agent.id} declares dtu_profile={raw!r} but it could not be "
        f"found relative to the cwd ({Path.cwd()}) or the agent directory "
        f"({agent.dir}). Use an absolute path if the profile lives elsewhere."
    )


async def install_agent(
    agent: AgentSpec,
    dtu: DTU,
    *,
    log_to: Path | None = None,
    step_timeout_s: float = 1800.0,
) -> None:
    """Install `agent` into `dtu`. No-op for agents using the `dtu_profile`
    pattern, since that profile already has the agent.

    Raises `InstallError` if a setup command fails.
    """
    if agent.install_mode == "dtu_profile":
        logger.info("agent %s uses dtu_profile mode; no in-DTU install", agent.id)
        return

    cmds = agent.install.get("setup_cmds") or []
    if not isinstance(cmds, list) or not cmds:
        raise InstallError(
            f"agent {agent.id} install.yaml has install_mode=setup_cmds but no setup_cmds"
        )

    for i, cmd in enumerate(cmds, start=1):
        if not isinstance(cmd, str):
            raise InstallError(f"agent {agent.id} setup_cmds[{i}] is not a string")
        logger.info("agent install [%d/%d]: %.80s", i, len(cmds), cmd.splitlines()[0])
        result = await dtu.exec_cmd(
            ["bash", "-lc", cmd],
            timeout_s=step_timeout_s,
            stream_to_logfile=log_to,
        )
        if result.returncode != 0:
            raise InstallError(
                f"agent {agent.id} setup_cmds[{i}] failed (exit {result.returncode}):\n"
                f"  cmd: {cmd}\n"
                f"  stderr: {result.stderr.strip()[:2000]}"
            )
