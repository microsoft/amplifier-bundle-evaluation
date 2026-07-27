"""Unit tests for `file-push` command construction and fail-loud guards.

The `amplifier-digital-twin file-push` CLI requires `--recursive` when any
source is a directory (without it a directory push delivers nothing), and
treats the destination of a plain-file push as an exact file path (so
`--recursive` must be omitted for files). These tests pin that contract for
both call sites that shell out to `file-push`:

- `harness.dtu.DTU.file_push`
- `grader.grader._push_mounts`

Both directory paths also carry a fail-loud guard: if the CLI reports
success but the directory did not land inside the DTU, the push raises
instead of proceeding silently (silently-empty mounts corrupt grading).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from amplifier_evaluation.grader import grader as grader_module
from amplifier_evaluation.grader.schema import Mount
from amplifier_evaluation.harness import dtu as dtu_module
from amplifier_evaluation.harness.dtu import CLI, DTU, CommandResult, DTUError


class FakeRun:
    """Stand-in for `dtu._run` that records argv and returns a fixed result."""

    def __init__(self, returncode: int = 0, stderr: str = ""):
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stderr = stderr

    async def __call__(self, args, *, timeout=None, env=None):
        self.calls.append(list(args))
        return (self.returncode, "", self.stderr)


class FakeExec:
    """Stand-in for `DTU.exec_cmd` (bound as an instance attribute)."""

    def __init__(self, returncode: int = 0):
        self.calls: list[list[str]] = []
        self.returncode = returncode

    async def __call__(self, command, *, timeout_s=None, stream_to_logfile=None):
        self.calls.append(list(command))
        return CommandResult(
            returncode=self.returncode, stdout="", stderr="", elapsed_s=0.0
        )


def _dtu() -> DTU:
    return DTU(id="dtu-test", profile_path="profile.yaml")


# ---------------------------------------------------------------------------
# DTU.file_push
# ---------------------------------------------------------------------------


def test_file_push_file_omits_recursive(tmp_path: Path, monkeypatch):
    src = tmp_path / "a.txt"
    src.write_text("hello", encoding="utf-8")
    run = FakeRun()
    monkeypatch.setattr(dtu_module, "_run", run)

    asyncio.run(_dtu().file_push(src, "/workspace/a.txt"))

    assert run.calls == [[CLI, "file-push", "dtu-test", str(src), "/workspace/a.txt"]]


def test_file_push_dir_adds_recursive_and_verifies(tmp_path: Path, monkeypatch):
    src = tmp_path / "data"
    src.mkdir()
    (src / "x.txt").write_text("x", encoding="utf-8")
    run = FakeRun()
    monkeypatch.setattr(dtu_module, "_run", run)
    dtu = _dtu()
    fake_exec = FakeExec(returncode=0)
    dtu.exec_cmd = fake_exec  # type: ignore[method-assign]

    asyncio.run(dtu.file_push(src, "/workspace/"))

    assert run.calls == [
        [CLI, "file-push", "--recursive", "dtu-test", str(src), "/workspace/"]
    ]
    # Post-push verification checks the landed directory (name preserved).
    assert len(fake_exec.calls) == 1
    shell, flag, script = fake_exec.calls[0]
    assert (shell, flag) == ("sh", "-c")
    assert "test -d /workspace/data" in script
    assert "ls -A" in script  # non-empty source requires non-empty destination


def test_file_push_empty_dir_skips_content_check(tmp_path: Path, monkeypatch):
    src = tmp_path / "empty"
    src.mkdir()
    monkeypatch.setattr(dtu_module, "_run", FakeRun())
    dtu = _dtu()
    fake_exec = FakeExec(returncode=0)
    dtu.exec_cmd = fake_exec  # type: ignore[method-assign]

    asyncio.run(dtu.file_push(src, "/workspace/"))

    script = fake_exec.calls[0][2]
    assert "test -d /workspace/empty" in script
    assert "ls -A" not in script


def test_file_push_dir_undelivered_raises(tmp_path: Path, monkeypatch):
    src = tmp_path / "data"
    src.mkdir()
    (src / "x.txt").write_text("x", encoding="utf-8")
    monkeypatch.setattr(dtu_module, "_run", FakeRun())
    dtu = _dtu()
    dtu.exec_cmd = FakeExec(returncode=1)  # type: ignore[method-assign]

    with pytest.raises(DTUError, match="missing or empty"):
        asyncio.run(dtu.file_push(src, "/workspace/"))


def test_file_push_cli_error_raises(tmp_path: Path, monkeypatch):
    src = tmp_path / "data"
    src.mkdir()
    monkeypatch.setattr(dtu_module, "_run", FakeRun(returncode=2, stderr="boom"))
    dtu = _dtu()
    fake_exec = FakeExec()
    dtu.exec_cmd = fake_exec  # type: ignore[method-assign]

    with pytest.raises(DTUError, match="file-push failed"):
        asyncio.run(dtu.file_push(src, "/workspace/"))
    assert fake_exec.calls == []  # no verification after a failed push


def test_file_push_missing_source_raises(tmp_path: Path, monkeypatch):
    run = FakeRun()
    monkeypatch.setattr(dtu_module, "_run", run)

    with pytest.raises(DTUError, match="source missing"):
        asyncio.run(_dtu().file_push(tmp_path / "nope", "/workspace/"))
    assert run.calls == []


# ---------------------------------------------------------------------------
# grader._push_mounts
# ---------------------------------------------------------------------------


class FakeCli:
    """Stand-in for `grader._run_cli` with per-call return codes."""

    def __init__(self, returncodes: list[int] | None = None):
        self.calls: list[list[str]] = []
        self.returncodes = list(returncodes or [])

    async def __call__(self, args):
        self.calls.append(list(args))
        rc = self.returncodes.pop(0) if self.returncodes else 0
        return (rc, "", "boom" if rc else "")


def test_push_mounts_file_omits_recursive(tmp_path: Path, monkeypatch):
    (tmp_path / "reference.json").write_text("{}", encoding="utf-8")
    cli = FakeCli()
    monkeypatch.setattr(grader_module, "_run_cli", cli)
    mounts = [Mount(source="reference.json", destination="/grader/reference.json")]

    asyncio.run(grader_module._push_mounts("dtu-x", mounts, tmp_path))

    assert cli.calls == [
        [
            "amplifier-digital-twin",
            "file-push",
            "dtu-x",
            str((tmp_path / "reference.json").resolve()),
            "/grader/reference.json",
        ]
    ]


def test_push_mounts_dir_adds_recursive_and_verifies(tmp_path: Path, monkeypatch):
    src = tmp_path / "refs"
    src.mkdir()
    (src / "answer.txt").write_text("42", encoding="utf-8")
    cli = FakeCli()
    monkeypatch.setattr(grader_module, "_run_cli", cli)
    mounts = [Mount(source="refs", destination="/grader/data/")]

    asyncio.run(grader_module._push_mounts("dtu-x", mounts, tmp_path))

    assert cli.calls[0] == [
        "amplifier-digital-twin",
        "file-push",
        "--recursive",
        "dtu-x",
        str(src.resolve()),
        "/grader/data/",
    ]
    # Post-push verification runs inside the DTU against the landed path.
    exec_call = cli.calls[1]
    assert exec_call[:5] == ["amplifier-digital-twin", "exec", "dtu-x", "--", "sh"]
    script = exec_call[6]
    assert "test -d /grader/data/refs" in script
    assert "ls -A" in script


def test_push_mounts_dir_undelivered_raises(tmp_path: Path, monkeypatch):
    src = tmp_path / "refs"
    src.mkdir()
    (src / "answer.txt").write_text("42", encoding="utf-8")
    cli = FakeCli(returncodes=[0, 1])  # push "succeeds", verification fails
    monkeypatch.setattr(grader_module, "_run_cli", cli)
    mounts = [Mount(source="refs", destination="/grader/data/")]

    with pytest.raises(RuntimeError, match="missing or empty"):
        asyncio.run(grader_module._push_mounts("dtu-x", mounts, tmp_path))


def test_push_mounts_push_failure_raises(tmp_path: Path, monkeypatch):
    (tmp_path / "reference.json").write_text("{}", encoding="utf-8")
    cli = FakeCli(returncodes=[2])
    monkeypatch.setattr(grader_module, "_run_cli", cli)
    mounts = [Mount(source="reference.json", destination="/grader/reference.json")]

    with pytest.raises(RuntimeError, match="file-push failed"):
        asyncio.run(grader_module._push_mounts("dtu-x", mounts, tmp_path))


def test_push_mounts_missing_source_raises(tmp_path: Path, monkeypatch):
    cli = FakeCli()
    monkeypatch.setattr(grader_module, "_run_cli", cli)
    mounts = [Mount(source="nope", destination="/grader/nope")]

    with pytest.raises(RuntimeError, match="mount source not found"):
        asyncio.run(grader_module._push_mounts("dtu-x", mounts, tmp_path))
    assert cli.calls == []
