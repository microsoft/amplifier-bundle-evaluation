#!/usr/bin/env python3
"""webu -- Phase 2 analyzer. Regenerates every table in FINDINGS.md from the
captures and SPENDS NOTHING (12v's convention).

Every rule implemented here is fixed in:
  PREREG.md            c37ad942822e9c648bdc8b6cb10250950c512a96
  PREREG-ADDENDUM-A.md ce4add33a29da9f80c81ff8d848ee06e1498d907
both committed before the numbers existed.

Usage:  analyze.py --cap <capture-root> [--json out.json]
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import re
import statistics
from collections import Counter
from pathlib import Path

CHARS_PER_TOKEN = 4.627  # 12v's measured constant; bub/cal reproduce 8,677 and 1,104 with it
CACHEABLE_MIN = 1024  # OpenAI cacheable minimum (P4)
FILE_DOMAIN = {"read_file", "write_file", "edit_file", "glob", "grep", "apply_patch"}
SURROGATE_RE = re.compile(r"^(cat|head|tail|less|sed|grep|rg|ls|find|awk|cut|wc|touch|mkdir|cp|mv)\b")
# supplementary, NOT the pre-registered verdict: the subset that directly duplicates a deferred
# `files` tool (read_file / grep). `wc`/`ls`/`mkdir`/`cp` have no tool equivalent at all.
STRONG_SURROGATE_RE = re.compile(r"^(cat|head|tail|less|sed|grep|rg)\b")
REDIRECT_RE = re.compile(r">>?\s*\S+\.[A-Za-z0-9]{1,6}\b")
CD_PREFIX_RE = re.compile(r"^\s*cd\s+[^&;|]+(&&|;)\s*")
G12_PHRASE = "No tool call found for function call output"
MISSING_NS = "Missing namespace for function_call"


def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def session_files(run: Path) -> list[Path]:
    out = []
    for f in glob.glob(str(run / "all-sessions" / "**" / "sessions" / "*" / "events.jsonl"), recursive=True):
        if "/context-intelligence/" in f:
            continue
        out.append(Path(f))
    return out


def sid_of(f: Path) -> str:
    s = str(f)
    return s.split("/sessions/")[1].split("/")[0] if "/sessions/" in s else ""


def iter_events(f: Path):
    try:
        fh = f.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def tree_files(run: Path, root_sid: str) -> tuple[list[Path], list[Path]]:
    """(root_session_files, whole_tree_files) resolved by parent_id chain."""
    files = session_files(run)
    parent: dict[str, str | None] = {}
    by_sid: dict[str, Path] = {}
    for f in files:
        s = sid_of(f)
        by_sid.setdefault(s, f)
        p = None
        for d in iter_events(f):
            data = d.get("data", {})
            if "parent_id" in data:
                p = data["parent_id"]
                break
        parent[s] = p

    def in_tree(s: str) -> bool:
        seen, cur = set(), s
        while cur and cur not in seen:
            if cur == root_sid:
                return True
            seen.add(cur)
            cur = parent.get(cur)
        return False

    tree = [f for f in files if root_sid and in_tree(sid_of(f))]
    root = [by_sid[root_sid]] if root_sid in by_sid else []
    return root, (tree or files)


def canon(o) -> str:
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(o) -> str:
    return hashlib.sha256(canon(o).encode()).hexdigest()


def usage_of(ev) -> dict:
    d = ev.get("data", {})
    u = d.get("usage") or (d.get("raw") or {}).get("usage") or {}
    return u if isinstance(u, dict) else {}


def cached_tokens(u: dict) -> int:
    for k in ("cache_read_tokens", "cached_tokens", "cache_read_input_tokens"):
        if isinstance(u.get(k), int):
            return u[k]
    det = u.get("input_tokens_details") or {}
    if isinstance(det, dict) and isinstance(det.get("cached_tokens"), int):
        return det["cached_tokens"]
    return 0


def scan_run(run: Path) -> dict:
    meta = jload(run / "meta.json", {}) or {}
    drv = jload(run / "driver_record.json", {}) or {}
    score = jload(run / "scorecard.json", {}) or {}
    meas = jload(run / "measure.json", {}) or {}
    root_sid = (run / "root_sid.txt").read_text().strip() if (run / "root_sid.txt").exists() else ""
    md5f = run / "driver_md5.txt"
    r: dict = {
        "run": run.name,
        "arm": meta.get("arm", run.name.split("-")[0]),
        "dtu": meta.get("dtu"),
        "driver_md5": meta.get("driver_md5") or (md5f.read_text().strip() if md5f.exists() else None),
        "root_sid": root_sid,
        "turns_done": sum(1 for t in drv.get("turns", []) if t.get("done")),
        "continuity_ok": drv.get("session_continuity_ok"),
        "wall_s": drv.get("wall_s") or meas.get("wall_s"),
        "score_total": score.get("total"),
        "score_pass": score.get("pass"),
        "dimensions": score.get("dimensions", {}),
        "constraint_breakdown": score.get("constraint_breakdown", {}),
        "checks": {c.get("check"): bool(c.get("ok")) for c in score.get("checks", [])},
        "cost_usd": meas.get("cost_usd"),
        "cache_read_share_pct": meas.get("cache_read_share_pct"),
        "llm_calls": meas.get("llm_calls"),
        "root_delegate_calls": meas.get("root_delegate_calls"),
    }
    root_files, all_files = tree_files(run, root_sid)

    cached_vals: list[int] = []
    tools_block_wire_tok = None
    loaded: set[str] = set()
    ts_entry_seen = defer_seen = ns_roundtrip_seen = False
    first_tools_names: list = []
    first_input_chars = first_instr_chars = None
    root_requests = boundaries = 0
    trace: list[tuple[str, int]] = []   # ordered ("boundary"|"resp", cache_read) on the root session
    head_tok_prime = None          # E-A' : request-0 total billed prompt
    cache_write_req0 = None        # bytes written into the cache at req0 = the pinned head
    uncached_req0 = None           # billed-but-not-cached remainder at req0
    first_cached_read = None       # independent server-side cross-check
    pending_tools = False          # did the request just seen carry a tools array?
    for f in root_files:
        for ev in iter_events(f):
            name = ev.get("event") or ev.get("type") or ""
            if "compact" in name.lower():
                boundaries += 1
                trace.append(("boundary", 0))
            if name == "llm:request":
                raw = (ev.get("data") or {}).get("raw") or {}
                tools = raw.get("tools")
                pending_tools = isinstance(tools, list) and len(tools) > 0
                if isinstance(tools, list):
                    root_requests += 1
                    if tools_block_wire_tok is None:
                        tools_block_wire_tok = round(len(canon(tools)) / CHARS_PER_TOKEN, 1)
                        first_tools_names = [t.get("name") or t.get("type") for t in tools if isinstance(t, dict)]
                        first_input_chars = len(canon(raw.get("input") or []))
                        first_instr_chars = len(raw.get("instructions") or "")
                    for t in tools:
                        if not isinstance(t, dict):
                            continue
                        if t.get("type") == "tool_search":
                            ts_entry_seen = True
                        if t.get("defer_loading") is True:
                            defer_seen = True
                        members = t.get("members") or t.get("tools")
                        if isinstance(members, list):
                            # a namespace: only NON-deferred members are actually loaded
                            # (deferred ones ship a stub the model cannot call until it searches)
                            for m in members:
                                if isinstance(m, dict):
                                    if m.get("defer_loading") is True:
                                        defer_seen = True  # defer_loading rides on MEMBERS, not the namespace
                                    else:
                                        loaded.add(m.get("name"))
                                else:
                                    loaded.add(m)
                        elif t.get("name") and t.get("type") != "tool_search":
                            loaded.add(t["name"])
                inp = raw.get("input")
                if isinstance(inp, list):
                    for it in inp:
                        if isinstance(it, dict) and it.get("type") == "function_call" and it.get("namespace"):
                            ns_roundtrip_seen = True
            elif name == "llm:response":
                u = usage_of(ev)
                c = cached_tokens(u)
                trace.append(("resp", c))
                if c >= CACHEABLE_MIN:
                    cached_vals.append(c)
                    if first_cached_read is None:
                        first_cached_read = c
                if head_tok_prime is None and pending_tools:
                    it_, cw_ = u.get("input_tokens"), u.get("cache_write_tokens")
                    if isinstance(it_, int) and isinstance(cw_, int):
                        head_tok_prime = it_ + cw_
                        cache_write_req0 = cw_
                        uncached_req0 = it_ - (cached_tokens(u) or 0)
                pending_tools = False
                raw = (ev.get("data") or {}).get("raw") or {}
                out = raw.get("output")
                if isinstance(out, list):
                    for it in out:
                        if isinstance(it, dict) and it.get("type") == "tool_search_output":
                            for t in it.get("tools") or []:
                                if isinstance(t, dict) and isinstance(t.get("tools"), list):
                                    # the output echoes a NAMESPACE object; its members are what loaded
                                    for m in t["tools"]:
                                        loaded.add(m.get("name") if isinstance(m, dict) else m)
                                else:
                                    loaded.add(t.get("name") if isinstance(t, dict) else t)

    r["root_requests"] = root_requests
    r["boundaries"] = boundaries
    rewarm: list[int] = []
    for i, (kind, _) in enumerate(trace):
        if kind != "boundary":
            continue
        pre = next((v for k, v in reversed(trace[:i]) if k == "resp"), 0)
        if pre <= 0:
            continue
        d = 0
        for k, v in trace[i + 1:]:
            if k != "resp":
                continue
            d += 1
            if v >= 0.5 * pre:
                break
        else:
            d = -1  # never re-warmed before the session ended
        rewarm.append(d)
    r["rewarm_distances"] = rewarm
    r["rewarm_max"] = max(rewarm) if rewarm else None
    # E-B, renamed: this is the WIRE PAYLOAD, not the billed prompt (ADDENDUM-B B2)
    r["tools_block_wire_tok"] = tools_block_wire_tok
    r["first_tools_entries"] = first_tools_names
    r["req0_input_chars"] = first_input_chars
    r["req0_instructions_chars"] = first_instr_chars
    r["tool_search_entry_on_wire"] = ts_entry_seen
    r["defer_loading_on_wire"] = defer_seen
    r["namespace_roundtrip_on_wire"] = ns_roundtrip_seen
    r["head_tok_prime"] = head_tok_prime                 # E-A'  (ADDENDUM-B B3)
    r["cache_write_req0"] = cache_write_req0             # independent corroboration of the head
    r["uncached_req0"] = uncached_req0                   # cold-start non-cacheable term
    r["first_cached_read"] = first_cached_read           # cross-check
    r["pinned_head_tok_MODAL_DEFECTIVE"] = Counter(cached_vals).most_common(1)[0][0] if cached_vals else None
    r["pinned_head_n"] = len(cached_vals)
    r["loaded_tools"] = sorted(x for x in loaded if x)
    r["loaded_count"] = len(r["loaded_tools"])

    surrogate = filedom = strong = bash_total = 0
    tool_calls: Counter = Counter()
    surrogate_examples: list[str] = []
    strong_examples: list[str] = []
    for f in all_files:
        for ev in iter_events(f):
            if (ev.get("event") or "") != "tool:pre":
                continue
            d = ev.get("data", {})
            # the event field is `tool_name` / `tool_input` in this harness; earlier drafts of
            # this analyzer looked only at `tool`/`arguments` and were therefore INERT on bash
            # (0 surrogates in every run of both arms) -- the i0cm failure mode, caught before
            # the verdict was banked. Every plausible field name is tried now.
            tool = d.get("tool_name") or d.get("tool") or d.get("name")
            if tool:
                tool_calls[tool] += 1
            if tool in FILE_DOMAIN:
                filedom += 1
            elif tool == "bash":
                args = d.get("tool_input") or d.get("arguments") or d.get("args") or d.get("input") or {}
                cmd = args.get("command") if isinstance(args, dict) else None
                if not isinstance(cmd, str):
                    cmd = json.dumps(args)[:400] if args else ""
                stripped = cmd
                for _ in range(3):
                    stripped = CD_PREFIX_RE.sub("", stripped)
                stripped = stripped.strip()
                if SURROGATE_RE.match(stripped) or REDIRECT_RE.search(cmd):
                    surrogate += 1
                    if len(surrogate_examples) < 3:
                        surrogate_examples.append(cmd[:140])
                    if STRONG_SURROGATE_RE.match(stripped):
                        strong += 1
                        if len(strong_examples) < 3:
                            strong_examples.append(cmd[:140])
                bash_total += 1
    r["d2_surrogate_calls"] = surrogate
    r["d2_file_domain_calls"] = filedom
    denom = surrogate + filedom
    r["d2_sub_rate"] = round(surrogate / denom, 4) if denom else None
    r["d2_examples"] = surrogate_examples
    r["d2_bash_calls"] = bash_total
    r["d2_strong_surrogate_calls"] = strong
    r["d2_strong_sub_rate"] = round(strong / (strong + filedom), 4) if (strong + filedom) else None
    r["d2_strong_examples"] = strong_examples
    r["tool_calls"] = dict(tool_calls)

    blob_parts = []
    for p in list(run.glob("turn*.out")) + [run / "driver.log", run / "run.log"]:
        if p.exists():
            try:
                blob_parts.append(p.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    for f in all_files:
        try:
            blob_parts.append(f.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            pass
    blob = "\n".join(blob_parts)
    # EVAL-SPEC G12 names ONE string; matching the bare token `InvalidRequestError` is a
    # FALSE POSITIVE on this scenario, whose seeded reference source is provider config
    # validation code that contains it. Only the full phrase counts.
    r["g12_hits"] = blob.count(G12_PHRASE)
    r["g12_bare_token_mentions"] = blob.count("InvalidRequestError")
    r["missing_namespace_400"] = blob.count(MISSING_NS)

    anth: list[dict] = []
    for f in root_files:
        for ev in iter_events(f):
            if (ev.get("event") or "") != "llm:request":
                continue
            d = ev.get("data", {})
            if "anthropic" not in str(d.get("provider", "")).lower():
                continue
            raw = d.get("raw") or {}
            tools = raw.get("tools")
            if not isinstance(tools, list):
                continue
            markers = [i for i, t in enumerate(tools) if isinstance(t, dict) and t.get("cache_control")]
            anth.append({
                "tools_sha": sha(tools), "n_tools": len(tools),
                "marker_indices": markers, "marker_count": len(markers),
                "last_index": len(tools) - 1,
                "system_sha": sha(raw.get("system")), "system_bytes": len(canon(raw.get("system"))),
                "messages_canon": canon(raw.get("messages"))[:400000],
            })
    r["anth_requests"] = [{k: v for k, v in a.items() if k != "messages_canon"} for a in anth]
    r["_anth_raw"] = anth

    reasons = []
    if r["turns_done"] != 5:
        reasons.append(f"V1 turns_done={r['turns_done']}")
    if r["continuity_ok"] is not True:
        reasons.append(f"V2 continuity_ok={r['continuity_ok']}")
    if not root_sid or r["root_requests"] == 0:
        reasons.append("V3 no root session / no llm requests")
    if not isinstance(r["score_total"], (int, float)):
        reasons.append("V4 no numeric scorecard total")
    if r["missing_namespace_400"]:
        reasons.append(f"V5 HTTP400 Missing namespace x{r['missing_namespace_400']}")
    r["valid"] = not reasons
    r["invalid_reasons"] = reasons
    return r


def med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(statistics.median(xs), 2) if xs else None


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(statistics.fmean(xs), 4) if xs else None


E5_CONSTRAINTS = [
    ("C1_stdlib_only", lambda r: r["constraint_breakdown"].get("C1_stdlib_only", 0) > 0),
    ("C2_exit_codes", lambda r: r["constraint_breakdown"].get("C2_exit_codes", 0) > 0),
    ("C3_under_120_lines", lambda r: r["constraint_breakdown"].get("C3_under_120_lines", 0) > 0),
    ("turn2_retention_b_constraints_ge20", lambda r: (r["dimensions"].get("b_constraints") or 0) >= 20),
    ("turn3_revision_c_revision_ge10", lambda r: (r["dimensions"].get("c_revision") or 0) >= 10),
    ("turn5_extension_suggest", lambda r: any(v for k, v in r["checks"].items() if k and "--suggest" in k)),
]


def analyse(cap: Path) -> dict:
    runs = [scan_run(p) for p in sorted((cap / "runs").glob("*")) if p.is_dir()]
    arms = {a: [r for r in runs if r["arm"] == a] for a in ("t0", "t1", "g0", "g1")}
    valid = {a: [r for r in rs if r["valid"]] for a, rs in arms.items()}
    out: dict = {
        "capture_root": str(cap),
        "prereg": {"PREREG.md": "c37ad942822e9c648bdc8b6cb10250950c512a96",
                   "PREREG-ADDENDUM-A.md": "ce4add33a29da9f80c81ff8d848ee06e1498d907"},
        "driver_md5_expected": "dc307c50090b11d981eee44382668431",
        "provider_openai_pin": "702b361a4d4d178da70cef96300591dc4015b9b1",
        "runs": runs, "per_arm": {}, "gates": {}, "spend": {},
    }
    for a in ("t0", "t1", "g0", "g1"):
        rs, vs = arms[a], valid[a]
        out["per_arm"][a] = {
            "launches": len(rs), "valid": len(vs),
            "achieved_validity": round(len(vs) / len(rs), 4) if rs else None,
            "invalid_reasons": [{"run": r["run"], "why": r["invalid_reasons"]} for r in rs if not r["valid"]],
            "spend_usd": round(sum(r["cost_usd"] or 0 for r in rs), 6),
            "cost_per_launch": round(sum(r["cost_usd"] or 0 for r in rs) / len(rs), 6) if rs else None,
            "median_score": med([r["score_total"] for r in vs]),
            "strict_pass": sum(1 for r in vs if r["score_pass"]),
            "median_head_tok_prime": med([r["head_tok_prime"] for r in vs]),
            "median_first_cached_read": med([r["first_cached_read"] for r in vs]),
            "median_cache_write_req0": med([r["cache_write_req0"] for r in vs]),
            "median_uncached_req0": med([r["uncached_req0"] for r in vs]),
            "median_pinned_head_MODAL_DEFECTIVE": med([r["pinned_head_tok_MODAL_DEFECTIVE"] for r in vs]),
            "median_tools_block_wire_tok": med([r["tools_block_wire_tok"] for r in vs]),
            "mean_cost": mean([r["cost_usd"] for r in vs]),
            "mean_boundaries": mean([r["boundaries"] for r in vs]),
            "median_loaded_count": med([r["loaded_count"] for r in vs]),
            "median_d2_sub_rate": med([r["d2_sub_rate"] for r in vs]),
            "median_d2_strong_sub_rate": med([r["d2_strong_sub_rate"] for r in vs]),
            "total_bash_calls": sum(r["d2_bash_calls"] for r in vs),
            "total_file_domain_calls": sum(r["d2_file_domain_calls"] for r in vs),
            "total_surrogate_calls": sum(r["d2_surrogate_calls"] for r in vs),
            "total_strong_surrogate_calls": sum(r["d2_strong_surrogate_calls"] for r in vs),
            "mean_wall_s": mean([r["wall_s"] for r in vs]),
            "g12_hits_total": sum(r["g12_hits"] for r in rs),
            "driver_md5_ok": all(r["driver_md5"] == out["driver_md5_expected"] for r in rs) if rs else None,
        }
    G = out["gates"]
    t0a, t1a = out["per_arm"]["t0"], out["per_arm"]["t1"]
    n0, n1 = t0a["valid"], t1a["valid"]

    # ---- G9. Verdict on PINNED CACHE_READ -- the quantity EVAL-SPEC G9 names (ADDENDUM-C C3).
    #      E-A' (total billed prompt), E-A (modal) and E-B (wire) are all still reported.
    pc0, pc1 = t0a["median_first_cached_read"], t1a["median_first_cached_read"]
    ea0, ea1 = t0a["median_head_tok_prime"], t1a["median_head_tok_prime"]
    cw0, cw1 = t0a["median_cache_write_req0"], t1a["median_cache_write_req0"]
    eb0, eb1 = t0a["median_tools_block_wire_tok"], t1a["median_tools_block_wire_tok"]
    md0, md1 = t0a["median_pinned_head_MODAL_DEFECTIVE"], t1a["median_pinned_head_MODAL_DEFECTIVE"]
    nc0, nc1 = t0a["median_uncached_req0"], t1a["median_uncached_req0"]
    if pc0 is None or pc1 is None:
        G["G9"] = {"verdict": "NOT-POSSIBLE", "why": "no pinned cache_read datum in one or both arms",
                   "pinned_cache_read": [pc0, pc1]}
    else:
        dir_p = pc1 - pc0
        dir_c = (cw1 - cw0) if (cw0 is not None and cw1 is not None) else None
        disagree = dir_c is not None and ((dir_p < 0) != (dir_c < 0)) and abs(dir_p) > 1 and abs(dir_c) > 1
        v = "UNINFORMATIVE" if disagree else ("PASS" if pc1 <= pc0 - 3000 else "FAIL")
        G["G9"] = {
            "verdict": v,
            "rule": "t1 median pinned cache_read <= t0 median - 3000 tok (EVAL-SPEC G9, VERBATIM, threshold unchanged)",
            "quantity": "pinned cache_read = cached_tokens of the first root response reporting >= 1024 (ADDENDUM-B cross-check; ADDENDUM-C C3)",
            "pinned_cache_read_t0": pc0, "pinned_cache_read_t1": pc1,
            "PINNED_HEAD_SAVING_tok": round(-dir_p, 1),
            "PINNED_HEAD_SAVING_pct_of_t0_head": round(100.0 * (-dir_p) / pc0, 1) if pc0 else None,
            "independent_corroboration_cache_write_at_req0_t0": cw0,
            "independent_corroboration_cache_write_at_req0_t1": cw1,
            "corroboration_saving": round(-dir_c, 1) if dir_c is not None else None,
            "corroboration_agrees_within_tok": abs((-dir_p) - (-dir_c)) if dir_c is not None else None,
            "estimators_disagree_in_direction": disagree,
            "req0_input_chars_identical_across_arms": len({r["req0_input_chars"] for r in valid["t0"] + valid["t1"] if r["req0_input_chars"]}) == 1,
            "req0_instructions_chars_identical_across_arms": len({r["req0_instructions_chars"] for r in valid["t0"] + valid["t1"] if r["req0_instructions_chars"]}) == 1,
            "COLD_START_DECOMPOSITION": {
                "total_billed_prompt_at_req0_t0": ea0, "total_billed_prompt_at_req0_t1": ea1,
                "cold_request_saving_tok": round((ea0 - ea1), 1) if (ea0 is not None and ea1 is not None) else None,
                "non_cached_treatment_only_term_t0": nc0, "non_cached_treatment_only_term_t1": nc1,
                "cold_start_cost_tok": round((nc1 - nc0), 1) if (nc0 is not None and nc1 is not None) else None,
                "note": "reported ALWAYS, both directions (ADDENDUM-C C4): the pinned saving applies from the 2nd request onward; the cold request pays a one-off non-cacheable term.",
            },
            "E_A_prime_REPORTED_NOT_VERDICT": {"t0": ea0, "t1": ea1,
                "saving": round((ea0 - ea1), 1) if (ea0 is not None and ea1 is not None) else None,
                "defect": "total-billed-prompt measure; the treatment arm's total prompt carries a non-cacheable term the control does not, so it is not 'pinned cache_read' (ADDENDUM-C C2). Reported, not repaired."},
            "E_A_MODAL_DEFECTIVE": {"t0": md0, "t1": md1,
                "defect": "tracks transcript length, arm-asymmetrically (ADDENDUM-B B1). Reported, not repaired."},
            "E_B_WIRE_PAYLOAD": {"t0": eb0, "t1": eb1,
                "note": "WIRE payload, NOT the billed prompt (ADDENDUM-B B2): deferred member schemas travel but are not billed. 12v's chars/4.627 method misreads a namespaced block as a small LOSS."},
            "n": {"t0": n0, "t1": n1},
        }

    m0, m1 = t0a["median_score"], t1a["median_score"]
    p0, p1 = t0a["strict_pass"], t1a["strict_pass"]
    if not n0 or not n1:
        G["G10"] = {"verdict": "NOT-POSSIBLE", "why": "an arm has no valid runs", "n": {"t0": n0, "t1": n1}}
    elif m0 == m1 == 100 and p0 == n0 and p1 == n1:
        G["G10"] = {"verdict": "UNINFORMATIVE",
                    "why": "both arms at the S3 ceiling -- never banked as no-harm (00-what-we-know.md:55)",
                    "median": [m0, m1], "strict_pass": [f"{p0}/{n0}", f"{p1}/{n1}"]}
    else:
        ok = (m1 >= m0 - 5) and (p1 >= p0 - 1)
        G["G10"] = {"verdict": "PASS" if ok else "FAIL",
                    "rule": "t1 median >= t0 median - 5 AND t1 strict-pass >= t0 - 1",
                    "median": [m0, m1], "strict_pass": [f"{p0}/{n0}", f"{p1}/{n1}"],
                    "n_prereg": 10, "n_achieved": {"t0": n0, "t1": n1}}

    e5c = {}
    for cname, fn in E5_CONSTRAINTS:
        c0 = sum(1 for r in valid["t0"] if fn(r))
        c1 = sum(1 for r in valid["t1"] if fn(r))
        e5c[cname] = {"t0": f"{c0}/{n0}", "t1": f"{c1}/{n1}", "drop": c0 - c1, "fail": (c1 <= c0 - 2)}
    e5_total = G["G10"]["verdict"]
    e5cf = any(v["fail"] for v in e5c.values())
    G["E5"] = {"verdict": "FAIL" if e5cf else e5_total, "E5_total": e5_total,
               "E5_constraint": "FAIL" if e5cf else "PASS", "per_constraint": e5c,
               "note": "6ei recorded E5_quality NOT MEASURED; that omission is one of the two reasons PR 83 reverted PR 82."}

    b0, b1 = t0a["mean_boundaries"], t1a["mean_boundaries"]
    cadence = ("UNDEFINED (t0 mean boundaries == 0)" if not b0
               else ("within" if abs((b1 or 0) - b0) <= 0.15 * b0 else "outside"))
    cok = (t1a["mean_cost"] is not None and t0a["mean_cost"] is not None and t1a["mean_cost"] <= t0a["mean_cost"])
    G["G11"] = {"verdict": ("PASS" if (cok and cadence == "within") else ("PARTIAL" if cok else "FAIL")) if b0
                else "ADVISORY-COST-ONLY", "advisory": True,
                "mean_cost": [t0a["mean_cost"], t1a["mean_cost"]], "mean_boundaries": [b0, b1],
                "cadence_clause": cadence, "cost_clause": "PASS" if cok else "FAIL"}

    l1 = t1a["median_loaded_count"]
    G["G4prime"] = {"verdict": ("NOT-POSSIBLE" if l1 is None else ("PASS" if l1 <= 10 else "FAIL")),
                    "rule": "median distinct tools actually loaded per run <= 10 of 14",
                    "median_loaded_t1": l1, "median_loaded_t0": t0a["median_loaded_count"],
                    "per_run_t1": [{"run": r["run"], "n": r["loaded_count"], "tools": r["loaded_tools"]} for r in valid["t1"]]}

    g12 = sum(r["g12_hits"] for r in arms["t1"])
    G["G12"] = {"verdict": ("NOT-POSSIBLE" if not arms["t1"] else ("PASS" if g12 == 0 else "FAIL")),
                "rule": "InvalidRequestError: No tool call found for function call output == 0 across all t1 runs (EVAL-SPEC G12, verbatim)",
                "hits": g12, "n_runs_scanned": len(arms["t1"]),
                "bare_token_mentions_EXCLUDED_as_false_positives": sum(r["g12_bare_token_mentions"] for r in arms["t1"]),
                "false_positive_note": "the S3 scenario seeds provider config-validation SOURCE that contains the bare token InvalidRequestError; matching it alone scores the scenario text, not a failure"}

    tb1 = sum(r["boundaries"] for r in valid["t1"])
    G["G13"] = {"verdict": "UNINFORMATIVE" if tb1 == 0 else "NOT-POSSIBLE",
                "why": ("no compaction boundary was crossed in any valid t1 run -- a fact about S3's length; "
                        "the dependency is still unlanded" if tb1 == 0 else
                        "compaction boundaries occurred but context-simple break 5 is UNLANDED (v5co shipped it "
                        "as a patch artifact with no home) -- the gate cannot be discharged"),
                "dependency": "amplifier-module-context-simple break 5 (v5co patch artifact, applies clean at a2a098b)",
                "t1_total_boundaries": tb1,
                "note": "never recorded PASS under either branch (PREREG.md section 3)"}

    # Guardrail arms are compared WITHIN A PAIR (ADDENDUM-B B5): pair k = {g0-0k, g1-0k}.
    # Pair 1 ran at the default compaction budget; pair 2 at 45,000 (>=3 boundaries).
    def _pair(run_name: str) -> str:
        return run_name.split("-")[-1]
    pairs = sorted({_pair(r["run"]) for r in valid["g0"] if r["_anth_raw"]} &
                   {_pair(r["run"]) for r in valid["g1"] if r["_anth_raw"]})
    G["G5_pairs_compared"] = pairs
    G["G5_pairs_incomplete"] = sorted(({_pair(r["run"]) for r in arms["g0"]} | {_pair(r["run"]) for r in arms["g1"]}) - set(pairs))
    g0r = [r for r in valid["g0"] if r["_anth_raw"] and _pair(r["run"]) in pairs]
    g1r = [r for r in valid["g1"] if r["_anth_raw"] and _pair(r["run"]) in pairs]
    if not g0r or not g1r:
        for k in ("G5a", "G5b_prime", "G5c", "G5d"):
            G[k] = {"verdict": "NOT-POSSIBLE",
                    "why": "no LIVE Anthropic requests captured in one or both guardrail arms; a static hash "
                           "comparison does NOT discharge this gate (cal)",
                    "g0_runs_with_anth": len(g0r), "g1_runs_with_anth": len(g1r)}
    else:
        div = []
        n = 0
        a0, a1 = [], []
        per_pair = {}
        for k in pairs:
            p0 = [x for r in g0r if _pair(r["run"]) == k for x in r["_anth_raw"]]
            p1 = [x for r in g1r if _pair(r["run"]) == k for x in r["_anth_raw"]]
            m = min(len(p0), len(p1))
            d = [i for i in range(m) if p0[i]["tools_sha"] != p1[i]["tools_sha"]]
            per_pair[k] = {"indices_compared": m, "divergences": len(d),
                           "g0_requests": len(p0), "g1_requests": len(p1)}
            div += [f"{k}[{i}]" for i in d]
            n += m
            a0 += p0
            a1 += p1
        G["G5a"] = {"verdict": "PASS" if not div else "FAIL",
                    "rule": "sha256(params['tools']) equal at EVERY request index; 0 divergences, no tolerance band",
                    "indices_compared": n, "divergences": len(div), "divergent_indices": div[:20],
                    "g0_sha_head": a0[0]["tools_sha"][:16], "g1_sha_head": a1[0]["tools_sha"][:16],
                    "g0_distinct_shas": len({x["tools_sha"] for x in a0}),
                    "g1_distinct_shas": len({x["tools_sha"] for x in a1}),
                    "per_pair": per_pair, "live": True}
        viol = []
        for arm, arr in (("g0", a0), ("g1", a1)):
            for i, x in enumerate(arr):
                if x["marker_count"] != 1:
                    viol.append(f"{arm}[{i}] B1 marker_count={x['marker_count']}")
                if x["marker_count"] == 0:
                    viol.append(f"{arm}[{i}] B2 no breakpoint used")
                if x["marker_indices"] and x["marker_indices"][-1] != x["last_index"]:
                    viol.append(f"{arm}[{i}] B3 marker at {x['marker_indices']} not last index {x['last_index']}")
                if x["marker_count"] > 4:
                    viol.append(f"{arm}[{i}] B4 markers>4")
        G["G5b_prime"] = {"verdict": "PASS" if not viol else "FAIL",
                          "rule": "B1 exactly one marker; B2 breakpoint used; B3 on the last entry; B4 <=4 markers -- "
                                  "ABSOLUTE per arm, per request (cal's re-scope: old-G5b has zero marginal coverage)",
                          "violations": viol[:20], "n_violations": len(viol),
                          "requests_checked": len(a0) + len(a1)}
        c_pairs = {}
        c_ok = True
        for k in pairs:
            p0 = [x for r in g0r if _pair(r["run"]) == k for x in r["_anth_raw"]]
            p1 = [x for r in g1r if _pair(r["run"]) == k for x in r["_anth_raw"]]
            d0, d1 = len({x["system_sha"] for x in p0}), len({x["system_sha"] for x in p1})
            bb0, bb1 = p0[0]["system_bytes"], p1[0]["system_bytes"]
            ok = (d0 == 1 and d1 == 1 and bb0 == bb1)
            c_ok = c_ok and ok
            c_pairs[k] = {"g0_distinct": d0, "g1_distinct": d1, "g0_bytes": bb0,
                          "g1_bytes": bb1, "byte_delta": bb1 - bb0, "pass": ok}
        G["G5c"] = {"verdict": "PASS" if c_ok else "FAIL",
                    "rule": "distinct system sha per run == 1; byte delta g1 vs g0 == +0 B (within pair)",
                    "per_pair": c_pairs}
        d_pairs = {}
        share_ok_all = True
        for k in pairs:
            s0k = mean([r["cache_read_share_pct"] for r in g0r if _pair(r["run"]) == k])
            s1k = mean([r["cache_read_share_pct"] for r in g1r if _pair(r["run"]) == k])
            okk = s0k is not None and s1k is not None and abs(s1k - s0k) <= 10.0
            share_ok_all = share_ok_all and okk
            d_pairs[k] = {"share_g0": s0k, "share_g1": s1k,
                          "delta_pts": round(s1k - s0k, 2) if (s0k is not None and s1k is not None) else None,
                          "pass": okk,
                          "g0_boundaries": sum(r["boundaries"] for r in g0r if _pair(r["run"]) == k),
                          "g1_boundaries": sum(r["boundaries"] for r in g1r if _pair(r["run"]) == k)}
        sh0 = mean([r["cache_read_share_pct"] for r in g0r])
        sh1 = mean([r["cache_read_share_pct"] for r in g1r])
        idonly = 0
        for arr in (a0, a1):
            for i in range(1, len(arr)):
                p, c = arr[i - 1]["messages_canon"], arr[i]["messages_canon"]
                if p != c and len(p) == len(c):
                    if re.sub(r'"id":"[^"]*"', '"id":"X"', p) == re.sub(r'"id":"[^"]*"', '"id":"X"', c):
                        idonly += 1
        share_ok = share_ok_all
        rw_all = [d for r in g1r for d in r["rewarm_distances"]]
        rw_ok = all(0 <= d <= 1 for d in rw_all) if rw_all else None
        bnd = sum(r["boundaries"] for r in g1r)
        G["G5d"] = {"verdict": "PASS" if (share_ok and idonly == 0 and (rw_ok is not False)) else "FAIL",
                    "rule": "cache_read share within +-10 pts of g0; re-warm <=1 request at every boundary; ID_ONLY == 0",
                    "share_g0": sh0, "share_g1": sh1,
                    "share_delta_pts": round(sh1 - sh0, 2) if (sh0 is not None and sh1 is not None) else None,
                    "share_clause": "PASS" if share_ok else "FAIL", "per_pair": d_pairs,
                    "id_only_divergences": idonly,
                    "g1_boundaries": bnd,
                    "rewarm_clause": ("UNDEFINED (no boundary in g1)" if not rw_all
                                      else ("PASS" if rw_ok else "FAIL")),
                    "rewarm_distances_g1": rw_all,
                    "rewarm_distances_g0": [d for r in g0r for d in r["rewarm_distances"]],
                    "rewarm_rule": "requests after a boundary until cache_read returns to >= 50% of its pre-boundary value; <= 1 at every boundary",
                    "live": True}

    d0, d1 = t0a["median_d2_sub_rate"], t1a["median_d2_sub_rate"]
    opp0 = sum(1 for r in valid["t0"] if (r["d2_surrogate_calls"] + r["d2_file_domain_calls"]) == 0)
    opp1 = sum(1 for r in valid["t1"] if (r["d2_surrogate_calls"] + r["d2_file_domain_calls"]) == 0)
    uninf = (n0 and opp0 >= n0 / 2) or (n1 and opp1 >= n1 / 2)
    if d0 is None or d1 is None or uninf:
        G["D2"] = {"verdict": "UNINFORMATIVE", "why": "no substitution opportunity in >= half the runs of an arm",
                   "median_sub_rate": [d0, d1], "no_opportunity_runs": [opp0, opp1]}
    else:
        fires = (d1 - d0) >= 0.05
        G["D2"] = {"verdict": "FIRES -- DON'T-BUILD" if fires else "did not fire",
                   "rule": "median(sub_rate t1) - median(sub_rate t0) >= 0.05 (5 pp; 6ei observed 8.7 pp)",
                   "median_sub_rate_t0": d0, "median_sub_rate_t1": d1,
                   "delta_pp": round((d1 - d0) * 100, 2), "n": {"t0": n0, "t1": n1},
                   "counts_t0": {"bash": t0a["total_bash_calls"], "file_domain": t0a["total_file_domain_calls"],
                                 "surrogate": t0a["total_surrogate_calls"], "strong_surrogate": t0a["total_strong_surrogate_calls"]},
                   "counts_t1": {"bash": t1a["total_bash_calls"], "file_domain": t1a["total_file_domain_calls"],
                                 "surrogate": t1a["total_surrogate_calls"], "strong_surrogate": t1a["total_strong_surrogate_calls"]},
                   "supplementary_strong_median": [t0a["median_d2_strong_sub_rate"], t1a["median_d2_strong_sub_rate"]],
                   "supplementary_note": "the STRONG subset (cat/head/tail/sed/grep/rg) is reported as supplementary evidence only; the VERDICT is the pre-registered rule above. wc/ls/mkdir/cp have no deferred-tool equivalent and appear in BOTH arms, so they largely cancel in a differential.",
                   "6ei_reference": "read_file reached 21/23 deferred vs 13/13 static; both misses called bash"}

    # ---- TOOL REACH -- the D2-class channel the pre-registered D2 rule does not cover ----
    ALL_TOOLS = ["read_file", "write_file", "edit_file", "glob", "grep", "apply_patch", "bash",
                 "todo", "load_skill", "recipes", "mode", "delegate", "web_search", "web_fetch"]
    DEFERRED = {"read_file", "write_file", "edit_file", "glob", "grep", "load_skill", "recipes",
                "mode", "delegate", "web_search", "web_fetch"}
    reach = {}
    for t in ALL_TOOLS:
        r0 = sum(1 for r in valid["t0"] if r["tool_calls"].get(t, 0) > 0)
        r1 = sum(1 for r in valid["t1"] if r["tool_calls"].get(t, 0) > 0)
        c0 = sum(r["tool_calls"].get(t, 0) for r in valid["t0"])
        c1 = sum(r["tool_calls"].get(t, 0) for r in valid["t1"])
        reach[t] = {"t0_reach": f"{r0}/{n0}", "t1_reach": f"{r1}/{n1}", "t0_calls": c0, "t1_calls": c1,
                    "deferred": t in DEFERRED,
                    "vanished_in_treatment": (r0 > 0 and r1 == 0 and t in DEFERRED)}
    vanished = [t for t, v in reach.items() if v["vanished_in_treatment"]]
    G["TOOL_REACH_D2_CLASS"] = {
        "verdict": ("D2-CLASS SUBSTITUTION PRESENT" if vanished else "no tool vanished"),
        "rule": "NOT the pre-registered D2 rule -- this is 6ei's own D2 FORM ('tool reached in static "
                "but not deferred') applied to every tool, which the pre-registered rule (bash surrogates "
                "only) does not cover. Reported as a finding with its counts; the D2 VERDICT above is "
                "unchanged and did not fire.",
        "tools_reached_in_control_and_NEVER_in_treatment": vanished,
        "table": reach,
        "6ei_reference": "read_file reached 21/23 deferred vs 13/13 static -- 2 misses of ONE tool",
    }

    G["PIN_WIRE"] = {
        "P3_tool_search_and_defer_in_t1": any(r["tool_search_entry_on_wire"] and r["defer_loading_on_wire"] for r in arms["t1"]),
        "P4_namespace_roundtrip_in_t1": any(r["namespace_roundtrip_on_wire"] for r in arms["t1"]),
        "t0_control_provably_untreated": all(not r["tool_search_entry_on_wire"] and not r["defer_loading_on_wire"] for r in arms["t0"]),
        "missing_namespace_400s": sum(r["missing_namespace_400"] for r in runs),
    }

    total = sum(r["cost_usd"] or 0 for r in runs)
    terra = [r for r in runs if r["arm"] in ("t0", "t1")]
    anth = [r for r in runs if r["arm"] in ("g0", "g1")]
    vt = sum(1 for r in terra if r["valid"])
    va = sum(1 for r in anth if r["valid"])
    p_t = (sum(r["cost_usd"] or 0 for r in terra) / len(terra)) if terra else None
    p_a = (sum(r["cost_usd"] or 0 for r in anth) / len(anth)) if anth else None
    v_t = (vt / len(terra)) if terra else None
    v_a = (va / len(anth)) if anth else None
    v_tf = v_t if v_t else 0.67
    v_af = v_a if v_a else 0.67
    req = None
    if p_t is not None and p_a is not None:
        req = round(max(0, 20 - vt) / v_tf * p_t + max(0, 4 - va) / v_af * p_a, 2)
    out["spend"] = {
        "authority_usd": 170.00, "spent_usd": round(total, 6),
        "terra_launches": len(terra), "terra_valid": vt,
        "anth_launches": len(anth), "anth_valid": va,
        "observed_price_per_terra_launch": round(p_t, 4) if p_t is not None else None,
        "observed_price_per_anth_launch": round(p_a, 4) if p_a is not None else None,
        "achieved_validity_terra": round(v_t, 4) if v_t is not None else None,
        "achieved_validity_anth": round(v_a, 4) if v_a is not None else None,
        "validity_used_for_forecast": {"terra": v_tf, "anth": v_af,
                                       "floored_at_0.67_when_unobserved": (v_t is None or v_a is None)},
        "REQUIRED_REMAINING_for_n10_per_arm": req,
        "forecast_total": round(total + req, 2) if req is not None else None,
        "fundable_at_170": (total + req <= 170.0) if req is not None else None,
        "goal_quoted_price": {"terra": 4.63, "anth": 3.53, "validity": 0.67,
                              "goal_arithmetic": "30 x 4.63 + 6 x 3.53 = 160.08 <= 170.00 -- the goal's cap closes AT ITS OWN QUOTED PRICE"},
    }
    for r in runs:
        r.pop("_anth_raw", None)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = analyse(Path(a.cap))
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, default=str))
    print("=" * 96)
    print("webu Phase 2 -- gate summary (regenerated from captures, $0)")
    print("=" * 96)
    for k in ("t0", "t1", "g0", "g1"):
        p = res["per_arm"][k]
        print(f"{k}: launch={p['launches']} valid={p['valid']} v={p['achieved_validity']} "
              f"${p['spend_usd']:.4f} score={p['median_score']} pass={p['strict_pass']} "
              f"pinned={p['median_first_cached_read']} cw0={p['median_cache_write_req0']} unc0={p['median_uncached_req0']} "
              f"loaded={p['median_loaded_count']} bnd={p['mean_boundaries']} d2={p['median_d2_sub_rate']} "
              f"wall={p['mean_wall_s']} md5ok={p['driver_md5_ok']}")
        for iv in p["invalid_reasons"]:
            print(f"     INVALID {iv['run']}: {iv['why']}")
    print("-" * 96)
    for k, v in res["gates"].items():
        print(f"{k:22} {v.get('verdict', v) if isinstance(v, dict) else v}")
    print("-" * 96)
    print(json.dumps(res["spend"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
