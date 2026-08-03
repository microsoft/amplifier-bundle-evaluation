"""Unit tests for the DTU CLI exec JSON-envelope unwrap (fail-loud setup_cmds).

Current DTU CLI versions report the INNER command's result as a JSON envelope
on stdout ({id, command, exit_code, stdout, stderr}) and exit 0 themselves.
`install_agent` checks `CommandResult.returncode`; without unwrapping it tests
the CLI process, not the command — a failed in-DTU gate is recorded but never
enforced. Observed live (parity-eval run 20260728T105215Z): all six trials
recorded a FAILED code-identity gate (envelope "exit_code": 1) and ran to
full metered completion.

These tests are composed-state: the failing case drives the REAL envelope
recorded in that run through `install_agent` end-to-end and asserts the
InstallError actually fires.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from amplifier_evaluation.harness.dtu import DTU, _unwrap_exec_envelope
from amplifier_evaluation.harness.install import InstallError, install_agent
from amplifier_evaluation.harness.schema import AgentSpec

# Verbatim shape (abridged stdout) of the envelope recorded in
# parity-eval run 20260728T105215Z, trial anthropic-skills-prefix__pdf-hr-q4__trial-1,
# install.log setup_cmds[6] — the gate that failed but did not abort.
REAL_FAILED_ENVELOPE = json.dumps(
    {
        "id": "dtu-ce952038",
        "command": "bash -lc 'set -e\\n...in-session injection + placement gates...'",
        "exit_code": 1,
        "stdout": (
            "--- in-session injection + placement gates ---\n"
            "RESOLVED-SHA skills-prefix-mirror 2fadd3072fd28a6fa74db926cfc99529d52c2b23\n"
            "throwaway run to activate modules + capture behavioral evidence (~cents):\n"
        ),
        "stderr": (
            "ERROR: no cache clone from the skills-bundle mirror found — the "
            "source override did not govern activation (mount-plan intent != "
            "code identity)\n"
        ),
    }
)


# ---------------------------------------------------------------------------
# _unwrap_exec_envelope unit contract
# ---------------------------------------------------------------------------


def test_unwrap_real_failed_envelope():
    rc, stdout, stderr = _unwrap_exec_envelope(0, REAL_FAILED_ENVELOPE, "")
    assert rc == 1
    assert "RESOLVED-SHA skills-prefix-mirror" in stdout
    assert "no cache clone from the skills-bundle mirror found" in stderr


def test_unwrap_success_envelope():
    env = json.dumps(
        {
            "id": "dtu-x",
            "command": "bash -lc 'true'",
            "exit_code": 0,
            "stdout": "ok\n",
            "stderr": "",
        }
    )
    rc, stdout, stderr = _unwrap_exec_envelope(0, env, "")
    assert (rc, stdout, stderr) == (0, "ok\n", "")


def test_plain_stdout_passthrough():
    """Plain (non-JSON) stdout — e.g. `--stream` mode output or a mock
    backend that doesn't wrap — passes through untouched."""
    rc, stdout, stderr = _unwrap_exec_envelope(1, "boom\n", "err\n")
    assert (rc, stdout, stderr) == (1, "boom\n", "err\n")
    rc, stdout, stderr = _unwrap_exec_envelope(0, "hello world\n", "")
    assert (rc, stdout, stderr) == (0, "hello world\n", "")


def test_json_lookalike_stdout_passthrough():
    """A command whose real output is JSON without the envelope keys passes through."""
    payload = json.dumps({"result": "ok", "count": 3})
    rc, stdout, stderr = _unwrap_exec_envelope(0, payload, "")
    assert (rc, stdout, stderr) == (0, payload, "")


def test_non_int_exit_code_passthrough():
    env = json.dumps({"command": "x", "exit_code": "1", "stdout": "", "stderr": ""})
    assert _unwrap_exec_envelope(0, env, "")[0] == 0


