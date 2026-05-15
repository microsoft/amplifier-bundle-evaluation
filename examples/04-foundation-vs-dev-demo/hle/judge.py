#!/usr/bin/env python3
"""Host-side judge for a single HLE task (same shape as example 02).

Runs `amplifier run "<judge prompt>"` as a fresh amplifier session on the
host (separate from the solver). Captures stdout, regex-parses the verdict,
writes verdict.json, and copies the judge session directory next to it.

Usage:
    python3 hle/judge.py \
        --sample <path to sample.json> \
        --answer <path to solver answer.txt> \
        --output <path to judge output dir>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from prompts import build_judge_prompt  # noqa: E402


_SESSION_ID_RE = re.compile(r"Session ID:\s*([0-9a-fA-F-]{36})")
_CORRECT_RE = re.compile(r"correct:\s*(yes|no)", re.IGNORECASE)
_EXTRACTED_RE = re.compile(
    r"extracted_final_answer:\s*(.+?)(?=\n\s*(?:\[correct_answer\]|reasoning:|correct:|$))",
    re.IGNORECASE | re.DOTALL,
)
# Capture the judge's reasoning paragraph that explains WHY the answer is right or wrong.
_REASONING_RE = re.compile(
    r"reasoning:\s*(.+?)(?=\n\s*correct:|$)",
    re.IGNORECASE | re.DOTALL,
)
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    # Strip ANSI codes and collapse runs of whitespace (the amplifier CLI
    # right-pads each rendered line, which makes the reasoning paragraph
    # show up as a wall of trailing spaces in the saved stdout).
    cleaned = _ANSI_RE.sub("", text)
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def _find_session_dir(session_id: str) -> Path | None:
    projects_root = Path.home() / ".amplifier" / "projects"
    if not projects_root.exists():
        return None
    matches = list(projects_root.glob(f"*/sessions/{session_id}"))
    return matches[0] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Judge an HLE solver answer using amplifier run"
    )
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--answer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--amplifier-bin", type=str, default="amplifier")
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    sample = json.loads(args.sample.read_text())
    response_text = args.answer.read_text() if args.answer.exists() else ""

    prompt = build_judge_prompt(
        question=sample["question"],
        response=response_text,
        correct_answer=sample["answer"],
    )
    (args.output / "judge_prompt.txt").write_text(prompt)

    print(
        f"[judge] running amplifier run (prompt {len(prompt)} chars)",
        file=sys.stderr,
    )
    start = time.monotonic()
    proc = subprocess.run(
        [args.amplifier_bin, "run", prompt],
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )
    wall = time.monotonic() - start

    (args.output / "stdout.txt").write_text(proc.stdout)
    (args.output / "stderr.txt").write_text(proc.stderr)

    if proc.returncode != 0:
        print(
            f"[judge] amplifier run exited with code {proc.returncode}; see stderr.txt",
            file=sys.stderr,
        )

    sid_match = _SESSION_ID_RE.search(proc.stdout)
    session_id = sid_match.group(1) if sid_match else None
    if session_id:
        session_dir = _find_session_dir(session_id)
        if session_dir:
            dest = args.output / "sessions" / "sessions" / session_id
            dest.mkdir(parents=True, exist_ok=True)
            for fname in ("events.jsonl", "transcript.jsonl", "metadata.json"):
                src = session_dir / fname
                if src.exists():
                    shutil.copy(src, dest / fname)

    judge_text = proc.stdout
    correct_match = _CORRECT_RE.search(judge_text)
    extracted_match = _EXTRACTED_RE.search(judge_text)
    reasoning_match = _REASONING_RE.search(judge_text)
    correct = correct_match and correct_match.group(1).lower() == "yes"
    extracted = _clean(extracted_match.group(1)) if extracted_match else None
    reasoning = _clean(reasoning_match.group(1)) if reasoning_match else None

    verdict = {
        "correct": bool(correct),
        "extracted_final_answer": extracted,
        "reasoning": reasoning,
        "judge_response": judge_text,
        "judge_session_id": session_id,
        "judge_wall_seconds": round(wall, 2),
        "amplifier_exit_code": proc.returncode,
        "parsed": {
            "correct_match_found": bool(correct_match),
            "extracted_match_found": bool(extracted_match),
            "reasoning_match_found": bool(reasoning_match),
        },
    }
    (args.output / "verdict.json").write_text(json.dumps(verdict, indent=2))

    print(
        f"[judge] verdict: correct={verdict['correct']} extracted={extracted!r}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()