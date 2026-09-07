#!/usr/bin/env python3
"""FAIL-BEFORE regression test for the S3 scripted driver's continuity flag.

Subject under test
------------------
`.amplifier/evaluation/scenarios/s3/scripted_driver.py` in the evals repo
(`/home/bkrabach/dev/openai-evals-team-ci`), plus its 70 byte-identical copies
under `hw-model-performance/lanes/*/evaluation/scenarios/s3/`.

**That file is NOT in this repository.** This lane's worktree is
`amplifier-bundle-evaluation`; the driver lives in a different, remote-less
repo that this lane does not own (0rg hazard). So the test is shipped as a lane
artifact and pointed at the driver by path:

    S3_SCRIPTED_DRIVER=/path/to/scenarios/s3/scripted_driver.py \
        python3 -m pytest docs/lanes/i0cm-harness-defect-audit/test_scripted_driver_continuity.py -q

It defaults to the evals-repo path and SKIPS (never fails) when the driver is
absent, so it is inert in this repo's CI, which has no evals checkout.

What it pins
------------
1. `capture_sid` must recognise BOTH phrasings the CLI actually prints:
   turn 1 -> ``Session ID: <sid>``; ``amplifier run --resume`` -> ``Resuming
   session: <sid>``. Matching only the first is the defect: it made
   `session_continuity_ok` False for **151/151** driver records in the corpus.
2. A turn whose stdout capture came back EMPTY (`out_len == 0`, observed on
   6 runs / 10 turns, all openai) must not be read as a continuity break -- the
   container executed the turn; only the host-side capture was lost. It must
   still be surfaced explicitly, never silently absorbed.
3. A run whose turns genuinely ran in DIFFERENT sessions must still come back
   False. This is the guard against "fixing" the flag by making it always True.
   The fixture for it is real: `20260901-threeknob/runs/val-tk-sol-xhigh-s3-02`
   resumed `8839b22c...` on turn 5 after four turns in `1f19b7ad...`.

The header lines below are quoted VERBATIM from
`20260906-8rugb/runs/A-anth-01/turn{1,2}.out`.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

DEFAULT_DRIVER = Path(
    "/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/scenarios/s3/scripted_driver.py"
)
DRIVER_PATH = Path(os.environ.get("S3_SCRIPTED_DRIVER", str(DEFAULT_DRIVER)))

# Real session ids from 20260906-8rugb/runs/A-anth-01 and
# 20260901-threeknob/runs/val-tk-sol-xhigh-s3-02.
SID = "ca74aafb-50f7-4d17-b1ef-b01f0c012a34"
OTHER_SID = "8839b22c-e8bf-4ae0-91b7-fe92a8d109d5"

# turn1.out line 3, verbatim.
TURN1_OUT = (
    "Bundle 'foundation' prepared successfully\n"
    "\n"
    f"Session ID: {SID}\n"
    "Bundle: foundation | Provider: Anthropic | claude-opus-5\n"
    "...agent output...\n"
)

# turn2.out line 1, verbatim (leading U+2713 CHECK MARK, as the CLI prints it).
RESUME_OUT = f"\u2713 Resuming session: {SID}\n  Messages: 12\n  Using saved bundle: foundation\n...agent output...\n"

RESUME_OUT_OTHER = (
    f"\u2713 Resuming session: {OTHER_SID}\n  Messages: 87\n  Using saved bundle: anchors-amp-dev\n...agent output...\n"
)


def load_driver():
    if not DRIVER_PATH.exists():
        pytest.skip(f"S3 scripted driver not present at {DRIVER_PATH}")
    spec = importlib.util.spec_from_file_location("s3_scripted_driver_under_test", DRIVER_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def drive(mod, monkeypatch, tmp_path: Path, turn_outputs: list[str]) -> dict:
    """Run the driver's own main() against replayed turn stdout, return the record."""
    scen = tmp_path / "scen"
    scen.mkdir()
    (scen / "turns.json").write_text(
        json.dumps(
            {
                "turns": [
                    {"n": i + 1, "label": f"t{i + 1}", "message": f"message {i + 1}"}
                    for i in range(len(turn_outputs))
                ]
            }
        )
    )
    outdir = tmp_path / "out"
    seq = list(turn_outputs)
    calls: list[int] = []

    monkeypatch.setattr(mod, "exec_bash", lambda *a, **k: None)
    monkeypatch.setattr(mod, "launch_turn", lambda *a, **k: None)

    def fake_poll(_dtu, _poll_interval, _turn_timeout):
        out = seq[len(calls)]
        calls.append(1)
        return True, "DONE EXIT:0", out

    monkeypatch.setattr(mod, "poll_turn", fake_poll)
    monkeypatch.setattr(mod.time, "sleep", lambda *_a, **_k: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["scripted_driver.py", "--dtu", "fake-dtu", "--scenario-dir", str(scen), "--outdir", str(outdir)],
    )
    assert mod.main() == 0
    return json.loads((outdir / "driver_record.json").read_text())


