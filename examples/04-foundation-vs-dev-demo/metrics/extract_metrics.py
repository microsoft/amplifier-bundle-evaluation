#!/usr/bin/env python3
"""Extract structured metrics from a captured run of example 04.

The run directory layout is:
    <run-dir>/meta.json
    <run-dir>/sample/                            (HLE: sample.json + question.md;
                                                  SWE-bench: instance.json + problem_statement.md)
    <run-dir>/solver/sessions/sessions/<sid>/    events.jsonl, transcript.jsonl
    <run-dir>/solver/answer.txt                  (HLE only)
    <run-dir>/solver/patch.diff                  (SWE-bench only)
    <run-dir>/judge/verdict.json                 (HLE only)
    <run-dir>/grader/verdict.json                (SWE-bench only)

The benchmark type is read from meta.json["benchmark"].

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
    if not patch_path.exists():
        return {"missing": True}
    text = patch_path.read_text()
    if not text.strip():
        return {"empty": True, "patch_chars": 0}
    files = re.findall(r"^diff --git a/(\S+) b/(\S+)", text, re.MULTILINE)
    added = sum(
        1 for line in text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    removed = sum(
        1 for line in text.splitlines()
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


def _final_assistant_text(transcript_path: Path) -> str:
    if not transcript_path.exists():
        return ""
    text = ""
    for line in transcript_path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
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


def _extract_hle(run_dir: Path, meta: dict) -> dict:
    sample = json.loads((run_dir / "sample" / "sample.json").read_text())
    verdict_path = run_dir / "judge" / "verdict.json"
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else {}

    solver_sid = meta.get("solver", {}).get("session_id")
    solver_dir = _solver_session_dir(run_dir, solver_sid)
    answer_file = run_dir / "solver" / "answer.txt"
    solver_answer_text = answer_file.read_text() if answer_file.exists() else ""

    final_answer_line = ""
    for line in reversed(solver_answer_text.splitlines()):
        line = line.strip()
        if line.upper().startswith("ANSWER:"):
            final_answer_line = line.split(":", 1)[1].strip()
            break

    outcome = bool(verdict.get("correct"))
    extracted = verdict.get("extracted_final_answer")
    if not solver_answer_text.strip():
        failure_mode = "no_answer_file"
    elif not final_answer_line:
        failure_mode = "no_answer_line"
    elif outcome:
        failure_mode = None
    elif extracted in (None, "", "None"):
        failure_mode = "judge_could_not_extract"
    else:
        failure_mode = "wrong_answer"

    return {
        "sample": {
            "id": sample.get("id"),
            "answer_type": sample.get("answer_type"),
            "has_image": sample.get("has_image", False),
            "ground_truth": sample.get("answer"),
            "question_chars": len(sample.get("question", "") or ""),
        },
        "verdict": {
            "outcome_key": "correct",
            "outcome": outcome,
            "extracted_final_answer": extracted,
            "reasoning": verdict.get("reasoning"),
            "failure_mode": failure_mode,
        },
        "solver": {
            "session_id": solver_sid,
            "wall_seconds": meta.get("solver", {}).get("wall_seconds"),
            "exit_code": meta.get("solver", {}).get("exit_code"),
            "final_answer_line": final_answer_line,
            "answer_text_chars": len(solver_answer_text),
            "session": _summarize_events(solver_dir / "events.jsonl")
            if solver_dir
            else {"missing": True},
        },
        "judge_or_grader": {
            "kind": "judge",
            "wall_seconds": verdict.get("judge_wall_seconds"),
        },
    }


def _extract_swebench(run_dir: Path, meta: dict) -> dict:
    instance = json.loads((run_dir / "sample" / "instance.json").read_text())
    verdict_path = run_dir / "grader" / "verdict.json"
    verdict = json.loads(verdict_path.read_text()) if verdict_path.exists() else {}

    solver_sid = meta.get("solver", {}).get("session_id")
    solver_dir = _solver_session_dir(run_dir, solver_sid)
    patch = _patch_shape(run_dir / "solver" / "patch.diff")

    status = verdict.get("status", {}) or {}
    f2p = status.get("fail_to_pass", {}) or {}
    p2p = status.get("pass_to_pass", {}) or {}

    outcome = bool(verdict.get("resolved"))
    patch_empty = bool(verdict.get("patch_was_empty"))
    patch_applied = status.get("patch_successfully_applied")
    f2p_pass = f2p.get("success_count", 0)
    f2p_fail = f2p.get("failure_count", 0)
    p2p_fail = p2p.get("failure_count", 0)

    if outcome:
        failure_mode = None
        explanation = "All fix-verification tests pass and no regressions."
    elif patch_empty:
        failure_mode = "empty_patch"
        explanation = "Agent did not edit any files (empty patch)."
    elif patch_applied is False:
        failure_mode = "patch_did_not_apply"
        explanation = "Patch generated but did not apply cleanly against the base commit."
    elif p2p_fail > 0 and f2p_pass == 0:
        failure_mode = "regressions_and_no_fix"
        explanation = f"Patch broke {p2p_fail} existing test(s) and did not pass any fix-verification tests."
    elif p2p_fail > 0:
        failure_mode = "regressions_broke"
        explanation = f"Patch broke {p2p_fail} existing test(s) (PASS_TO_PASS regressions)."
    elif f2p_fail > 0 and f2p_pass == 0:
        failure_mode = "tests_failed"
        explanation = f"Patch applied cleanly but failed all {f2p_fail} fix-verification test(s)."
    elif f2p_fail > 0:
        failure_mode = "tests_partial"
        explanation = (
            f"Patch applied and passed {f2p_pass}/{f2p_pass + f2p_fail} fix-verification "
            "tests, but did not pass all required ones."
        )
    else:
        failure_mode = "unknown"
        explanation = "Harness did not produce a definitive failure signal."
    # Prefer harness errors over inferred explanation when the harness errored out.
    harness_exit = verdict.get("harness_exit_code")
    if harness_exit not in (0, None) and not patch_empty:
        failure_mode = failure_mode or "harness_error"
        explanation = f"swebench harness exited {harness_exit}. " + explanation
    return {
        "sample": {
            "id": instance.get("instance_id"),
            "repo": instance.get("repo"),
            "base_commit": instance.get("base_commit"),
            "fail_to_pass_total": instance.get("fail_to_pass_count"),
            "pass_to_pass_total": instance.get("pass_to_pass_count"),
            "image_count": instance.get("image_count_problem_statement"),
        },
        "verdict": {
            "outcome_key": "resolved",
            "outcome": outcome,
            "patch_was_empty": patch_empty,
            "patch_successfully_applied": patch_applied,
            "fail_to_pass": f2p,
            "pass_to_pass": p2p,
            "failure_mode": failure_mode,
            "explanation": explanation,
        },
        "solver": {
            "session_id": solver_sid,
            "wall_seconds": meta.get("solver", {}).get("wall_seconds"),
            "exit_code": meta.get("solver", {}).get("exit_code"),
            "patch": patch,
            "session": _summarize_events(solver_dir / "events.jsonl")
            if solver_dir
            else {"missing": True},
        },
        "judge_or_grader": {
            "kind": "grader",
            "wall_seconds": verdict.get("harness_wall_seconds"),
        },
    }


def extract(run_dir: Path) -> dict:
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        return {"error": "meta.json missing", "run_dir": str(run_dir)}
    meta = json.loads(meta_path.read_text())
    benchmark = meta.get("benchmark") or "unknown"

    if benchmark == "hle":
        result = _extract_hle(run_dir, meta)
    elif benchmark == "swebench":
        result = _extract_swebench(run_dir, meta)
    else:
        result = {"error": f"unknown benchmark {benchmark!r}"}

    result["meta"] = {
        "benchmark": benchmark,
        "variant": meta.get("variant"),
        "task_idx": meta.get("task_idx"),
        "ran_at": meta.get("ran_at"),
        "dtu_id": meta.get("solver", {}).get("dtu_id"),
        "profile": meta.get("solver", {}).get("profile"),
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: extract_metrics.py <run-dir>", file=sys.stderr)
        sys.exit(2)
    print(json.dumps(extract(Path(sys.argv[1])), indent=2))