def test_warning_on_unrecognizable_stdout(caplog):
    """Outer success + unrecognizable stdout passes through, but LOUDLY:
    the real CLI always envelopes, so plain output at rc 0 means the
    envelope shape drifted — that must show up in logs, not vanish."""
    import logging

    with caplog.at_level(logging.WARNING, logger="amplifier_evaluation.harness.dtu"):
        rc, stdout, stderr = _unwrap_exec_envelope(0, "hello world\n", "")
    assert (rc, stdout, stderr) == (0, "hello world\n", "")
    assert any("not a recognizable JSON envelope" in r.message for r in caplog.records)

    # A proper envelope unwraps silently — no drift warning.
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="amplifier_evaluation.harness.dtu"):
        _unwrap_exec_envelope(0, REAL_FAILED_ENVELOPE, "")
    assert not caplog.records

    # Outer CLI failure passes through silently too (raw contract applies).
    caplog.clear()
    with caplog.at_level(logging.WARNING, logger="amplifier_evaluation.harness.dtu"):
        _unwrap_exec_envelope(7, "boom\n", "cli blew up")
    assert not caplog.records


def test_last_line_envelope_scan():
    """An envelope preceded by other output on the same stream (e.g. a
    wrapper banner) is still found via the last-line fallback."""
    stdout = "some banner line\nanother line\n" + REAL_FAILED_ENVELOPE + "\n"
    rc, inner_stdout, stderr = _unwrap_exec_envelope(0, stdout, "")
    assert rc == 1
    assert "RESOLVED-SHA skills-prefix-mirror" in inner_stdout
    assert "no cache clone from the skills-bundle mirror found" in stderr


def test_nested_output_envelope_unwrapped():
    """Some CLI versions nest the envelope fields under an "output" key —
    unwrapped only after the flat 4-key gate fails."""
    env = json.dumps(
        {
            "id": "dtu-x",
            "output": {
                "command": "bash -lc 'exit 3'",
                "exit_code": 3,
                "stdout": "partial\n",
                "stderr": "gate failed\n",
            },
        }
    )
    rc, stdout, stderr = _unwrap_exec_envelope(0, env, "")
    assert (rc, stdout, stderr) == (3, "partial\n", "gate failed\n")


def test_flat_envelope_wins_over_nested_output():
    """Flat-gate-first ordering: a flat envelope that also carries an
    "output" sub-object is never shadowed by it."""
    env = json.dumps(
        {
            "command": "c",
            "exit_code": 5,
            "stdout": "flat\n",
            "stderr": "",
            "output": {
                "command": "x",
                "exit_code": 9,
                "stdout": "nested\n",
                "stderr": "",
            },
        }
    )
    rc, stdout, _ = _unwrap_exec_envelope(0, env, "")
    assert (rc, stdout) == (5, "flat\n")


def test_lookalike_with_output_subobject_passthrough():
    """JSON command output whose "output" value is not an envelope still
    passes through — the nested tolerance doesn't widen the lookalike net."""
    payload = json.dumps({"output": {"result": "ok"}, "count": 3})
    rc, stdout, stderr = _unwrap_exec_envelope(0, payload, "")
    assert (rc, stdout, stderr) == (0, payload, "")


def test_outer_failure_never_unwrapped():
    """Outer CLI failure (timeout, container gone) is reported as-is."""
    rc, _, _ = _unwrap_exec_envelope(7, REAL_FAILED_ENVELOPE, "cli blew up")
    assert rc == 7


def test_outer_stderr_preserved_alongside_inner():
    rc, _, stderr = _unwrap_exec_envelope(0, REAL_FAILED_ENVELOPE, "outer warning\n")
    assert rc == 1
    assert "no cache clone" in stderr
    assert "outer warning" in stderr


# ---------------------------------------------------------------------------
# Composed-state: the real envelope through install_agent must ABORT
# ---------------------------------------------------------------------------


