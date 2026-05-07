#!/usr/bin/env python3
"""Extract structured metrics from a captured run.

Reads events.jsonl + transcript.jsonl from a run directory and emits a JSON
summary of root-context tokens, tool-call counts, delegation behavior, wall
time, and the final assistant answer text.

Usage:
    python extract_metrics.py <results-dir>/<side>/<run>/

Where the run directory contains:
    meta.json
    sessions/sessions/<session_id>/events.jsonl
    sessions/sessions/<session_id>/transcript.jsonl
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def extract(run_dir: Path) -> dict:
    meta = json.loads((run_dir / "meta.json").read_text())
    session_id = meta["session_id"]
    session_dir = run_dir / "sessions" / "sessions" / session_id

    # ---- events.jsonl ----------------------------------------------------
    events_path = session_dir / "events.jsonl"
    event_counts: Counter[str] = Counter()
    delegations: list[dict] = []
    root_input = root_output = root_cache_write = root_cache_read = 0
    first_event_ts = last_event_ts = None
    tool_uses: list[str] = []

    for line in events_path.read_text().splitlines():
        if not line.strip():
            continue
        ev = json.loads(line)
        name = ev.get("event", "")
        event_counts[name] += 1
        ts = ev.get("ts") or ev.get("data", {}).get("timestamp")
        if ts:
            t = parse_iso(ts)
            first_event_ts = first_event_ts or t
            last_event_ts = t

        data = ev.get("data") or {}

        if name == "delegate:agent_spawned":
            delegations.append({"agent": data.get("agent"), "sub_session": data.get("sub_session_id")})

        elif name == "tool:pre":
            # tool:pre data has the tool name in `tool_name`
            tool_uses.append(data.get("tool_name", data.get("tool", data.get("name", "?"))))

        elif name == "llm:response":
            usage = data.get("usage", {}) or {}
            # Only count root-session usage; sub-sessions are recorded in their own events.jsonl.
            # The root events.jsonl only has root llm:response events, so summing here is correct.
            root_input += int(usage.get("input_tokens", 0))
            root_output += int(usage.get("output_tokens", 0))
            root_cache_write += int(usage.get("cache_write_tokens", 0))
            root_cache_read += int(usage.get("cache_read_tokens", 0))

    wall_seconds_events = None
    if first_event_ts and last_event_ts:
        wall_seconds_events = (last_event_ts - first_event_ts).total_seconds()

    # ---- transcript.jsonl: pull the final assistant message text --------
    transcript_path = session_dir / "transcript.jsonl"
    final_answer = ""
    if transcript_path.exists():
        for line in transcript_path.read_text().splitlines():
            if not line.strip():
                continue
            msg = json.loads(line)
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                # Anthropic-style content blocks
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_answer = block.get("text", "")
            elif isinstance(content, str):
                final_answer = content

    # Strip ANSI just in case (transcript should already be clean)
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    final_answer = ansi.sub("", final_answer)

    # ---- citations: find file:line patterns in the answer ---------------
    # Match path-like tokens followed by ":<line>" — keep it conservative.
    cite_re = re.compile(r"([\w./\-_]+\.[a-zA-Z0-9]+):(\d+(?:-\d+)?)")
    citations = sorted({m.group(0) for m in cite_re.finditer(final_answer)})

    return {
        "session_id": session_id,
        "wall_seconds_meta": meta.get("wall_seconds"),
        "wall_seconds_events": wall_seconds_events,
        "root_tokens": {
            "input": root_input,
            "output": root_output,
            "cache_write": root_cache_write,
            "cache_read": root_cache_read,
            "total": root_input + root_output,
        },
        "event_counts": dict(event_counts.most_common()),
        "tool_call_count": len(tool_uses),
        "tool_mix": dict(Counter(tool_uses).most_common()),
        "delegations": delegations,
        "delegated_to_explorer": any(d.get("agent") == "foundation:explorer" for d in delegations),
        "citation_count": len(citations),
        "citations": citations,
        "final_answer": final_answer,
        "final_answer_chars": len(final_answer),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: extract_metrics.py <run-dir>", file=sys.stderr)
        sys.exit(2)
    run_dir = Path(sys.argv[1])
    result = extract(run_dir)
    # Don't include the full answer in stdout — pipeline writes it separately
    out = {k: v for k, v in result.items() if k != "final_answer"}
    print(json.dumps(out, indent=2))
