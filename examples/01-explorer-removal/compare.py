#!/usr/bin/env python3
"""Compare root-context metrics across the two explorer-removal trials.

This is the metric half of the eval. The harness uses the Extractor agent to
pull each trial's session artifacts out of its DTU; this script reads those
artifacts from disk and computes the A/B comparison that surfaces the
context-sink effect.

For each trial it locates the agent-under-test's ROOT session (the explorer
runs in a sub-session, which we deliberately exclude), then ports the metrics
from the original example's extract_metrics.py: root-context token usage,
event/tool mix, delegations, and file:line citations from the final answer.

Usage:
    python compare.py --with-dir  <trial_dir> \\
                      --without-dir <trial_dir> \\
                      --output <dir>

Each <trial_dir> is a trial output directory containing an `extraction/`
subtree (as produced by the harness / Extractor). The script scans that subtree
for `events.jsonl` files rather than assuming a fixed path, because the
Extractor chooses the on-disk layout.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
CITE = re.compile(r"([\w./\-]+\.[A-Za-z0-9]+):(\d+(?:-\d+)?)")


def _iso(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _iter_events(path: Path):
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def _find_sessions(trial_dir: Path) -> dict[str, dict]:
    """Map session_id -> {events, transcript, metadata} for every session whose
    events.jsonl appears anywhere under the trial's extraction subtree."""
    root = trial_dir / "extraction"
    if not root.is_dir():
        root = trial_dir
    sessions: dict[str, dict] = {}
    for events_path in root.rglob("events.jsonl"):
        sdir = events_path.parent
        sessions[sdir.name] = {
            "dir": sdir,
            "events": events_path,
            "transcript": sdir / "transcript.jsonl",
            "metadata": sdir / "metadata.json",
        }
    return sessions


def _pick_root(sessions: dict[str, dict]) -> str | None:
    """The ROOT session is the one that received the user's prompt and is not
    spawned as anyone's sub-session.

    The strongest signal is a `prompt:submit` event -- the user's message is
    submitted to the root only, never to a delegated sub-session. We also
    collect every sub_session_id (from delegate:agent_spawned) and every
    metadata parent_id to exclude sub-sessions, then rank the survivors by:
    has prompt:submit, has a transcript, spawned delegates, most recent.
    """
    if not sessions:
        return None
    if len(sessions) == 1:
        return next(iter(sessions))

    sub_ids: set[str] = set()
    spawns: dict[str, int] = {}
    has_prompt: dict[str, bool] = {}
    for sid, s in sessions.items():
        n = 0
        prompt = False
        for ev in _iter_events(s["events"]):
            name = ev.get("event")
            if name == "prompt:submit":
                prompt = True
            elif name == "delegate:agent_spawned":
                child = (ev.get("data") or {}).get("sub_session_id")
                if child:
                    sub_ids.add(child)
                n += 1
        spawns[sid] = n
        has_prompt[sid] = prompt
        meta_path = s["metadata"]
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                pid = meta.get("parent_id") or meta.get("parent_session_id")
                if pid:
                    sub_ids.add(sid)
            except json.JSONDecodeError:
                pass

    candidates = [sid for sid in sessions if sid not in sub_ids] or list(sessions)
    candidates.sort(
        key=lambda sid: (
            has_prompt.get(sid, False),
            sessions[sid]["transcript"].exists(),
            spawns.get(sid, 0),
            sessions[sid]["dir"].stat().st_mtime,
        ),
        reverse=True,
    )
    return candidates[0]


def _answer_from_transcript(transcript: Path) -> str:
    if not transcript.exists():
        return ""
    answer = ""
    for msg in _iter_events(transcript):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = [
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            ]
            answer = "".join(parts)
        elif isinstance(content, str):
            answer = content
    return answer


def _answer_from_events(events: Path) -> str:
    """Reconstruct the final assistant answer from events.jsonl.

    Each assistant generation is delimited by an `llm:request`; the final answer
    is the text emitted after the LAST one. We keep only `content_block:end`
    blocks of type `text` (excluding `thinking` and `tool_call`).
    """
    turn: list[str] = []
    for ev in _iter_events(events):
        name = ev.get("event")
        if name == "llm:request":
            turn = []
        elif name == "content_block:end":
            block = (ev.get("data") or {}).get("block") or {}
            if block.get("type") == "text" and block.get("text"):
                turn.append(block["text"])
    return "".join(turn)