class EnvelopeRun:
    """Stand-in for `dtu._run`: the CLI exits 0 and prints an envelope."""

    def __init__(self, envelopes: list[str]):
        self.envelopes = list(envelopes)
        self.calls: list[list[str]] = []

    async def __call__(self, args, *, timeout=None, env=None):
        self.calls.append(list(args))
        return (
            0,
            self.envelopes[min(len(self.calls) - 1, len(self.envelopes) - 1)],
            "",
        )


def _agent(setup_cmds: list[str]) -> AgentSpec:
    return AgentSpec(
        id="test-agent",
        dir=Path("."),
        meta={},
        install={"setup_cmds": setup_cmds},
        invocation_md="",
        data_yaml_path=None,
    )


def test_install_agent_aborts_on_failed_gate(monkeypatch, tmp_path):
    """THE regression: gate fails inside the envelope -> InstallError fires
    (previously: returncode==0 from the CLI process, trial proceeded)."""
    from amplifier_evaluation.harness import dtu as dtu_module

    ok = json.dumps(
        {
            "id": "dtu-x",
            "command": "c1",
            "exit_code": 0,
            "stdout": "fine\n",
            "stderr": "",
        }
    )
    fake = EnvelopeRun([ok, REAL_FAILED_ENVELOPE])
    monkeypatch.setattr(dtu_module, "_run", fake)
    dtu = DTU(id="dtu-x", profile_path=tmp_path / "p.yaml")

    with pytest.raises(InstallError) as exc:
        asyncio.run(
            install_agent(
                _agent(["echo fine", "exit 1  # the gate"]),
                dtu,
                log_to=tmp_path / "install.log",
            )
        )
    assert "setup_cmds[2]" in str(exc.value)
    assert "no cache clone" in str(exc.value)
    # The log keeps the (unwrapped) evidence for post-hoc forensics.
    log = (tmp_path / "install.log").read_text(encoding="utf-8")
    assert "RESOLVED-SHA skills-prefix-mirror" in log


def test_push_mounts_aborts_on_failed_verification_envelope(monkeypatch, tmp_path):
    """Grader-path twin of the regression: `_push_mounts`' mount-verification
    gate checked the CLI process's exit code; with the JSON envelope (outer
    rc 0) it could never fire. Drive the real envelope through the REAL
    `_push_mounts` — monkeypatching only the subprocess seam — and assert
    the fail-loud RuntimeError now fires."""
    from amplifier_evaluation.grader import grader as grader_module
    from amplifier_evaluation.grader.schema import Mount

    src = tmp_path / "refs"
    src.mkdir()
    (src / "answer.txt").write_text("42", encoding="utf-8")

    calls: list[list[str]] = []

    async def fake_run_cli(args):
        calls.append(list(args))
        if args[1] == "file-push":
            return (0, "", "")  # push "succeeds"
        # exec (JSON mode): CLI exits 0, inner failure only in the envelope.
        return (0, REAL_FAILED_ENVELOPE, "")

    monkeypatch.setattr(grader_module, "_run_cli", fake_run_cli)

    with pytest.raises(RuntimeError, match="missing or empty"):
        asyncio.run(
            grader_module._push_mounts(
                "dtu-x",
                [Mount(source="refs", destination="/grader/data/")],
                tmp_path,
            )
        )
    assert calls[1][1] == "exec"  # the verification exec actually ran


def test_install_agent_passes_on_clean_envelopes(monkeypatch, tmp_path):
    from amplifier_evaluation.harness import dtu as dtu_module

    ok = json.dumps(
        {
            "id": "dtu-x",
            "command": "c",
            "exit_code": 0,
            "stdout": "fine\n",
            "stderr": "",
        }
    )
    monkeypatch.setattr(dtu_module, "_run", EnvelopeRun([ok]))
    dtu = DTU(id="dtu-x", profile_path=tmp_path / "p.yaml")
    asyncio.run(
        install_agent(_agent(["echo fine"]), dtu, log_to=tmp_path / "install.log")
    )  # must not raise
