#!/usr/bin/env python3
"""Host-side judge.

Runs `amplifier run "<judge prompt>"` as a subprocess (a fresh amplifier
session, separate from the solver). Captures stdout, regex-parses the
verdict, writes verdict.json, and copies the judge session directory next
to verdict.json so the run is reproducible.

Usage:
    python3 hle/judge.py \\
        --sample <path to sample.json> \\
        --answer <path to solver answer.txt> \\
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

# Allow `from prompts import ...` when invoked from the example directory.
sys.path.insert(0, str(Path(__file__).parent))
from prompts import build_judge_prompt  # noqa: E402


_SESSION_ID_RE = re.compile(r"Session ID:\s*([0-9a-fA-F-]{36})")
_CORRECT_RE = re.compile(r"correct:\s*(yes|no)", re.IGNORECASE)
_EXTRACTED_RE = re.compile(
    r"extracted_final_answer:\s*(.+?)(?=\n\s*(?:\[correct_answer\]|reasoning:|correct:|$))",
    re.IGNORECASE | re.DOTALL,
)


def _find_session_dir(session_id: str) -> Path | None:
    """Locate the amplifier session dir for a given session id."""
    projects_root = Path.home() / ".amplifier" / "projects"
    if not projects_root.exists():
        return None
    matches = list(projects_root.glob(f"*/sessions/{session_id}"))
    return matches[0] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Judge an HLE solver answer using amplifier run"
    )
    parser.add_argument(
        "--sample", type=Path, required=True, help="path to sample.json"
    )
    parser.add_argument(
        "--answer", type=Path, required=True, help="path to solver answer.txt"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="output dir for judge artifacts"
    )
    parser.add_argument(
        "--amplifier-bin",
        type=str,
        default="amplifier",
        help="path or name of the amplifier executable",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    sample = json.loads(args.sample.read_text())
    response_text = args.answer.read_text() if args.answer.exists() else ""

    prompt = build_judge_prompt(
        question=sample["question"],
        response=response_text,
        correct_answer=sample["answer"],
    )

    # Save the exact judge prompt for reproducibility.
    (args.output / "judge_prompt.txt").write_text(prompt)

    print(
        f"[judge] running amplifier run (prompt {len(prompt)} chars)", file=sys.stderr
    )
    start = time.monotonic()
    # Pipe the prompt via stdin to avoid shell quoting issues with long multi-line prompts.
    # amplifier accepts the prompt as a positional argument; piping is via "-" or using --prompt
    # depending on version. Safest: pass as a positional. But we still want to avoid argv
    # length limits + special-char escaping, so we use Python's list-form subprocess (no shell).
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
            print(f"[judge] captured session dir for {session_id}", file=sys.stderr)
        else:
            print(
                f"[judge] WARNING: could not locate session dir for {session_id}",
                file=sys.stderr,
            )
    else:
        print(
            "[judge] WARNING: no Session ID found in amplifier stdout", file=sys.stderr
        )

    # Extract verdict from amplifier's final assistant text. amplifier prints
    # the final answer to stdout after the session log; the regex tolerates
    # surrounding ANSI codes and prose.
    judge_text = proc.stdout
    correct_match = _CORRECT_RE.search(judge_text)
    extracted_match = _EXTRACTED_RE.search(judge_text)

    correct = correct_match and correct_match.group(1).lower() == "yes"
    extracted = extracted_match.group(1).strip() if extracted_match else None

    verdict = {
        "correct": bool(correct),
        "extracted_final_answer": extracted,
        "judge_response": judge_text,
        "judge_session_id": session_id,
        "judge_wall_seconds": round(wall, 2),
        "amplifier_exit_code": proc.returncode,
        "parsed": {
            "correct_match_found": bool(correct_match),
            "extracted_match_found": bool(extracted_match),
        },
    }
    (args.output / "verdict.json").write_text(json.dumps(verdict, indent=2))

    print(
        f"[judge] verdict: correct={verdict['correct']} extracted={extracted!r}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
