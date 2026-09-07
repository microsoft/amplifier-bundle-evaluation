#!/usr/bin/env python3
"""ytja routing-awareness grader.

Grades EXECUTED tool results only.

Primary source  : events.jsonl  `tool:post`      (the executed-RESULT entry)
Cross-check     : transcript.jsonl `role":"tool"` (the normalized RESULT entry)
NEVER counted   : content_block thinking text. webu's first recompute was fooled
                  by exactly that -- write_file "appeared" in 9/10 runs as
                  thinking-text mentions while the executed entries were absent.

Cost: summed from every `llm:response` `data.usage.cost_usd` across the run's whole
session tree (root + delegated sub-sessions), matching probes/dw_measure.py.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

REACH_TOOLS = {"delegate", "load_skill", "mode"}


def load_events(p: Path) -> list[dict]:
    out = []
    if not p.exists():
        return out
    with p.open() as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def session_dir(root: Path, sid: str) -> Path | None:
    for c in root.rglob(sid):
        if c.is_dir():
            return c
    return None


def reach_target(ev: dict) -> str | None:
    d = ev.get("data", {})
    name = d.get("tool_name")
    ti = d.get("tool_input") or {}
    if name == "delegate":
        return ti.get("agent") or "delegate:<unknown>"
    if name == "load_skill":
        for k in ("skill_name", "info", "search"):
            if ti.get(k):
                return f"load_skill:{ti[k]}"
        if ti.get("list"):
            return "load_skill:<list>"
        return "load_skill:<unknown>"
    if name == "mode":
        return f"mode:{ti.get('name') or ti.get('operation')}"
    return None


def tree_sessions(captures: Path, root_sid: str) -> list[Path]:
    """root session dir + every session whose events name it as an ancestor."""
    dirs: dict[str, Path] = {}
    for ej in captures.rglob("events.jsonl"):
        if "/context-intelligence/" in str(ej):
            continue
        dirs[ej.parent.name] = ej.parent
    if root_sid not in dirs:
        return []
    parent: dict[str, str | None] = {}
    for sid, dpath in dirs.items():
        par = None
        for e in load_events(dpath / "events.jsonl"):
            if e.get("event") == "session:start":
                par = (e.get("data") or {}).get("parent_session_id") or (
                    e.get("data") or {}
                ).get("parent_id")
                break
        parent[sid] = par
    keep = []
    for sid, dpath in dirs.items():
        cur, hops = sid, 0
        while cur and hops < 12:
            if cur == root_sid:
                keep.append(dpath)
                break
            cur = parent.get(cur)
            hops += 1
    return keep


def grade_run(rec: dict, captures: Path, spec_by_id: dict, N: int) -> dict:
    sids = rec.get("new_sessions") or []
    root = None
    for sid in sids:
        d = session_dir(captures, sid)
        if not d:
            continue
        evs = load_events(d / "events.jsonl")
        par = None
        for e in evs:
            if e.get("event") == "session:start":
                par = (e.get("data") or {}).get("parent_session_id") or (
                    e.get("data") or {}
                ).get("parent_id")
                break
        if par is None:
            root = (sid, d, evs)
            break
    if root is None:
        return {
            **{
                k: rec[k]
                for k in ("run_id", "arm", "provider", "prompt_id", "kind", "rep")
            },
            "valid": False,
            "reason": "no root session captured",
            "cost_usd": 0.0,
        }

    sid, sdir, evs = root
    posts = [e for e in evs if e.get("event") == "tool:post"]
    seq = [(e["data"].get("tool_name"), reach_target(e)) for e in posts]
    first_n = seq[:N]

    # ---- cross-check against transcript.jsonl role:"tool" ----
    tpath = sdir / "transcript.jsonl"
    trole = 0
    if tpath.exists():
        for line in tpath.read_text().splitlines():
            try:
                o = json.loads(line)
            except Exception:
                continue
            if isinstance(o, dict) and o.get("role") == "tool":
                trole += 1
    # ---- thinking-text control: count mentions we must NOT grade on ----
    thinking_mentions = 0
    for e in evs:
        if e.get("event") in ("content_block:start", "content_block:end"):
            d = e.get("data") or {}
            if d.get("block_type") == "thinking":
                txt = json.dumps(d)
                thinking_mentions += sum(txt.count(t) for t in REACH_TOOLS)

    # ---- cost over the whole tree ----
    cost = 0.0
    reqs = 0
    for d in tree_sessions(captures, sid) or [sdir]:
        for e in load_events(d / "events.jsonl"):
            if e.get("event") == "llm:response":
                u = (e.get("data") or {}).get("usage") or {}
                cost += float(u.get("cost_usd") or 0.0)
                reqs += 1

    completed = any(e.get("event") == "prompt:complete" for e in evs)
    valid = completed and (
        len(posts) > 0 or any(e.get("event") == "llm:response" for e in evs)
    )

    out = {
        **{
            k: rec[k] for k in ("run_id", "arm", "provider", "prompt_id", "kind", "rep")
        },
        "root_sid": sid,
        "valid": valid,
        "n_tool_post": len(posts),
        "n_transcript_role_tool": trole,
        "thinking_mentions": thinking_mentions,
        "tool_seq": [t for t, _ in seq][:12],
        "cost_usd": round(cost, 6),
        "requests": reqs,
        "wall_s": rec.get("wall_s"),
    }

    if rec["kind"] == "control":
        over = [t for t, _ in seq if t in ("delegate", "load_skill")]
        out["over_reach"] = len(over) > 0
        out["over_reach_tools"] = over
        out["pass"] = (not out["over_reach"]) and valid
        return out

    spec = spec_by_id[rec["prompt_id"]]
    eq = set(spec["equivalence_set"]) | {spec["expected_target"]}
    first_reach = None
    for tname, tgt in first_n:
        if tname in REACH_TOOLS:
            first_reach = tgt
            break
    out["first_reach"] = first_reach
    out["first_reach_within_N"] = first_reach is not None
    out["pass"] = bool(first_reach is not None and first_reach in eq) and valid
    out["expected"] = spec["expected_target"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--captures", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--N", type=int, default=4)
    a = ap.parse_args()

    spec = json.loads(Path(a.prompts).read_text())
    by_id = {p["id"]: p for p in spec["hidden"]}
    recs = [
        json.loads(ln) for ln in Path(a.runs).read_text().splitlines() if ln.strip()
    ]
    caps = Path(a.captures)
    graded = [grade_run(r, caps, by_id, a.N) for r in recs]
    Path(a.out).write_text("\n".join(json.dumps(g) for g in graded) + "\n")

    tot = sum(g["cost_usd"] for g in graded)
    print(f"graded {len(graded)} runs, total cost ${tot:.4f}")
    for g in graded:
        print(
            f"  {g['run_id']:>28} valid={str(g['valid']):5} pass={str(g.get('pass')):5} "
            f"${g['cost_usd']:.4f} tools={g.get('tool_seq')} reach={g.get('first_reach') or g.get('over_reach_tools')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