def _final_answer(session: dict) -> str:
    """Prefer the clean transcript answer; fall back to events.jsonl (which is
    always extracted) so citation counting works even when the Extractor did not
    pull transcript.jsonl."""
    answer = _answer_from_transcript(session["transcript"])
    if not answer:
        answer = _answer_from_events(session["events"])
    return ANSI.sub("", answer)


def _session_token_sums(events: Path) -> dict:
    """Sum llm:response token usage for a single session's events.jsonl."""
    ti = to = cw = cr = n = 0
    for ev in _iter_events(events):
        if ev.get("event") == "llm:response":
            u = (ev.get("data") or {}).get("usage", {}) or {}
            ti += int(u.get("input_tokens", 0) or 0)
            to += int(u.get("output_tokens", 0) or 0)
            cw += int(u.get("cache_write_tokens", 0) or 0)
            cr += int(u.get("cache_read_tokens", 0) or 0)
            n += 1
    return {
        "input": ti,
        "output": to,
        "cache_write": cw,
        "cache_read": cr,
        "responses": n,
    }


def collect_metrics(trial_dir: Path) -> dict:
    trial_dir = Path(trial_dir)
    sessions = _find_sessions(trial_dir)
    root_id = _pick_root(sessions)
    if root_id is None:
        return {"error": f"no session events.jsonl found under {trial_dir}"}

    root = sessions[root_id]
    counts: Counter[str] = Counter()
    tools: list[str] = []
    delegations: list[dict] = []
    ti = to = tcw = tcr = 0
    first = last = None

    for ev in _iter_events(root["events"]):
        name = ev.get("event", "")
        counts[name] += 1
        ts = ev.get("ts") or (ev.get("data") or {}).get("timestamp")
        if ts:
            t = _iso(ts)
            if t:
                first = first or t
                last = t
        data = ev.get("data") or {}
        if name == "delegate:agent_spawned":
            delegations.append(
                {"agent": data.get("agent"), "sub_session": data.get("sub_session_id")}
            )
        elif name == "tool:pre":
            tools.append(data.get("tool_name", data.get("tool", data.get("name", "?"))))
        elif name == "llm:response":
            u = data.get("usage", {}) or {}
            ti += int(u.get("input_tokens", 0) or 0)
            to += int(u.get("output_tokens", 0) or 0)
            tcw += int(u.get("cache_write_tokens", 0) or 0)
            tcr += int(u.get("cache_read_tokens", 0) or 0)

    answer = _final_answer(root)
    citations = sorted({m.group(0) for m in CITE.finditer(answer)})
    wall = (last - first).total_seconds() if first and last else None

    # Total across EVERY session (root + any delegated sub-sessions). The root
    # numbers above show the context-sink benefit (lean root); these show the
    # true compute cost -- the explorer does not make the work free, it moves
    # it into a sub-session that still spends tokens.
    breakdown: list[dict] = []
    all_t = {"input": 0, "output": 0, "cache_write": 0, "cache_read": 0}
    for sid, s in sessions.items():
        st = _session_token_sums(s["events"])
        breakdown.append(
            {
                "session_id": sid,
                "role": "root" if sid == root_id else "sub",
                "input": st["input"],
                "output": st["output"],
                "cache_read": st["cache_read"],
                "cache_write": st["cache_write"],
                "responses": st["responses"],
            }
        )
        for k in ("input", "output", "cache_write", "cache_read"):
            all_t[k] += st[k]
    breakdown.sort(key=lambda b: (b["role"] != "root", -(b["input"] + b["output"])))
    all_t["total"] = all_t["input"] + all_t["output"]
    all_t["processed"] = (
        all_t["input"] + all_t["output"] + all_t["cache_read"] + all_t["cache_write"]
    )

    return {
        "root_session_id": root_id,
        "session_count": len(sessions),
        "wall_seconds_events": wall,
        "root_tokens": {
            "input": ti,
            "output": to,
            "cache_write": tcw,
            "cache_read": tcr,
            "total": ti + to,
        },
        "all_tokens": all_t,
        "sessions": breakdown,
        "event_counts": dict(counts.most_common()),
        "tool_call_count": len(tools),
        "tool_mix": dict(Counter(tools).most_common()),
        "delegation_count": len(delegations),
        "delegations": delegations,
        "citation_count": len(citations),
        "citations": citations,
        "final_answer_chars": len(answer),
    }


def _ratio(after: float, before: float) -> float | None:
    if not before:
        return None
    return round(after / before, 2)