# ---------------------------------------------------------------- capture_sid


def test_capture_sid_reads_turn_one_session_id():
    """Baseline: the phrasing the driver already handles. Passes before and after."""
    mod = load_driver()
    assert mod.capture_sid(TURN1_OUT) == SID


def test_capture_sid_reads_resume_phrasing():
    """FAILS on the current driver: it only matches 'Session ID:'.

    `amplifier run --resume` prints 'Resuming session: <sid>' instead, so every
    turn after the first returns None and continuity can never hold.
    """
    mod = load_driver()
    assert mod.capture_sid(RESUME_OUT) == SID


# --------------------------------------------------------- continuity outcome


def test_continuity_true_for_a_real_five_turn_resume_run(monkeypatch, tmp_path):
    """FAILS on the current driver (False for 151/151 recorded runs)."""
    mod = load_driver()
    rec = drive(mod, monkeypatch, tmp_path, [TURN1_OUT] + [RESUME_OUT] * 4)
    assert rec["root_session_id"] == SID
    assert rec["session_continuity_ok"] is True


def test_continuity_survives_an_empty_turn_capture(monkeypatch, tmp_path):
    """An empty host-side capture is a transport artifact, not a broken session.

    Observed on A-oai-01/02, A-oai-03, B-oai-01/02 (turns 4-5) and
    val-tk-sol-high-s3-03 (turn 4) -- 6 runs, 10 turns, every one openai, while
    the container executed the turn. It must not read as a break, and it must
    still be reported.
    """
    mod = load_driver()
    rec = drive(mod, monkeypatch, tmp_path, [TURN1_OUT, RESUME_OUT, RESUME_OUT, "", ""])
    assert rec["session_continuity_ok"] is True
    assert rec["turn_captures_empty"] == 2


def test_continuity_false_when_a_turn_ran_in_a_different_session(monkeypatch, tmp_path):
    """The guard against 'fix it by returning True'.

    Real fixture: 20260901-threeknob/runs/val-tk-sol-xhigh-s3-02 ran turns 1-4
    in 1f19b7ad... (4 prompt:complete on disk) and turn 5 in 8839b22c..., a
    session absent from the capture entirely -- and still scored 90/100, pass.
    """
    mod = load_driver()
    rec = drive(mod, monkeypatch, tmp_path, [TURN1_OUT, RESUME_OUT, RESUME_OUT, RESUME_OUT, RESUME_OUT_OTHER])
    assert rec["session_continuity_ok"] is False


def test_continuity_false_when_a_turn_never_ran(monkeypatch, tmp_path):
    """A turn that produced neither phrasing and was not empty is unexplained.

    Real fixture: the two 20260901-rebaseline sol-xhigh runs, whose last turn
    hit TIMEOUT with a 57-byte stub.
    """
    mod = load_driver()
    rec = drive(mod, monkeypatch, tmp_path, [TURN1_OUT, RESUME_OUT, "TIMEOUT stub, no session line\n"])
    assert rec["session_continuity_ok"] is False
