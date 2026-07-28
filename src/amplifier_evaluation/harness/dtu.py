"""Thin async wrapper over the `amplifier-digital-twin` CLI.

The harness shells out to the published CLI rather than importing the engine
directly. This keeps the dependency surface tiny and lets us swap in a
different DTU backend (or mock) by replacing this one file.

All methods are async and use `asyncio.create_subprocess_exec` so they don't
block the event loop while many trials run concurrently.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


CLI = "amplifier-digital-twin"


def _file_push_args(instance_id: str, src: Path, destination: str) -> list[str]:
    """Build the `file-push` argv for one source path.

    The CLI requires `--recursive` when the source is a directory. It must
    be OMITTED for plain files: with `--recursive` the CLI treats the
    destination as a parent directory (`dest/<basename>`) instead of an
    exact file path, which would break single-file pushes.
    """
    args = [CLI, "file-push"]
    if src.is_dir():
        args.append("--recursive")
    args.extend([instance_id, str(src), destination])
    return args


def _pushed_dir_root(src: Path, destination: str) -> str:
    """Remote path where a directory push lands.

    The CLI preserves the source directory *name* under the destination
    (`cp -r` convention): pushing `data/` to `/workspace/` creates
    `/workspace/data/`.
    """
    return f"{destination.rstrip('/')}/{src.name}"


def _dir_check_script(src: Path, remote_root: str) -> str:
    """Shell script verifying a pushed directory actually landed in the DTU.

    Checks the remote root exists and, when the source has entries, that
    the remote root is non-empty. Guards against the CLI reporting success
    while delivering nothing (silently-empty mounts corrupt grading).
    """
    quoted = shlex.quote(remote_root)
    script = f"test -d {quoted}"
    if any(src.iterdir()):
        script += f' && [ -n "$(ls -A {quoted})" ]'
    return script


class DTUError(RuntimeError):
    """Raised when a DTU CLI invocation fails."""

    def __init__(
        self, message: str, *, returncode: int | None = None, stderr: str = ""
    ):
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


@dataclass
class CommandResult:
    """Outcome of one `dtu.exec_cmd()` call."""

    returncode: int
    stdout: str
    stderr: str
    elapsed_s: float


async def _run(
    args: list[str],
    *,
    timeout: float | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    """Run a CLI command, return (returncode, stdout, stderr)."""
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    logger.debug("dtu exec: %s", " ".join(args))
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=proc_env,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise DTUError(
            f"DTU command timed out after {timeout}s: {' '.join(args)}",
            returncode=None,
        ) from None
    return (
        proc.returncode or 0,
        stdout_b.decode("utf-8", errors="replace"),
        stderr_b.decode("utf-8", errors="replace"),
    )


def cli_available() -> bool:
    """Quick check that the DTU CLI is on PATH."""
    return shutil.which(CLI) is not None


def _unwrap_exec_envelope(rc: int, stdout: str, stderr: str) -> tuple[int, str, str]:
    """Unwrap the DTU CLI's `exec` JSON result envelope, if present.

    The DTU CLI's `exec` in JSON mode (the default, and the mode this
    harness uses) reports the INNER command's result as a JSON envelope on
    stdout — {"id", "command", "exit_code", "stdout", "stderr"} — and exits
    0 itself; only the opt-in `--stream` mode propagates the inner exit
    code. Without unwrapping, `CommandResult.returncode` is the CLI
    process's exit code, so every caller that checks it (notably
    `install_agent`'s fail-loud setup_cmds check, install.py:171) tests the
    WRONG LAYER: an inner command can fail with exit 1 and the trial
    proceeds. This is not hypothetical — in parity-eval run 20260728T105215Z
    all six trials recorded a FAILED in-DTU code-identity gate
    ("exit_code": 1 in the envelope, `--- exit 0 ---` outer marker) and ran
    to full metered completion anyway.

    Unwrap only when the shape matches: outer success, stdout is one JSON
    object carrying at least {command, exit_code, stdout, stderr} with an
    int exit_code. Everything else passes through untouched: outer CLI
    failures (nonzero rc, timeouts, container gone), `--stream`-style plain
    output, JSON command output lacking the envelope keys, and
    mock/alternative backends that don't wrap. Caveat: the CLI multiplexes
    data and control on one stdout, so an inner command whose own output
    exactly matches the envelope shape (the four keys with an int
    exit_code) WILL be unwrapped — that ambiguity is inherent to the
    envelope protocol and cannot be resolved on this side.
    """
    if rc != 0:
        return rc, stdout, stderr
    s = stdout.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return rc, stdout, stderr
    try:
        envelope = json.loads(s)
    except json.JSONDecodeError:
        return rc, stdout, stderr
    if not isinstance(envelope, dict) or not {
        "command",
        "exit_code",
        "stdout",
        "stderr",
    } <= set(envelope):
        return rc, stdout, stderr
    inner_rc = envelope.get("exit_code")
    if not isinstance(inner_rc, int):
        return rc, stdout, stderr
    inner_stderr = str(envelope.get("stderr") or "")
    if stderr.strip():
        inner_stderr = f"{inner_stderr}\n{stderr}" if inner_stderr else stderr
    return inner_rc, str(envelope.get("stdout") or ""), inner_stderr


@dataclass
class DTU:
    """A handle to one running Digital Twin Universe instance."""

    id: str
    profile_path: str

    # ---- lifecycle ----------------------------------------------------------

    @classmethod
    async def launch(
        cls,
        profile_path: Path | str,
        *,
        name: str | None = None,
        variables: dict[str, str] | None = None,
        launch_timeout_s: float = 600.0,
    ) -> "DTU":
        """Launch a new DTU instance from a profile.

        `name` is set deterministically when omitted so callers always know
        the resulting id up front. After launch we parse the CLI's JSON output
        to validate it actually came up.
        """
        if not cli_available():
            raise DTUError(f"`{CLI}` is not on PATH")

        if name is None:
            name = f"dtu-{uuid.uuid4().hex[:8]}"

        args = [CLI, "launch", "--name", name]
        if variables:
            for k, v in variables.items():
                args.extend(["--var", f"{k}={v}"])
        args.append(str(profile_path))

        rc, stdout, stderr = await _run(args, timeout=launch_timeout_s)
        if rc != 0:
            raise DTUError(
                f"DTU launch failed (exit {rc}): {stderr.strip() or stdout.strip()}",
                returncode=rc,
                stderr=stderr,
            )

        # Parse the CLI's last stdout line as JSON to confirm the launch and
        # extract the instance id. We rely on `--name` to control the id, so
        # the fallback is safe, but log loudly when we use it: that means the
        # CLI changed its output shape and our parser is out of date.
        instance_id = name
        parsed_id: str | None = None
        last_line = stdout.strip().splitlines()[-1] if stdout.strip() else ""
        try:
            payload = json.loads(last_line)
            if isinstance(payload, dict):
                for key in ("id", "container_id", "name"):
                    if payload.get(key):
                        parsed_id = str(payload[key])
                        break
        except json.JSONDecodeError:
            pass

        if parsed_id is None:
            logger.warning(
                "dtu launch: could not extract id from CLI output; "
                "falling back to --name=%s. Last stdout line: %r",
                name,
                last_line[:200],
            )
        else:
            instance_id = parsed_id

        logger.info("dtu launched: %s (profile=%s)", instance_id, profile_path)
        return cls(id=instance_id, profile_path=str(profile_path))

    async def destroy(self, *, timeout_s: float = 120.0) -> None:
        """Stop and delete the DTU. Idempotent: missing instance is a no-op."""
        rc, _stdout, stderr = await _run([CLI, "destroy", self.id], timeout=timeout_s)
        if rc != 0:
            # Don't raise on cleanup failures - log and move on.
            logger.warning(
                "dtu destroy %s returned %s: %s", self.id, rc, stderr.strip()
            )

    # ---- operations ---------------------------------------------------------

    async def exec_cmd(
        self,
        command: list[str],
        *,
        timeout_s: float | None = 600.0,
        stream_to_logfile: Path | None = None,
    ) -> CommandResult:
        """Run a command inside the DTU. Returns full stdout/stderr.

        `command` is the raw argv; the CLI separates it with `--`.
        """
        import time

        args = [CLI, "exec"]
        if timeout_s is None:
            args.extend(["--timeout", "none"])
        else:
            args.extend(["--timeout", str(int(timeout_s))])
        args.append(self.id)
        args.append("--")
        args.extend(command)

        start = time.monotonic()
        # We use the CLI's own timeout for the inner command; add slack for the
        # outer wait so the CLI can report properly.
        outer = (timeout_s + 60.0) if timeout_s is not None else None
        rc, stdout, stderr = await _run(args, timeout=outer)
        rc, stdout, stderr = _unwrap_exec_envelope(rc, stdout, stderr)
        elapsed = time.monotonic() - start

        if stream_to_logfile is not None:
            try:
                stream_to_logfile.parent.mkdir(parents=True, exist_ok=True)
                with stream_to_logfile.open("a", encoding="utf-8") as f:
                    f.write(f"$ {' '.join(command)}\n")
                    f.write(stdout)
                    if stderr:
                        f.write("\n--- stderr ---\n")
                        f.write(stderr)
                    f.write(f"\n--- exit {rc} ({elapsed:.1f}s) ---\n\n")
            except OSError as exc:
                logger.warning("could not append to %s: %s", stream_to_logfile, exc)

        return CommandResult(
            returncode=rc, stdout=stdout, stderr=stderr, elapsed_s=elapsed
        )

    async def file_push(
        self,
        source: Path | str,
        destination: str,
        *,
        timeout_s: float = 300.0,
    ) -> None:
        """Push a single host path (file or directory) into the DTU.

        Directory sources are pushed with `--recursive` (the CLI requires
        it for directories; without it a directory push delivers nothing).
        Per the CLI's `cp -r` convention the directory *name* is preserved:
        pushing `data/` to `/workspace/` creates `/workspace/data/`.

        After a directory push the destination is verified inside the DTU.
        A push that "succeeds" but delivers nothing raises DTUError instead
        of proceeding silently -- empty mounts corrupt everything downstream
        (e.g. graders scoring an empty workspace).
        """
        src = Path(source)
        if not src.exists():
            raise DTUError(f"file-push source missing: {src}")
        rc, _stdout, stderr = await _run(
            _file_push_args(self.id, src, destination),
            timeout=timeout_s,
        )
        if rc != 0:
            raise DTUError(
                f"file-push failed: {src} -> {self.id}:{destination} "
                f"(exit {rc}): {stderr.strip()}",
                returncode=rc,
                stderr=stderr,
            )
        if src.is_dir():
            remote_root = _pushed_dir_root(src, destination)
            check = await self.exec_cmd(
                ["sh", "-c", _dir_check_script(src, remote_root)],
                timeout_s=60.0,
            )
            if check.returncode != 0:
                raise DTUError(
                    f"file-push reported success but {self.id}:{remote_root} "
                    f"is missing or empty (source: {src}); the directory was "
                    f"not delivered into the DTU",
                    returncode=check.returncode,
                    stderr=check.stderr,
                )

    async def file_pull(
        self,
        source: str,
        destination: Path | str,
        *,
        timeout_s: float = 300.0,
    ) -> None:
        """Pull a path out of the DTU to a host destination."""
        dest = Path(destination)
        dest.parent.mkdir(parents=True, exist_ok=True)
        rc, _stdout, stderr = await _run(
            [CLI, "file-pull", self.id, source, str(dest)],
            timeout=timeout_s,
        )
        if rc != 0:
            raise DTUError(
                f"file-pull failed: {self.id}:{source} -> {dest} "
                f"(exit {rc}): {stderr.strip()}",
                returncode=rc,
                stderr=stderr,
            )