def compare(with_dir: Path, without_dir: Path) -> dict:
    """`with` = explorer present (the baseline); `without` = explorer removed."""
    w = collect_metrics(with_dir)
    wo = collect_metrics(without_dir)
    diff = {}
    if "error" not in w and "error" not in wo:
        wt, wot = w["root_tokens"], wo["root_tokens"]
        wa, woa = w["all_tokens"], wo["all_tokens"]
        diff = {
            "root_input_tokens": {
                "with": wt["input"],
                "without": wot["input"],
                "ratio_without_over_with": _ratio(wot["input"], wt["input"]),
            },
            "root_total_tokens": {
                "with": wt["total"],
                "without": wot["total"],
                "ratio_without_over_with": _ratio(wot["total"], wt["total"]),
            },
            "total_input_tokens": {
                "with": wa["input"],
                "without": woa["input"],
                "ratio_without_over_with": _ratio(woa["input"], wa["input"]),
            },
            "total_tokens": {
                "with": wa["total"],
                "without": woa["total"],
                "ratio_without_over_with": _ratio(woa["total"], wa["total"]),
            },
            "total_processed_tokens": {
                "with": wa["processed"],
                "without": woa["processed"],
                "ratio_without_over_with": _ratio(woa["processed"], wa["processed"]),
            },
            "root_tool_calls": {
                "with": w["tool_call_count"],
                "without": wo["tool_call_count"],
                "ratio_without_over_with": _ratio(
                    wo["tool_call_count"], w["tool_call_count"]
                ),
            },
            "delegations": {
                "with": w["delegation_count"],
                "without": wo["delegation_count"],
            },
            "citations": {"with": w["citation_count"], "without": wo["citation_count"]},
            "wall_seconds_events": {
                "with": w["wall_seconds_events"],
                "without": wo["wall_seconds_events"],
            },
        }
    return {"with_explorer": w, "without_explorer": wo, "diff": diff}


def render_markdown(result: dict) -> str:
    d = result.get("diff") or {}
    lines = ["# Explorer-removal metric comparison", ""]
    if not d:
        lines += [
            "Comparison unavailable -- one or both trials produced no extractable session.",
            "",
            "```json",
            json.dumps(result, indent=2),
            "```",
            "",
        ]
        return "\n".join(lines)

    def row(label: str, key: str, field: str = "ratio_without_over_with") -> str:
        e = d[key]
        extra = f"  (without/with = {e[field]}x)" if e.get(field) is not None else ""
        return f"- {label}: with={e['with']}  without={e['without']}{extra}"

    lines += [
        "Independent variable: foundation WITH vs WITHOUT the foundation:explorer agent.",
        "Same prompt, same target repo. `with` is the baseline.",
        "",
        "ROOT context (what the root session pays -- the context-sink benefit):",
        row("  Root-context input tokens", "root_input_tokens"),
        row("  Root-context total tokens", "root_total_tokens"),
        row("  Root tool calls", "root_tool_calls"),
        "",
        "TOTAL across root + sub-sessions (the true compute cost -- the explorer",
        "moves work into a sub-session, it does not make it free):",
        row("  Total input tokens (all sessions)", "total_input_tokens"),
        row("  Total tokens in+out (all sessions)", "total_tokens"),
        row("  Total processed incl cache (all sessions)", "total_processed_tokens"),
        "",
        f"- Root delegations: with={d['delegations']['with']}  without={d['delegations']['without']}",
        f"- file:line citations: with={d['citations']['with']}  without={d['citations']['without']}",
        f"- Wall seconds (events): with={d['wall_seconds_events']['with']}  without={d['wall_seconds_events']['without']}",
        "",
        "Interpretation: the explorer keeps the ROOT context lean (big ratio) while",
        "the TOTAL compute gap is much smaller -- the win is root-context preservation",
        "(longer viable sessions), not raw token savings. Answer quality (see grader)",
        "should hold for the claim to stand.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--with-dir", required=True, type=Path, help="trial dir, explorer present"
    )
    ap.add_argument(
        "--without-dir", required=True, type=Path, help="trial dir, explorer removed"
    )
    ap.add_argument(
        "--output",
        required=True,
        type=Path,
        help="dir for comparison.json + comparison.md",
    )
    args = ap.parse_args()

    result = compare(args.with_dir, args.without_dir)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "comparison.json").write_text(json.dumps(result, indent=2))
    md = render_markdown(result)
    (args.output / "comparison.md").write_text(md)
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
