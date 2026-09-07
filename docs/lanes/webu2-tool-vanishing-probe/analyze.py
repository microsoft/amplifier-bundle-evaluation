#!/usr/bin/env python3
"""`2gxp` -- three-arm tool-vanishing analyzer. Regenerates every table in
FINDINGS.md from the captures and SPENDS NOTHING.

Every rule implemented here is fixed in PREREG.md, committed before the first
API call of this lane. Definitions that must stay comparable with `webu`
(pinned cache_read, the D2 surrogate regex, tree resolution) are lifted verbatim
from `webu`'s analyze.py rather than re-derived.

Usage:  analyze.py --cap <capture-root> [--json out.json]
        analyze.py --validate-instrument <webu-capture-root>
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import statistics
from collections import Counter
from pathlib import Path

CHARS_PER_TOKEN = 4.627  # 12v's measured constant (webu analyze.py)
CACHEABLE_MIN = 1024  # OpenAI cacheable minimum (P4)
MISSING_NS = "Missing namespace for function_call"
G12_PHRASE = "No tool call found for function call output"

THREE = ("write_file", "edit_file", "delegate")
REPORT_TOOLS = (
    "write_file", "edit_file", "delegate", "apply_patch",
    "read_file", "grep", "glob", "bash", "todo", "load_skill", "mode", "recipes",
    "web_search", "web_fetch",
)
DRIVER_MD5 = "dc307c50090b11d981eee44382668431"
OPENAI_PIN = "702b361a4d4d178da70cef96300591dc4015b9b1"

# D2 (webu PREREG 1a), verbatim -- reported, not a verdict of this lane.
FILE_DOMAIN = {"read_file", "write_file", "edit_file", "glob", "grep", "apply_patch"}
SURROGATE_RE = re.compile(r"^(cat|head|tail|less|sed|grep|rg|ls|find|awk|cut|wc|touch|mkdir|cp|mv)\b")
REDIRECT_RE = re.compile(r">>?\s*\S+\.[A-Za-z0-9]{1,6}\b")
CD_PREFIX_RE = re.compile(r"^\s*cd\s+[^&;|]+(&&|;)\s*")


# ---------------------------------------------------------------- primitives


def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return default


def iter_jsonl(f: Path):
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


def sid_of(p) -> str:
    s = str(p)
    return s.split("/sessions/")[1].split("/")[0] if "/sessions/" in s else ""


def event_files(run: Path) -> list[Path]:
    return [
        Path(f)
        for f in glob.glob(str(run / "all-sessions" / "**" / "sessions" / "*" / "events.jsonl"), recursive=True)
        if "/context-intelligence/" not in f
    ]


def transcript_files(run: Path) -> list[Path]:
    # `.backup` files are excluded: they are a stale copy of the same transcript
    # and would double-count every call in them.
    return [
        Path(f)
        for f in glob.glob(str(run / "all-sessions" / "**" / "sessions" / "*" / "transcript.jsonl"), recursive=True)
    ]


def tree_files(run: Path, root_sid: str) -> tuple[list[Path], list[Path]]:
    """(root_session_event_files, whole_tree_event_files) by parent_id chain (webu)."""
    files = event_files(run)
    parent: dict[str, str | None] = {}
    by_sid: dict[str, Path] = {}
    for f in files:
        s = sid_of(f)
        by_sid.setdefault(s, f)
        p = None
        for d in iter_jsonl(f):
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


def usage_of(ev) -> dict:
    d = ev.get("data", {})
    u = d.get("usage") or (d.get("raw") or {}).get("usage") or {}
    return u if isinstance(u, dict) else {}


def cached_tokens(u: dict) -> int:
    for k in ("cache_read_tokens", "cached_tokens", "cache_read_input_tokens"):
        if isinstance(u.get(k), int):
            return u[k]
    return 0


def med(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(statistics.median(xs), 1) if xs else None


def mean(xs):
    xs = [x for x in xs if isinstance(x, (int, float))]
    return round(statistics.mean(xs), 4) if xs else None


# ------------------------------------------------------- the two discriminators


def count_role_tool(run: Path) -> Counter:
    """PRIMARY (PREREG section 2): `{"role":"tool","name":X}` transcript entries.

    A thinking-text mention of a tool name is NOT a call and is never counted.
    """
    c: Counter = Counter()
    for f in transcript_files(run):
        for d in iter_jsonl(f):
            if d.get("role") == "tool" and d.get("name"):
                c[d["name"]] += 1
    return c


def count_tool_pre(run: Path, tree: list[Path]) -> Counter:
    """CORROBORATING: `tool:pre` events (webu's counter)."""
    c: Counter = Counter()
    for f in tree:
        for ev in iter_jsonl(f):
            if (ev.get("event") or "") != "tool:pre":
                continue
            d = ev.get("data", {})
            n = d.get("tool_name") or d.get("tool") or d.get("name")
            if n:
                c[n] += 1
    return c


# ------------------------------------------------------------------ scan a run


def scan_run(run: Path) -> dict:
    meta = jload(run / "meta.json", {}) or {}
    r: dict = {
        "run": run.name,
        "arm": meta.get("arm") or run.name.split("-")[0],
        "driver_md5": (run / "driver_md5.txt").read_text().strip() if (run / "driver_md5.txt").exists() else None,
        "invalid_reasons": [],
    }
    root_sid = (run / "root_sid.txt").read_text().strip() if (run / "root_sid.txt").exists() else ""
    r["root_sid"] = root_sid
    root_files, all_files = tree_files(run, root_sid)

    m = jload(run / "measure.json", {}) or {}
    r["cost_usd"] = m.get("cost_usd")
    r["wall_s"] = m.get("wall_s")
    r["llm_calls"] = m.get("llm_calls")

    sc = jload(run / "scorecard.json", {}) or {}
    r["score_total"] = sc.get("total") if isinstance(sc.get("total"), (int, float)) else sc.get("score")
    r["score_pass"] = bool(sc.get("strict_pass") or sc.get("pass"))
    r["scorecard_ok"] = bool(sc)
    r["turns_captured"] = sum(1 for i in range(1, 6) if (run / f"turn{i}.out").exists())
    r["transcript_bytes"] = (run / "transcript.txt").stat().st_size if (run / "transcript.txt").exists() else 0

    # ---- wire: arm shape, pins, head
    ts_entry = False
    defer_any = False
    ns_roundtrip = False
    deferred_names: set[str] = set()
    loaded_names: set[str] = set()
    namespaces_seen: set[str] = set()
    first_tools_wire_tok = None
    first_input_chars = first_instr_chars = None
    root_requests = boundaries = 0
    first_cached_read = None
    cache_write_req0 = None
    head_tok_prime = None
    uncached_req0 = None
    pending_tools = False

    for f in root_files:
        for ev in iter_jsonl(f):
            name = ev.get("event") or ev.get("type") or ""
            if "compact" in name.lower():
                boundaries += 1
            if name == "llm:request":
                raw = (ev.get("data") or {}).get("raw") or {}
                tools = raw.get("tools")
                pending_tools = isinstance(tools, list) and len(tools) > 0
                if isinstance(tools, list):
                    root_requests += 1
                    if first_tools_wire_tok is None:
                        first_tools_wire_tok = round(len(canon(tools)) / CHARS_PER_TOKEN, 1)
                        first_input_chars = len(canon(raw.get("input") or []))
                        first_instr_chars = len(raw.get("instructions") or "")
                    for t in tools:
                        if not isinstance(t, dict):
                            continue
                        if t.get("type") == "tool_search":
                            ts_entry = True
                            continue
                        members = t.get("tools") if t.get("type") == "namespace" else None
                        if isinstance(members, list):
                            namespaces_seen.add(t.get("name") or "?")
                            for mm in members:
                                if not isinstance(mm, dict):
                                    continue
                                if mm.get("defer_loading") is True:
                                    defer_any = True
                                    deferred_names.add(mm.get("name"))
                                else:
                                    loaded_names.add(mm.get("name"))
                        else:
                            if t.get("defer_loading") is True:
                                defer_any = True
                                deferred_names.add(t.get("name"))
                            elif t.get("name"):
                                loaded_names.add(t["name"])
                            elif t.get("type"):
                                loaded_names.add(t["type"])
                inp = raw.get("input")
                if isinstance(inp, list):
                    for it in inp:
                        if isinstance(it, dict) and it.get("type") == "function_call" and it.get("namespace"):
                            ns_roundtrip = True
            elif name == "llm:response":
                u = usage_of(ev)
                c = cached_tokens(u)
                if c >= CACHEABLE_MIN and first_cached_read is None:
                    first_cached_read = c
                if head_tok_prime is None and pending_tools:
                    it_, cw_ = u.get("input_tokens"), u.get("cache_write_tokens")
                    if isinstance(it_, int) and isinstance(cw_, int):
                        head_tok_prime = it_ + cw_
                        cache_write_req0 = cw_
                        uncached_req0 = it_ - c
                pending_tools = False

    r["root_requests"] = root_requests
    r["boundaries"] = boundaries
    r["tool_search_entry_on_wire"] = ts_entry
    r["defer_loading_on_wire"] = defer_any
    r["namespace_roundtrip_on_wire"] = ns_roundtrip
    r["deferred_on_wire"] = sorted(x for x in deferred_names if x)
    r["loaded_on_wire"] = sorted(x for x in loaded_names if x)
    r["namespaces_on_wire"] = sorted(namespaces_seen)
    r["tools_block_wire_tok"] = first_tools_wire_tok
    r["req0_input_chars"] = first_input_chars
    r["req0_instructions_chars"] = first_instr_chars
    r["pinned_cache_read"] = first_cached_read
    r["cache_write_req0"] = cache_write_req0
    r["head_tok_prime"] = head_tok_prime
    r["uncached_req0"] = uncached_req0

    # ---- per-tool executed calls, both discriminators
    rt = count_role_tool(run)
    tp = count_tool_pre(run, all_files)
    r["calls_role_tool"] = {t: rt.get(t, 0) for t in REPORT_TOOLS}
    r["calls_tool_pre"] = {t: tp.get(t, 0) for t in REPORT_TOOLS}
    r["calls_role_tool_all"] = dict(rt)
    r["agg_three_role_tool"] = sum(rt.get(t, 0) for t in THREE)
    r["agg_three_tool_pre"] = sum(tp.get(t, 0) for t in THREE)

    # ---- D2 (webu's rule, reported)
    surrogate = filedom = bash_total = 0
    for f in all_files:
        for ev in iter_jsonl(f):
            if (ev.get("event") or "") != "tool:pre":
                continue
            d = ev.get("data", {})
            tool = d.get("tool_name") or d.get("tool") or d.get("name")
            args = d.get("tool_input") or d.get("arguments") or d.get("input") or {}
            if tool in FILE_DOMAIN:
                filedom += 1
            elif tool == "bash":
                bash_total += 1
                cmd = ""
                if isinstance(args, dict):
                    cmd = str(args.get("command") or "")
                elif isinstance(args, str):
                    cmd = args
                stripped = CD_PREFIX_RE.sub("", cmd).strip()
                if SURROGATE_RE.match(stripped) or REDIRECT_RE.search(stripped):
                    surrogate += 1
    r["d2_file_domain_calls"] = filedom
    r["d2_bash_calls"] = bash_total
    r["d2_surrogate_calls"] = surrogate
    denom = surrogate + filedom
    r["d2_sub_rate"] = round(surrogate / denom, 4) if denom else None

    # ---- error scan
    blob = ""
    for p in (run / "run.log", run / "driver.log"):
        if p.exists():
            blob += p.read_text(encoding="utf-8", errors="replace")
    for f in all_files:
        try:
            blob += f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            pass
    r["missing_namespace_400"] = blob.count(MISSING_NS)
    r["g12_hits"] = blob.count(G12_PHRASE)

    # ---- VALIDITY (PREREG section 4)
    if r["driver_md5"] != DRIVER_MD5:
        r["invalid_reasons"].append(f"V1 driver md5 {r['driver_md5']}")
    if r["turns_captured"] < 5 or r["transcript_bytes"] <= 0:
        r["invalid_reasons"].append(f"V2 turns={r['turns_captured']} transcript_bytes={r['transcript_bytes']}")
    arm = r["arm"]
    three_deferred = all(t in deferred_names for t in THREE)
    three_loaded = not any(t in deferred_names for t in THREE)
    others_deferred = all(t in deferred_names for t in ("read_file", "grep", "glob"))
    if arm == "c":
        if ts_entry or defer_any:
            r["invalid_reasons"].append("V3 arm c wire is TREATED (tool_search/defer present)")
    elif arm == "a":
        if not (ts_entry and three_deferred):
            r["invalid_reasons"].append(f"V3 arm a wire: ts_entry={ts_entry} three_deferred={three_deferred}")
    elif arm == "b":
        if not (ts_entry and three_loaded and others_deferred):
            r["invalid_reasons"].append(
                f"V3 arm b wire: ts_entry={ts_entry} three_loaded={three_loaded} others_deferred={others_deferred}"
            )
    if r["missing_namespace_400"]:
        r["invalid_reasons"].append(f"V4 HTTP400 Missing namespace x{r['missing_namespace_400']}")
    if not root_sid or r["cost_usd"] is None:
        r["invalid_reasons"].append("V5 root session / cost unresolved")
    r["valid"] = not r["invalid_reasons"]
    return r


# --------------------------------------------------------------------- analyse


def analyse(cap: Path, prereg_sha: str = "") -> dict:
    runs = [scan_run(p) for p in sorted((cap / "runs").glob("*")) if p.is_dir()]
    arms = {a: [r for r in runs if r["arm"] == a] for a in ("a", "b", "c")}
    valid = {a: [r for r in rs if r["valid"]] for a, rs in arms.items()}
    out: dict = {
        "capture_root": str(cap),
        "item": "model_performance-2gxp",
        "prereg_sha": prereg_sha,
        "driver_md5_expected": DRIVER_MD5,
        "provider_openai_pin": OPENAI_PIN,
        "discriminator": (
            'PRIMARY: {"role":"tool","name":X} entries in transcript.jsonl of every session in the run '
            "tree. A thinking-text mention is NOT a call. CORROBORATING: tool:pre events in events.jsonl."
        ),
        "arms": {
            "a": "treatment as-run -- tool_search namespaced, always_loaded [bash, todo] (reproduces webu t1)",
            "b": "treatment BUT write_file/edit_file/delegate kept ALWAYS-VISIBLE (rest still deferred)",
            "c": "control -- no tool_search (reproduces webu t0)",
        },
        "runs": runs,
        "per_arm": {},
        "per_tool": {},
        "rule": {},
        "spend": {},
    }

    for a in ("a", "b", "c"):
        rs, vs = arms[a], valid[a]
        out["per_arm"][a] = {
            "launches": len(rs),
            "valid": len(vs),
            "achieved_validity": round(len(vs) / len(rs), 4) if rs else None,
            "invalid": [{"run": r["run"], "why": r["invalid_reasons"]} for r in rs if not r["valid"]],
            "spend_usd": round(sum(r["cost_usd"] or 0 for r in rs), 6),
            "cost_per_launch": round(sum(r["cost_usd"] or 0 for r in rs) / len(rs), 6) if rs else None,
            "median_score": med([r["score_total"] for r in vs]),
            "strict_pass": sum(1 for r in vs if r["score_pass"]),
            "median_pinned_cache_read": med([r["pinned_cache_read"] for r in vs]),
            "median_cache_write_req0": med([r["cache_write_req0"] for r in vs]),
            "median_head_tok_prime": med([r["head_tok_prime"] for r in vs]),
            "median_uncached_req0": med([r["uncached_req0"] for r in vs]),
            "median_tools_block_wire_tok": med([r["tools_block_wire_tok"] for r in vs]),
            "mean_cost": mean([r["cost_usd"] for r in vs]),
            "mean_wall_s": mean([r["wall_s"] for r in vs]),
            "mean_boundaries": mean([r["boundaries"] for r in vs]),
            "median_d2_sub_rate": med([r["d2_sub_rate"] for r in vs]),
            "total_surrogate_calls": sum(r["d2_surrogate_calls"] for r in vs),
            "total_file_domain_calls": sum(r["d2_file_domain_calls"] for r in vs),
            "agg_three_calls_role_tool": sum(r["agg_three_role_tool"] for r in vs),
            "agg_three_per_run": round(sum(r["agg_three_role_tool"] for r in vs) / len(vs), 4) if vs else None,
            "runs_with_any_of_three": sum(1 for r in vs if r["agg_three_role_tool"] > 0),
            "missing_namespace_400s": sum(r["missing_namespace_400"] for r in rs),
            "g12_hits": sum(r["g12_hits"] for r in rs),
            "driver_md5_ok": all(r["driver_md5"] == DRIVER_MD5 for r in rs) if rs else None,
        }

    for t in REPORT_TOOLS:
        row = {}
        for a in ("a", "b", "c"):
            vs = valid[a]
            n = len(vs)
            row[a] = {
                "reach": f"{sum(1 for r in vs if r['calls_role_tool'][t] > 0)}/{n}",
                "calls_role_tool": sum(r["calls_role_tool"][t] for r in vs),
                "calls_tool_pre": sum(r["calls_tool_pre"][t] for r in vs),
                "calls_per_run": round(sum(r["calls_role_tool"][t] for r in vs) / n, 4) if n else None,
            }
        out["per_tool"][t] = row

    # ------------------------------------------------- THE RULE (PREREG s3)
    A, B, C = out["per_arm"]["a"], out["per_arm"]["b"], out["per_arm"]["c"]
    agg_b, agg_c = B["agg_three_per_run"], C["agg_three_per_run"]
    if not valid["b"] or not valid["c"]:
        clause1 = {"verdict": "NOT-POSSIBLE", "why": "an arm has no valid runs"}
    elif not agg_c:
        clause1 = {"verdict": "UNINFORMATIVE-ZERO-CONTROL", "agg_b": agg_b, "agg_c": agg_c}
    else:
        ratio = agg_b / agg_c
        clause1 = {
            "verdict": "PASS" if abs(ratio - 1) <= 0.30 else "FAIL",
            "rule": "|agg(b)/agg(c) - 1| <= 0.30 where agg = mean executed calls/run of "
            "write_file+edit_file+delegate from role:tool entries",
            "agg_b_per_run": agg_b,
            "agg_c_per_run": agg_c,
            "ratio": round(ratio, 4),
            "deviation_pct": round(100 * (ratio - 1), 1),
        }
    per_tool_clause = {}
    for t in THREE:
        cb = out["per_tool"][t]["b"]["calls_per_run"]
        cc = out["per_tool"][t]["c"]["calls_per_run"]
        if not cc:
            per_tool_clause[t] = {"verdict": "UNINFORMATIVE-ZERO-CONTROL", "b_per_run": cb, "c_per_run": cc}
        else:
            rr = cb / cc
            per_tool_clause[t] = {
                "verdict": "PASS" if abs(rr - 1) <= 0.30 else "FAIL",
                "b_per_run": cb, "c_per_run": cc, "ratio": round(rr, 4),
            }
    clause1["per_tool_REPORTED_NOT_VERDICT"] = per_tool_clause

    pc_a, pc_b, pc_c = A["median_pinned_cache_read"], B["median_pinned_cache_read"], C["median_pinned_cache_read"]
    if None in (pc_a, pc_b, pc_c):
        clause2 = {"verdict": "NOT-POSSIBLE", "why": "no pinned cache_read datum in an arm",
                   "median_pinned_cache_read": {"a": pc_a, "b": pc_b, "c": pc_c}}
    else:
        sav_a = round(pc_c - pc_a, 1)
        sav_b = round(pc_c - pc_b, 1)
        clause2 = {
            "verdict": "PASS" if sav_b >= 0.5 * sav_a else "FAIL",
            "rule": "saving(b) >= 0.50 * saving(a); saving(x) = median pinned cache_read(c) - median(x)",
            "median_pinned_cache_read": {"a": pc_a, "b": pc_b, "c": pc_c},
            "saving_a_tok": sav_a,
            "saving_b_tok": sav_b,
            "saving_b_as_pct_of_a": round(100 * sav_b / sav_a, 1) if sav_a else None,
            "corroboration_cache_write_req0": {
                "a": A["median_cache_write_req0"], "b": B["median_cache_write_req0"], "c": C["median_cache_write_req0"],
            },
            "PREREG_PREDICTION_P_A": "40.7%-48.1% of arm a's saving -> FAIL predicted before launch",
        }

    revisit = clause1.get("verdict") == "PASS" and clause2.get("verdict") == "PASS"
    out["rule"] = {
        "verbatim": "if arm (b) restores the three tools to within +/-30% of control AND keeps >=50% of "
        "arm (a)'s head saving -> REVISIT webu (file the design item). Otherwise webu's DON'T-BUILD STANDS.",
        "clause1_restoration": clause1,
        "clause2_head_saving": clause2,
        "VERDICT": "REVISIT" if revisit else "DON'T-BUILD STANDS",
        "power_disclosure_prereg_6a": "clause 1 passes with probability 0.353 even under PERFECT restoration "
        "at n=6 (200k bootstrap of webu's own control per-run aggregate [5,13,4,6,0,11,0,0,0,2]).",
    }

    # ------------------------------- secondary mechanism observable (PREREG 6b)
    ra = A["runs_with_any_of_three"]
    rb = B["runs_with_any_of_three"]
    na, nb = A["valid"], B["valid"]
    mech = "INDETERMINATE"
    if na and nb:
        if rb >= 4 and ra <= 1:
            mech = "REACH-RESTORED"
        elif rb <= 1 and ra <= 1:
            mech = "REACH-VANISHED"
    out["mechanism_secondary"] = {
        "rule": "REACH-RESTORED iff reach(any of three, b) >= 4/6 and reach(a) <= 1/6; "
        "REACH-VANISHED iff reach(b) <= 1/6 and reach(a) <= 1/6",
        "runs_with_any_of_three": {"a": f"{ra}/{na}", "b": f"{rb}/{nb}", "c": f"{C['runs_with_any_of_three']}/{C['valid']}"},
        "verdict": mech,
        "note": "NEVER overrides the rule; REVISIT is reached only through the rule in section 3.",
    }

    # ------------------------------------------------------------------ pins
    out["pins_on_wire"] = {
        "P3_tool_search_and_defer_present_in_a": any(
            r["tool_search_entry_on_wire"] and r["defer_loading_on_wire"] for r in arms["a"]
        ),
        "P3_tool_search_and_defer_present_in_b": any(
            r["tool_search_entry_on_wire"] and r["defer_loading_on_wire"] for r in arms["b"]
        ),
        "P4_namespace_roundtrip": any(r["namespace_roundtrip_on_wire"] for r in arms["a"] + arms["b"]),
        "c_control_provably_untreated": all(
            not r["tool_search_entry_on_wire"] and not r["defer_loading_on_wire"] for r in arms["c"]
        ),
        "missing_namespace_400s_total": sum(r["missing_namespace_400"] for r in runs),
        "namespaces_seen": sorted({n for r in runs for n in r["namespaces_on_wire"]}),
    }

    tot = sum(r["cost_usd"] or 0 for r in runs)
    out["spend"] = {
        "launches": len(runs),
        "total_usd": round(tot, 6),
        "per_launch_usd": round(tot / len(runs), 6) if runs else None,
        "authority_usd": 25.0,
        "remaining_usd": round(25.0 - tot, 6),
    }
    return out


# ------------------------------------------------------- instrument validation


def validate_instrument(webu_cap: Path) -> dict:
    """$0 check against webu's PUBLISHED table -- run BEFORE this lane spends."""
    expected = {
        "write_file": {"t0": (3, 12), "t1": (0, 0)},
        "edit_file": {"t0": (4, 24), "t1": (0, 0)},
        "delegate": {"t0": (4, 6), "t1": (0, 0)},
        "apply_patch": {"t0": (8, 41), "t1": (10, 58)},
    }
    got: dict = {}
    for arm in ("t0", "t1"):
        runs = sorted(p for p in (webu_cap / "runs").glob(f"{arm}-*") if p.is_dir())
        rt_tot: Counter = Counter()
        tp_tot: Counter = Counter()
        reach: Counter = Counter()
        for run in runs:
            rt = count_role_tool(run)
            tp = count_tool_pre(run, event_files(run))
            rt_tot += rt
            tp_tot += tp
            for k in rt:
                reach[k] += 1
        got[arm] = {
            t: {
                "reach": f"{reach[t]}/{len(runs)}",
                "role_tool": rt_tot[t],
                "tool_pre": tp_tot[t],
                "webu_published": expected[t][arm],
            }
            for t in expected
        }
    return {"source": str(webu_cap), "table": got}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--prereg-sha", default="")
    ap.add_argument("--validate-instrument", type=Path)
    a = ap.parse_args()
    if a.validate_instrument:
        res = validate_instrument(a.validate_instrument)
        print(json.dumps(res, indent=2))
        return
    if not a.cap:
        ap.error("--cap or --validate-instrument required")
    res = analyse(a.cap, a.prereg_sha)
    if a.json:
        a.json.write_text(json.dumps(res, indent=2))
    slim = {k: res[k] for k in ("per_arm", "per_tool", "rule", "mechanism_secondary", "pins_on_wire", "spend")}
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
