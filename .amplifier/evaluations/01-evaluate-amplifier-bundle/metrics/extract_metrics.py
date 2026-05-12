#!/usr/bin/env python3
"""Extract structured metrics from an evaluation-01 run.

Reads a run directory and emits presence-based signals about what the
agent under test (the evaluation bundle, inside the outer DTU) actually
did when handed the "validate this new bundle" prompt.

Two output modes:

    python extract_metrics.py <run-dir>           -> JSON metrics to stdout
    python extract_metrics.py <run-dir> --report  -> markdown report to stdout

A "run dir" looks like:

    results/<date>/run-1/
      meta.json
      stdout.txt
      sessions/sessions/<session_id>/events.jsonl
      sessions/sessions/<session_id>/transcript.jsonl
      produced/                # files pulled from /work/eval-output/ in the outer DTU
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
    mode_sets: list[str] = []
    reached_evaluation_mode = False
    session_completed = False
    tool_uses: list[str] = []
    delegations: list[dict] = []
    root_input = root_output = 0
    first_ts = last_ts = None

    if events_path.exists():
        for line in events_path.read_text().splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            name = ev.get("event", "")
            event_counts[name] += 1
            ts = ev.get("ts") or ev.get("data", {}).get("timestamp")
            if ts:
                try:
                    t = parse_iso(ts)
                    first_ts = first_ts or t
                    last_ts = t
                except ValueError:
                    pass
            data = ev.get("data") or {}

            if name == "tool:pre":
                tool_name = data.get("tool_name", data.get("tool", "?"))
                tool_uses.append(tool_name)
                if tool_name == "mode":
                    tool_input = data.get("tool_input") or {}
                    if isinstance(tool_input, dict):
                        if tool_input.get("operation") == "set":
                            requested = tool_input.get("name")
                            if requested:
                                mode_sets.append(requested)
                                if requested == "evaluation":
                                    reached_evaluation_mode = True

            elif name == "delegate:agent_spawned":
                delegations.append({"agent": data.get("agent")})

            elif name == "llm:response":
                usage = data.get("usage", {}) or {}
                root_input += int(usage.get("input_tokens", 0))
                root_output += int(usage.get("output_tokens", 0))

            elif name in ("orchestrator:complete", "prompt:complete"):
                session_completed = True

    wall_seconds_events = None
    if first_ts and last_ts:
        wall_seconds_events = (last_ts - first_ts).total_seconds()

    # ---- produced/ directory --------------------------------------------
    produced = run_dir / "produced"
    produced_files: list[str] = []
    if produced.exists():
        for p in produced.rglob("*"):
            if p.is_file():
                produced_files.append(str(p.relative_to(produced)))
    produced_files.sort()

    def files_matching(predicate) -> list[str]:
        return [f for f in produced_files if predicate(f)]

    produced_profiles = files_matching(lambda f: f.endswith((".yaml", ".yml")))
    produced_runner = files_matching(lambda f: f.endswith(".sh") or f.split("/")[-1] == "run.sh")
    produced_metrics_script = files_matching(
        lambda f: f.endswith(".py") and ("metric" in f.lower() or "extract" in f.lower())
    )

    # references_inner_artifact: does ANY produced file mention "crusty-reminder"?
    references_inner_artifact = False
    references_in: list[str] = []
    if produced.exists():
        for p in produced.rglob("*"):
            if not p.is_file():
                continue
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            if "crusty-reminder" in text or "crusty_reminder" in text:
                references_inner_artifact = True
                references_in.append(str(p.relative_to(produced)))

    # ---- transcript: pull the final assistant message text --------------
    transcript = session_dir / "transcript.jsonl"
    final_answer = ""
    if transcript.exists():
        for line in transcript.read_text().splitlines():
            if not line.strip():
                continue
            msg = json.loads(line)
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        final_answer = block.get("text", "")
            elif isinstance(content, str):
                final_answer = content
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    final_answer = ansi.sub("", final_answer)

    return {
        "evaluation": meta.get("evaluation"),
        "session_id": session_id,
        "wall_seconds_meta": meta.get("wall_seconds"),
        "wall_seconds_events": wall_seconds_events,
        "wall_minutes_meta": round((meta.get("wall_seconds") or 0) / 60, 2),
        "exit_code": meta.get("exit_code"),
        # Presence signals on what the agent did
        "reached_evaluation_mode": reached_evaluation_mode,
        "mode_sets": mode_sets,
        "session_completed": session_completed,
        "tool_call_count": len(tool_uses),
        "tool_mix": dict(Counter(tool_uses).most_common()),
        "delegations": delegations,
        # Presence signals on what the agent produced
        "produced_dir_present": bool(produced_files),
        "produced_file_count": len(produced_files),
        "produced_files": produced_files,
        "produced_profiles": produced_profiles,
        "produced_runner": produced_runner,
        "produced_metrics_script": produced_metrics_script,
        "references_inner_artifact": references_inner_artifact,
        "references_in": references_in,
        # Cost
        "root_tokens": {
            "input": root_input,
            "output": root_output,
            "total": root_input + root_output,
        },
        # Final answer
        "final_answer_chars": len(final_answer),
        "final_answer": final_answer,
    }


def render_report(m: dict) -> str:
    def yn(b: bool) -> str:
        return "yes" if b else "no"

    sigs = [
        ("reached_evaluation_mode", m["reached_evaluation_mode"]),
        ("session_completed", m["session_completed"]),
        ("produced_dir_present", m["produced_dir_present"]),
        ("produced_profiles", bool(m["produced_profiles"])),
        ("produced_runner", bool(m["produced_runner"])),
        ("produced_metrics_script", bool(m["produced_metrics_script"])),
        ("references_inner_artifact", m["references_inner_artifact"]),
    ]
    passed = sum(1 for _, v in sigs if v)
    total = len(sigs)

    lines = [
        f"# Report: evaluation 01 ({m['session_id'][:8]})",
        "",
        f"Signals: {passed}/{total} passed",
        "",
        "## Presence signals",
        "",
        "```",
    ]
    for name, val in sigs:
        lines.append(f"  {name:32s} {yn(val)}")
    lines += [
        "```",
        "",
        "## Run summary",
        "",
        "```",
        f"  exit_code              {m['exit_code']}",
        f"  wall_minutes           {m['wall_minutes_meta']}",
        f"  tool_call_count        {m['tool_call_count']}",
        f"  produced_file_count    {m['produced_file_count']}",
        f"  root_tokens_total      {m['root_tokens']['total']}",
        "```",
        "",
        "## Tool mix",
        "",
        "```",
    ]
    for tool, count in m["tool_mix"].items():
        lines.append(f"  {count:3d}  {tool}")
    lines += [
        "```",
        "",
        "## Produced files",
        "",
        "```",
    ]
    if m["produced_files"]:
        lines.extend(f"  {f}" for f in m["produced_files"])
    else:
        lines.append("  (none)")
    lines += [
        "```",
        "",
        "## Mode activations (chronological)",
        "",
        "```",
    ]
    if m["mode_sets"]:
        lines.extend(f"  {x}" for x in m["mode_sets"])
    else:
        lines.append("  (no /mode set calls in this session)")
    lines += [
        "```",
        "",
        "## Files referencing the inner artifact",
        "",
        "```",
    ]
    if m["references_in"]:
        lines.extend(f"  {f}" for f in m["references_in"])
    else:
        lines.append("  (none mention crusty-reminder)")
    lines += [
        "```",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: extract_metrics.py <run-dir> [--report]", file=sys.stderr)
        return 2
    run_dir = Path(args[0])
    report_mode = "--report" in args[1:]
    result = extract(run_dir)
    if report_mode:
        print(render_report(result))
    else:
        # Drop final_answer from JSON output to keep it tight; it lives
        # in transcript.jsonl already.
        slim = {k: v for k, v in result.items() if k != "final_answer"}
        print(json.dumps(slim, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
