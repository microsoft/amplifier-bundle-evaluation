#!/usr/bin/env python3
"""Extract structured metrics from a captured run of example 03.

Reads:
    <run-dir>/meta.json
    <run-dir>/sample/instance.json
    <run-dir>/solver/sessions/sessions/<sid>/events.jsonl
    <run-dir>/solver/sessions/sessions/<sid>/transcript.jsonl
    <run-dir>/solver/patch.diff
    <run-dir>/grader/verdict.json

Emits a JSON summary covering: the verdict (resolved?), the solver session
shape (tokens, tool mix, delegations, wall time), the grader stats, and the
extracted patch shape.

Usage:
    python3 metrics/extract_metrics.py <run-dir>
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _summarize_events(events_path: Path) -> dict:
    if not events_path.exists():
        return {"missing": True}

    event_counts: Counter[str] = Counter()
    delegations: list[dict] = []
    tool_uses: list[str] = []
    root_input = root_output = root_cache_write = root_cache_read = 0
    first_ts = last_ts = None

    for line in events_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        name = ev.get("event", "")
        event_counts[name] += 1
        ts = ev.get("ts") or ev.get("data", {}).get("timestamp")
        if ts:
            t = _parse_iso(ts)
            first_ts = first_ts or t
            last_ts = t

        data = ev.get("data") or {}
        if name == "delegate:agent_spawned":
            delegations.append(
                {"agent": data.get("agent"), "sub_session": data.get("sub_session_id")}
            )
        elif name == "tool:pre":
            tool_uses.append(
                data.get("tool_name", data.get("tool", data.get("name", "?")))
            )
        elif name == "llm:response":
            usage = data.get("usage", {}) or {}
            root_input += int(usage.get("input_tokens", 0))
            root_output += int(usage.get("output_tokens", 0))
            root_cache_write += int(usage.get("cache_write_tokens", 0))
            root_cache_read += int(usage.get("cache_read_tokens", 0))

    wall = (last_ts - first_ts).total_seconds() if first_ts and last_ts else None

    return {
        "event_counts": dict(event_counts.most_common()),
        "tool_call_count": len(tool_uses),
        "tool_mix": dict(Counter(tool_uses).most_common()),
        "delegations": delegations,
        "root_tokens": {
            "input": root_input,
            "output": root_output,
            "cache_write": root_cache_write,
            "cache_read": root_cache_read,
            "total": root_input + root_output,
        },
        "wall_seconds_events": wall,
    }


def _patch_shape(patch_path: Path) -> dict:
    """Summarize a unified-diff patch: file count, line additions, etc."""
    if not patch_path.exists():
        return {"missing": True}
    text = patch_path.read_text()
    if not text.strip():
        return {"empty": True}

    files = re.findall(r"^diff --git a/(\S+) b/(\S+)", text, re.MULTILINE)
    added = sum(
        1
        for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1
        for line in text.splitlines()
        if line.startswith("-") and not line.startswith("---")
    )
    return {
        "files_changed": len(files),
        "files": [b for _, b in files],
        "lines_added": added,
        "lines_removed": removed,
        "patch_chars": len(text),
    }


def _solver_session_dir(run_dir: Path, session_id: str | None) -> Path | None:
    if not session_id:
        return None
    candidate = run_dir / "solver" / "sessions" / "sessions" / session_id
    return candidate if candidate.exists() else None


def extract(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text())
    instance = json.loads((run_dir / "sample" / "instance.json").read_text())
    verdict_path = run_dir / "grader" / "verdict.json"
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else {}

    solver_sid = meta.get("solver", {}).get("session_id")
    solver_dir = _solver_session_dir(run_dir, solver_sid)

    patch_path = run_dir / "solver" / "patch.diff"
    patch = _patch_shape(patch_path)

    status = verdict.get("status", {}) or {}

    return {
        "instance": {
            "id": instance.get("instance_id"),
            "repo": instance.get("repo"),
            "base_commit": instance.get("base_commit"),
            "version": instance.get("version"),
            "fail_to_pass_total": instance.get("fail_to_pass_count"),
            "pass_to_pass_total": instance.get("pass_to_pass_count"),
            "image_count": instance.get("image_count_problem_statement"),
        },
        "verdict": {
            "resolved": verdict.get("resolved"),
            "patch_was_empty": verdict.get("patch_was_empty"),
            "patch_successfully_applied": status.get("patch_successfully_applied"),
            "fail_to_pass": status.get("fail_to_pass", {}),
            "pass_to_pass": status.get("pass_to_pass", {}),
        },
        "solver": {
            "session_id": solver_sid,
            "wall_seconds_meta": meta.get("solver", {}).get("wall_seconds"),
            "exit_code": meta.get("solver", {}).get("exit_code"),
            "patch": patch,
            "session": _summarize_events(solver_dir / "events.jsonl")
            if solver_dir
            else {"missing": True},
        },
        "grader": {
            "harness_run_id": verdict.get("harness_run_id"),
            "wall_seconds": verdict.get("harness_wall_seconds"),
            "exit_code": verdict.get("harness_exit_code"),
        },
        "meta": {
            "foundation_branch": meta.get("solver", {}).get("foundation_branch"),
            "foundation_sha": meta.get("solver", {}).get("foundation_sha"),
            "ran_at": meta.get("ran_at"),
        },
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: extract_metrics.py <run-dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(extract(Path(sys.argv[1])), indent=2))
