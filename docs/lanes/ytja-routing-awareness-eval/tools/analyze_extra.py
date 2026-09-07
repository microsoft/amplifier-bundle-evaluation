#!/usr/bin/env python3
"""Secondary analyses: what the model reached FOR (not just whether it passed),
failure-mode split, discovery-tool shift, and cost/wall by arm. Reproducible at $0
from graded.jsonl."""

import json
import random
import sys
import collections
import statistics as st
from math import comb


def fisher2(a, b, c, d):
    r1, r2, k, n = a + b, c + d, a + c, a + b + c + d
    if 0 in (n, r1, r2, k, n - k):
        return 1.0

    def pr(x):
        return comb(r1, x) * comb(r2, k - x) / comb(n, k)

    p0 = pr(a)
    return min(
        1.0,
        sum(
            pr(x) for x in range(max(0, k - r2), min(r1, k) + 1) if pr(x) <= p0 + 1e-12
        ),
    )


graded, out = sys.argv[1], sys.argv[2]
rows = [json.loads(ln) for ln in open(graded)]
random.seed(20260907)
L = []


def w(s=""):
    L.append(s)
    print(s)


w("## What the model reached FOR — the pass/fail metric hides this")
w()
w("First EXECUTED tool of the run, all 15 prompts, n=120 per arm per provider:")
w()
for prov in ("terra", "opus"):
    d = {
        arm: collections.Counter(
            (r["tool_seq"] or ["<none>"])[0]
            for r in rows
            if r["provider"] == prov and r["arm"] == arm
        )
        for arm in ("stock", "lean")
    }
    N, M = sum(d["stock"].values()), sum(d["lean"].values())
    w(f"**{prov}**")
    w()
    w("| first tool | stock | lean | Fisher p (2-sided) |")
    w("|---|---:|---:|---:|")
    for k in sorted(set(d["stock"]) | set(d["lean"])):
        a, c = d["stock"][k], d["lean"][k]
        w(f"| `{k}` | {a} | {c} | {fisher2(a, N - a, c, M - c):.5f} |")
    w()

w("### The discovery-tool shift — the real behavioural effect of the lean head")
w()
w("| provider | tool | stock | lean | Fisher p |")
w("|---|---|---:|---:|---:|")
for prov in ("terra", "opus"):
    for tool in ("mode", "recipes"):
        a = sum(
            1
            for r in rows
            if r["provider"] == prov and r["arm"] == "stock" and tool in r["tool_seq"]
        )
        c = sum(
            1
            for r in rows
            if r["provider"] == prov and r["arm"] == "lean" and tool in r["tool_seq"]
        )
        n = sum(1 for r in rows if r["provider"] == prov and r["arm"] == "stock")
        m = sum(1 for r in rows if r["provider"] == prov and r["arm"] == "lean")
        w(
            f"| {prov} | `{tool}` anywhere in run | {a}/{n} | {c}/{m} | {fisher2(a, n - a, c, m - c):.6f} |"
        )
ids = {"H1", "H6", "H7", "H8", "H9"}
w()
w(
    "First CAPABILITY REACH on terra, pooled over the five prompts where stock's first reach "
    "was `per-repo-conventions` (n=40 per arm):"
)
w()
w("| first reach | stock | lean | Fisher p |")
w("|---|---:|---:|---:|")
for tgt in ("load_skill:per-repo-conventions", "mode:list", "load_skill:<list>"):
    a = sum(
        1
        for r in rows
        if r["provider"] == "terra"
        and r["arm"] == "stock"
        and r["prompt_id"] in ids
        and r.get("first_reach") == tgt
    )
    c = sum(
        1
        for r in rows
        if r["provider"] == "terra"
        and r["arm"] == "lean"
        and r["prompt_id"] in ids
        and r.get("first_reach") == tgt
    )
    w(f"| `{tgt}` | {a}/40 | {c}/40 | {fisher2(a, 40 - a, c, 40 - c):.6f} |")
w()

w(
    "### Failure-mode split on hidden prompts — no reach at all vs reached the wrong thing"
)
w()
w("| provider | arm | any capability reach | `delegate` used | `load_skill` used |")
w("|---|---|---:|---:|---:|")
for prov in ("opus", "terra"):
    for arm in ("stock", "lean"):
        rs = [
            r
            for r in rows
            if r["provider"] == prov and r["arm"] == arm and r["kind"] == "hidden"
        ]
        anyr = sum(
            1
            for r in rs
            if any(t in ("delegate", "load_skill", "mode") for t in r["tool_seq"])
        )
        w(
            f"| {prov} | {arm} | {anyr}/{len(rs)} | "
            f"{sum(1 for r in rs if 'delegate' in r['tool_seq'])} | "
            f"{sum(1 for r in rs if 'load_skill' in r['tool_seq'])} |"
        )
w()

w("### Cost and wall by arm — paired by prompt, 20,000-sample bootstrap")
w()
w(
    "| provider | stock $/run | lean $/run | delta | 95% CI on the paired mean delta | verdict |"
)
w("|---|---:|---:|---:|---|---|")
pids = sorted({r["prompt_id"] for r in rows}, key=lambda s: (s[0], int(s[1:])))
for prov in ("terra", "opus"):
    per = []
    for pid in pids:
        s = [
            r["cost_usd"]
            for r in rows
            if r["provider"] == prov and r["arm"] == "stock" and r["prompt_id"] == pid
        ]
        lv = [
            r["cost_usd"]
            for r in rows
            if r["provider"] == prov and r["arm"] == "lean" and r["prompt_id"] == pid
        ]
        per.append((st.mean(lv) - st.mean(s), st.mean(s), st.mean(lv)))
    boots = sorted(
        sum(random.choice(per)[0] for _ in per) / len(per) for _ in range(20000)
    )
    lo, hi = boots[500], boots[19499]
    ts, tl = sum(p[1] for p in per) / len(per), sum(p[2] for p in per) / len(per)
    sig = "**NOT significant** (CI spans 0)" if lo <= 0 <= hi else "significant"
    w(
        f"| {prov} | ${ts:.4f} | ${tl:.4f} | {100 * (tl - ts) / ts:+.1f}% | "
        f"[{lo:+.4f}, {hi:+.4f}] USD | {sig} |"
    )
w()
for prov in ("terra", "opus"):
    s = [r["wall_s"] for r in rows if r["provider"] == prov and r["arm"] == "stock"]
    lv = [r["wall_s"] for r in rows if r["provider"] == prov and r["arm"] == "lean"]
    w(
        f"- {prov} wall: stock {st.mean(s):.1f}s -> lean {st.mean(lv):.1f}s ({100 * (st.mean(lv) - st.mean(s)) / st.mean(s):+.1f}%)"
    )
w()
open(out, "w").write("\n".join(L) + "\n")
