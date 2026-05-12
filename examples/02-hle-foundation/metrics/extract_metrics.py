#!/usr/bin/env python3
"""Extract structured metrics from a captured run of example 02.

Reads:
    <run-dir>/meta.json
    <run-dir>/sample/sample.json
    <run-dir>/solver/sessions/sessions/<sid>/events.jsonl
    <run-dir>/solver/sessions/sessions/<sid>/transcript.jsonl
    <run-dir>/solver/answer.txt
    <run-dir>/judge/verdict.json

Emits a JSON summary covering: the verdict (correct?), the solver session
shape (tokens, tool mix, delegations, wall time), the judge session shape,
and the final extracted answer.

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
        ev = json.loads(line)
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


def _final_assistant_text(transcript_path: Path) -> str:
    if not transcript_path.exists():
        return ""
    text = ""
    for line in transcript_path.read_text().splitlines():
        if not line.strip():
            continue
        msg = json.loads(line)
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
        elif isinstance(content, str):
            text = content
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def _solver_session_dir(run_dir: Path, session_id: str | None) -> Path | None:
    if not session_id:
        return None
    candidate = run_dir / "solver" / "sessions" / "sessions" / session_id
    return candidate if candidate.exists() else None


def _judge_session_dir(run_dir: Path, session_id: str | None) -> Path | None:
    if not session_id:
        return None
    candidate = run_dir / "judge" / "sessions" / "sessions" / session_id
    return candidate if candidate.exists() else None


def extract(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text())
    sample = json.loads((run_dir / "sample" / "sample.json").read_text())
    verdict_path = run_dir / "judge" / "verdict.json"
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else {}

    solver_sid = meta.get("solver", {}).get("session_id")
    judge_sid = verdict.get("judge_session_id") or meta.get("judge", {}).get(
        "session_id"
    )

    solver_dir = _solver_session_dir(run_dir, solver_sid)
    judge_dir = _judge_session_dir(run_dir, judge_sid)

    answer_file = run_dir / "solver" / "answer.txt"
    solver_answer_text = answer_file.read_text() if answer_file.exists() else ""

    # Try to pull ANSWER: <...> from the answer.txt last line (the expected format)
    final_answer_line = ""
    for line in reversed(solver_answer_text.splitlines()):
        line = line.strip()
        if line.upper().startswith("ANSWER:"):
            final_answer_line = line.split(":", 1)[1].strip()
            break

    return {
        "sample": {
            "id": sample.get("id"),
            "answer_type": sample.get("answer_type"),
            "has_image": sample.get("has_image", False),
            "ground_truth": sample.get("answer"),
        },
        "verdict": {
            "correct": verdict.get("correct"),
            "extracted_final_answer": verdict.get("extracted_final_answer"),
        },
        "solver": {
            "session_id": solver_sid,
            "wall_seconds_meta": meta.get("solver", {}).get("wall_seconds"),
            "exit_code": meta.get("solver", {}).get("exit_code"),
            "final_answer_line": final_answer_line,
            "answer_text_chars": len(solver_answer_text),
            "session": _summarize_events(solver_dir / "events.jsonl")
            if solver_dir
            else {"missing": True},
            "final_assistant_text_chars": len(
                _final_assistant_text(solver_dir / "transcript.jsonl")
            )
            if solver_dir
            else 0,
        },
        "judge": {
            "session_id": judge_sid,
            "wall_seconds": verdict.get("judge_wall_seconds")
            or meta.get("judge", {}).get("wall_seconds"),
            "session": _summarize_events(judge_dir / "events.jsonl")
            if judge_dir
            else {"missing": True},
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
