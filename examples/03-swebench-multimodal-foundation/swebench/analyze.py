#!/usr/bin/env python3
"""Host-side post-run analyzer.

Runs `amplifier run "<analysis prompt>"` as a subprocess (a fresh amplifier
session, separate from the solver and grader) with cwd at the run-1/ directory.
The agent inspects the artifacts (sample, solver patch + session, grader
verdict + harness output) and produces:

  ANALYSIS.md             human-readable analysis report
  analysis_metadata.json  {resolved, classification, valid_trial, summary, key_observations}

We then capture the analysis session id, copy its session dir next to the
run, and pass the analysis files through to summarize_run.py so they show up
inside verdict-{resolved|unresolved}.md.

Handles both resolved and unresolved runs uniformly. Runs as a host-side
amplifier session (the same CLI being evaluated, but in a fresh session).

Usage:
    python3 swebench/analyze.py \\
        --run-dir <path to run-1/> \\
        --output  <path to analysis/ output dir>
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
from analysis_prompts import build_analysis_full_prompt  # noqa: E402


_SESSION_ID_RE = re.compile(r"Session ID:\s*([0-9a-fA-F-]{36})")


def _find_session_dir(session_id: str) -> Path | None:
    projects_root = Path.home() / ".amplifier" / "projects"
    if not projects_root.exists():
        return None
    matches = list(projects_root.glob(f"*/sessions/{session_id}"))
    return matches[0] if matches else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run post-run analysis as a separate amplifier session"
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="path to the run-1 directory (sample/, solver/, grader/ inside)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="output dir for analysis artifacts (will be created)",
    )
    parser.add_argument(
        "--amplifier-bin",
        type=str,
        default="amplifier",
        help="path or name of the amplifier executable",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    # Read the verdict + instance to seed the prompt.
    verdict_path = args.run_dir / "grader" / "verdict.json"
    instance_path = args.run_dir / "sample" / "instance.json"
    if not verdict_path.exists() or not instance_path.exists():
        print(
            f"[analyze] ERROR: required artifacts missing under {args.run_dir}",
            file=sys.stderr,
        )
        sys.exit(2)

    verdict = json.loads(verdict_path.read_text())
    instance = json.loads(instance_path.read_text())

    resolved = bool(verdict.get("resolved"))
    instance_id = instance.get("instance_id", "")
    repo = instance.get("repo", "")

    prompt = build_analysis_full_prompt(
        instance_id=instance_id,
        repo=repo,
        resolved=resolved,
        run_dir=str(args.run_dir.resolve()),
    )

    # Save the exact prompt for reproducibility.
    (args.output / "analysis_prompt.txt").write_text(prompt)

    print(
        f"[analyze] running amplifier run as the analyzer "
        f"(prompt {len(prompt)} chars, cwd={args.run_dir})",
        file=sys.stderr,
    )
    start = time.monotonic()

    # Run amplifier with cwd = the run-dir so the agent's relative paths
    # (sample/instance.json, solver/patch.diff, etc.) resolve naturally.
    proc = subprocess.run(
        [args.amplifier_bin, "run", prompt],
        capture_output=True,
        text=True,
        cwd=str(args.run_dir),
        env={**os.environ, "PATH": os.environ.get("PATH", "")},
    )
    wall = time.monotonic() - start

    (args.output / "stdout.txt").write_text(proc.stdout)
    (args.output / "stderr.txt").write_text(proc.stderr)

    if proc.returncode != 0:
        print(
            f"[analyze] amplifier exited with code {proc.returncode}; see stderr.txt",
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
            print(f"[analyze] captured session dir for {session_id}", file=sys.stderr)
        else:
            print(
                f"[analyze] WARNING: could not locate session dir for {session_id}",
                file=sys.stderr,
            )
    else:
        print(
            "[analyze] WARNING: no Session ID found in amplifier stdout",
            file=sys.stderr,
        )

    # The analyzer agent writes ANALYSIS.md and analysis_metadata.json into
    # its cwd (= the run-dir). Move them into output/ so they live next to
    # the rest of the analysis artifacts, but also leave a copy at run-dir
    # root for easy access. (Actually keep them only in output/ to avoid
    # cluttering run-dir; summarize_run will read from output/.)
    run_root_md = args.run_dir / "ANALYSIS.md"
    run_root_meta = args.run_dir / "analysis_metadata.json"

    if run_root_md.exists():
        shutil.move(str(run_root_md), args.output / "ANALYSIS.md")
        print(
            f"[analyze] captured ANALYSIS.md ({(args.output / 'ANALYSIS.md').stat().st_size} bytes)",
            file=sys.stderr,
        )
    else:
        print("[analyze] WARNING: agent did not produce ANALYSIS.md", file=sys.stderr)
        (args.output / "ANALYSIS.md").write_text(
            "# Analysis\n\n_The analyzer agent did not produce ANALYSIS.md.  "
            "See analysis/stdout.txt for the raw session output._\n"
        )

    metadata = {
        "resolved": resolved,
        "classification": "UNKNOWN",
        "valid_trial": True,
        "summary": "(analyzer did not produce metadata)",
        "key_observations": [],
    }
    if run_root_meta.exists():
        try:
            metadata = json.loads(run_root_meta.read_text())
        except json.JSONDecodeError as exc:
            print(
                f"[analyze] WARNING: could not parse analysis_metadata.json: {exc}",
                file=sys.stderr,
            )
        shutil.move(str(run_root_meta), args.output / "analysis_metadata.json")
    else:
        print(
            "[analyze] WARNING: agent did not produce analysis_metadata.json",
            file=sys.stderr,
        )
        (args.output / "analysis_metadata.json").write_text(
            json.dumps(metadata, indent=2)
        )

    # Side-channel run summary for the orchestrator.
    side_channel = {
        "analysis_session_id": session_id,
        "analysis_wall_seconds": round(wall, 2),
        "amplifier_exit_code": proc.returncode,
        "classification": metadata.get("classification"),
        "valid_trial": metadata.get("valid_trial"),
    }
    (args.output / "run_info.json").write_text(json.dumps(side_channel, indent=2))

    print(
        f"[analyze] done: classification={metadata.get('classification')} "
        f"wall={wall:.1f}s",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
