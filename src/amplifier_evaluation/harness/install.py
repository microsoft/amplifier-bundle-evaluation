"""Install an agent into a running Digital Twin Universe instance.

Agents declare a single install pattern in `install.yaml`:

- `setup_cmds`: a list of shell commands to run inside an already-running DTU
  launched from the task's profile. Each command is run via `bash -lc` so
  heredocs and `$VAR` expansion work. The DTU is always launched from the
  task's own profile; agents customize that DTU at install time rather than
  shipping a parallel profile of their own.

`install.yaml` may declare `requires.env: [...]` -- host env vars that must
be present before installation begins. We validate them up front so trials
fail loudly instead of silently producing a broken DTU. The same list is
also used by `compose_launch_profile` to synthesize `passthrough.services`
entries so the agent's required vars actually reach the container without
the task profile having to enumerate every possible API key.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

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


def _required_env(agent: AgentSpec) -> list[str]:
    """Return the agent's declared `requires.env` list (empty if absent)."""
    requires = agent.install.get("requires") or {}
    needed = requires.get("env") or []
    if not isinstance(needed, list):
        return []
    return [v for v in needed if isinstance(v, str)]


def _service_name_for(env_var: str) -> str:
    """Derive a `passthrough.services` `name` from an env var name.

    Conventions matching the DTU profiles already in tree:
      OPENAI_API_KEY    -> openai
      ANTHROPIC_API_KEY -> anthropic
      MISTRAL_API_KEY   -> mistral
      GITHUB_TOKEN      -> github_token

    The `name` field is just a label inside the DTU profile; the actual
    forwarding is keyed on `key_env`. Keeping the convention consistent
    with existing profiles avoids surprising operators reading the merged
    profile we drop into the trial directory.
    """
    lowered = env_var.lower()
    for suffix in ("_api_key", "_token"):
        if lowered.endswith(suffix):
            return lowered[: -len(suffix)] if suffix == "_api_key" else lowered
    return lowered


def compose_launch_profile(
    agent: AgentSpec,
    task_profile_path: Path,
    output_path: Path,
) -> Path:
    """Synthesize a DTU profile that includes the agent's required env vars.

    Reads the task profile, ensures every var in `agent.install.requires.env`
    is covered by a `passthrough.services` entry (adding missing ones), and
    writes the merged profile to `output_path`. Returns `output_path`.

    Task profile entries always win on conflict (matched by `key_env`): a
    task author who deliberately configures a service entry shouldn't have
    it silently rewritten by the harness. We only *add* missing entries.

    If the agent has no `requires.env` and the task profile is already
    well-formed, the output is byte-for-byte equivalent to the input apart
    from YAML round-tripping. We still write it through so that the trial
    directory contains the exact profile that was launched.
    """
    raw = task_profile_path.read_text(encoding="utf-8")
    data: Any = yaml.safe_load(raw)
    if not isinstance(data, dict):
        raise InstallError(
            f"task profile {task_profile_path} did not parse to a mapping; "
            f"got {type(data).__name__}"
        )

    needed = _required_env(agent)
    if needed:
        passthrough = data.setdefault("passthrough", {})
        if not isinstance(passthrough, dict):
            raise InstallError(
                f"task profile {task_profile_path} has a non-mapping "
                f"`passthrough` block ({type(passthrough).__name__})"
            )
        services = passthrough.setdefault("services", [])
        if not isinstance(services, list):
            raise InstallError(
                f"task profile {task_profile_path} has a non-list "
                f"`passthrough.services` ({type(services).__name__})"
            )
        existing = {
            s.get("key_env")
            for s in services
            if isinstance(s, dict) and isinstance(s.get("key_env"), str)
        }
        added: list[str] = []
        for var in needed:
            if var in existing:
                continue
            services.append({"name": _service_name_for(var), "key_env": var})
            added.append(var)
        if added:
            logger.info(
                "compose_launch_profile: injected passthrough for %s into %s",
                added,
                output_path.name,
            )

    output_path.write_text(
        yaml.safe_dump(data, sort_keys=False, default_flow_style=False),
        encoding="utf-8",
    )
    return output_path


async def install_agent(
    agent: AgentSpec,
    dtu: DTU,
    *,
    log_to: Path | None = None,
    step_timeout_s: float = 1800.0,
) -> None:
    """Install `agent` into `dtu` by running its `setup_cmds`.

    Raises `InstallError` if a setup command fails.
    """
    cmds = agent.install.get("setup_cmds") or []
    if not isinstance(cmds, list) or not cmds:
        raise InstallError(
            f"agent {agent.id} install.yaml is missing `setup_cmds` (a list of "
            f"shell commands to run inside the task DTU)"
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
