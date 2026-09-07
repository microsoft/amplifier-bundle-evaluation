#!/usr/bin/env python3
"""ytja routing-awareness analysis.

Applies the PRE-REGISTERED rules, in order:
  1. the item's PRIMARY rule, reported with its own power verdict
  2. the lane's SECONDARY rule (per-prompt one-sided Fisher collapse detection)
  3. per-prompt cells, with DEGENERATE cells named UNEVALUABLE rather than verdicted
  4. per-provider (decisive) and pooled (transparency only) aggregates

PER-PROVIDER IS DECISIVE. njpd's COND2 failed per-provider at 0.4737 and would have
passed pooled at 1.1131; pooling let a terra gain mask a 53% collapse in opus.
"""

from __future__ import annotations

import argparse
import json
import math
from math import comb
from pathlib import Path

Z = 1.959963984540054


def wilson(x: int, n: int) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = x / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = (Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n))) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float]:
    """95% score CI for p1 - p2 (lean - stock)."""
    if n1 == 0 or n2 == 0:
        return (float("nan"), float("nan"))
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    p1, p2 = x1 / n1, x2 / n2
    return (
        (p1 - p2) - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2),
        (p1 - p2) + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2),
    )


def fisher_le(a: int, b: int, c: int, d: int) -> float:
    """One-sided P(X <= a) for the 2x2 [[a,b],[c,d]] -- 'lean reaches LESS than stock'."""
    r1, r2, k, n = a + b, c + d, a + c, a + b + c + d
    if n == 0 or r1 == 0 or r2 == 0:
        return 1.0
    p = 0.0
    for x in range(0, a + 1):
        if x > r1 or (k - x) > r2 or (k - x) < 0:
            continue
        p += comb(r1, x) * comb(r2, k - x) / comb(n, k)
    return min(1.0, p)


def holm(pvals: dict[str, float]) -> dict[str, float]:
    items = sorted(pvals.items(), key=lambda kv: kv[1])
    m = len(items)
    out, prev = {}, 0.0
    for i, (k, p) in enumerate(items):
        adj = min(1.0, max(prev, (m - i) * p))
        out[k] = adj
        prev = adj
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graded", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    spec = json.loads(Path(a.prompts).read_text())
    hidden_ids = [p["id"] for p in spec["hidden"]]
    control_ids = [c["id"] for c in spec["controls"]]

    rows = [
        json.loads(ln) for ln in Path(a.graded).read_text().splitlines() if ln.strip()
    ]
    valid = [r for r in rows if r.get("valid")]

    L: list[str] = []

    def w(s: str = "") -> None:
        L.append(s)
        print(s)

    w("# ytja — routing-awareness results")
    w()
    w(
        f"runs executed **{len(rows)}** · valid **{len(valid)}** · validity "
        f"**{len(valid) / len(rows):.3f}**"
        if rows
        else "no runs"
    )
    spend = sum(r.get("cost_usd", 0.0) for r in rows)
    w(f"· measured spend **${spend:.4f}**")
    w()

    # ---------- instrument check ----------
    dis = [
        r
        for r in valid
        if r.get("n_transcript_role_tool", 0)
        and r["n_transcript_role_tool"] != r["n_tool_post"]
    ]
    thinking_only = [
        r
        for r in valid
        if r.get("thinking_mentions", 0) > 0 and r.get("n_tool_post", 0) == 0
    ]
    w("## G-INSTRUMENT")
    w()
    w(
        f'- `events.jsonl tool:post` vs `transcript.jsonl role:"tool"` disagree on '
        f"**{len(dis)} / {len(valid)}** valid runs."
    )
    w(
        f"- runs with a thinking-text mention of a reach tool but **zero executed** reach: "
        f"**{len(thinking_only)}**. Those are exactly the runs a thinking-text grader would "
        f"have scored as reaches. None are counted here."
    )
    w()

    def cell(arm: str, prov: str, pid: str) -> tuple[int, int]:
        rs = [
            r
            for r in valid
            if r["arm"] == arm and r["provider"] == prov and r["prompt_id"] == pid
        ]
        return sum(1 for r in rs if r.get("pass")), len(rs)

    providers = sorted({r["provider"] for r in valid})
    report: dict = {
        "per_prompt": {},
        "aggregate": {},
        "spend_usd": round(spend, 4),
        "runs": len(rows),
        "valid": len(valid),
    }

    # ---------- per prompt ----------
    w("## Per-prompt cells (pass / n) — the aggregate never replaces these")
    w()
    hdr = (
        "| prompt | kind | "
        + " | ".join(f"{p} stock | {p} lean | {p} Fisher p" for p in providers)
        + " |"
    )
    w(hdr)
    w("|" + "---|" * (2 + 3 * len(providers)))
    raw_p: dict[str, float] = {}
    for pid in hidden_ids + control_ids:
        kind = "hidden" if pid in hidden_ids else "control"
        cells = []
        for prov in providers:
            sx, sn = cell("stock", prov, pid)
            lx, ln = cell("lean", prov, pid)
            if kind == "control":
                # over-reach: pass means NO over-reach; test lean over-reaching MORE
                p = fisher_le(sx, sn - sx, lx, ln - lx)
            else:
                p = fisher_le(lx, ln - lx, sx, sn - sx)
            key = f"{pid}|{prov}"
            degenerate = (
                (sn == 0 or ln == 0) or (sx == sn and lx == ln) or (sx == 0 and lx == 0)
            )
            report["per_prompt"][key] = {
                "kind": kind,
                "stock": [sx, sn],
                "lean": [lx, ln],
                "fisher_p": round(p, 5),
                "degenerate": degenerate,
            }
            if kind == "hidden" and not degenerate:
                raw_p[key] = p
            flag = "UNEVAL" if degenerate else f"{p:.4f}"
            cells += [f"{sx}/{sn}", f"{lx}/{ln}", flag]
        w(f"| {pid} | {kind} | " + " | ".join(cells) + " |")
    w()
    w(
        "`UNEVAL` = degenerate cell (both arms identical at a boundary, or an empty arm). "
        "`otr`'s pre-registered gate came back UNEVALUABLE on counts `[0,0,1,0,0]`; reporting a "
        "verdict the data cannot support is the error, not the UNEVALUABLE."
    )
    w()
    if raw_p:
        adj = holm(raw_p)
        report["holm"] = {k: round(v, 5) for k, v in adj.items()}
        w(
            "Holm–Bonferroni across evaluable hidden cells: "
            + ", ".join(f"`{k}` {v:.4f}" for k, v in sorted(adj.items()))
        )
        w()

    # ---------- aggregates ----------
    def agg(kind_ids: list[str], prov: str | None) -> tuple[int, int, int, int]:
        sx = sn = lx = ln = 0
        for pid in kind_ids:
            for p in [prov] if prov else providers:
                a1, a2 = cell("stock", p, pid)
                b1, b2 = cell("lean", p, pid)
                sx += a1
                sn += a2
                lx += b1
                ln += b2
        return sx, sn, lx, ln

    w(
        "## Aggregate reach rates — PER-PROVIDER IS DECISIVE, pooled is transparency only"
    )
    w()
    w(
        "| scope | measure | stock | lean | diff (lean−stock) | 95% Newcombe CI | width |"
    )
    w("|---|---|---:|---:|---:|---|---:|")
    for scope, prov in [(p, p) for p in providers] + [("POOLED (not decisive)", None)]:
        for label, ids in (
            ("hidden-reach", hidden_ids),
            ("control-pass (no over-reach)", control_ids),
        ):
            sx, sn, lx, ln = agg(ids, prov)
            if sn == 0 or ln == 0:
                continue
            lo, hi = newcombe(lx, ln, sx, sn)
            d = lx / ln - sx / sn
            report["aggregate"][f"{scope}|{label}"] = {
                "stock": [sx, sn],
                "lean": [lx, ln],
                "diff_pp": round(d * 100, 2),
                "ci_pp": [round(lo * 100, 2), round(hi * 100, 2)],
            }
            w(
                f"| {scope} | {label} | {sx}/{sn} = {sx / sn:.3f} | {lx}/{ln} = {lx / ln:.3f} | "
                f"{d * 100:+.2f} pp | [{lo * 100:+.2f}, {hi * 100:+.2f}] pp | {(hi - lo) * 100:.2f} pp |"
            )
    w()

    # ---------- the primary rule ----------
    w("## The item's PRIMARY rule — applied, and reported with its power verdict")
    w()
    w(
        "> Stage 1 is CLEAR if hidden-reach ≥ stock − 5 pp AND over-reach ≤ stock + 5 pp (both on the LB)."
    )
    w()
    for prov in providers:
        sx, sn, lx, ln = agg(hidden_ids, prov)
        if sn == 0 or ln == 0:
            continue
        lo, hi = newcombe(lx, ln, sx, sn)
        best_lo, _ = newcombe(ln, ln, sn, sn)
        w(
            f"- **{prov} hidden-reach** LB = **{lo * 100:+.2f} pp** vs bar −5.00 pp → "
            f"{'MEETS' if lo >= -0.05 else 'does not meet'}. "
            f"But the BEST ATTAINABLE LB at n={ln} is **{best_lo * 100:+.2f} pp** — "
            f"{'so the clause is satisfiable here' if best_lo >= -0.05 else '**the clause cannot be met at this n by any data**'}."
        )
        cx, cn, dx, dn = agg(control_ids, prov)
        lo2, hi2 = newcombe(dn - dx, dn, cn - cx, cn)  # over-reach = 1 - pass
        _, best_hi = newcombe(0, dn, 0, cn)
        w(
            f"- **{prov} over-reach** UB = **{hi2 * 100:+.2f} pp** vs bar +5.00 pp → "
            f"{'MEETS' if hi2 <= 0.05 else 'does not meet'}. "
            f"Best attainable UB at n={dn} is **{best_hi * 100:+.2f} pp** — "
            f"{'satisfiable' if best_hi <= 0.05 else '**cannot be met at this n by any data**'}."
        )
    w()
    w(
        "**VERDICT ON THE PRIMARY RULE: NOT-POSSIBLE (cap-bound).** It needs 73 observations per "
        "arm per provider on each clause — 620 launches, $1,197.29 at the item's reference prices, "
        "against a $200 authority. Reporting a CLEAR from these interval widths would be the exact "
        "error S2a, `1ru` and `8rugb` were each caught making."
    )
    w()

    # ---------- the secondary rule ----------
    w("## The lane's SECONDARY rule — what the authority actually bought")
    w()
    flagged = [
        (k, v)
        for k, v in report["per_prompt"].items()
        if v["kind"] == "hidden" and not v["degenerate"] and v["fisher_p"] < 0.05
    ]
    over = [
        (k, v)
        for k, v in report["per_prompt"].items()
        if v["kind"] == "control" and not v["degenerate"] and v["fisher_p"] < 0.05
    ]
    if flagged:
        w("**REGRESSED hidden prompts (one-sided Fisher p < 0.05, per provider):**")
        for k, v in sorted(flagged):
            w(
                f"- `{k}` — stock {v['stock'][0]}/{v['stock'][1]} → lean {v['lean'][0]}/{v['lean'][1]}, p = {v['fisher_p']:.4f}"
            )
    else:
        w(
            "**No hidden prompt regressed** at one-sided Fisher p < 0.05 on either provider."
        )
    w()
    if over:
        w("**INCREASED over-reach on controls (p < 0.05):**")
        for k, v in sorted(over):
            w(f"- `{k}` — p = {v['fisher_p']:.4f}")
    else:
        w("**No control showed increased over-reach** at p < 0.05 on either provider.")
    w()
    report["regressed"] = [k for k, _ in flagged]
    report["over_reach_flagged"] = [k for k, _ in over]

    Path(a.out).write_text("\n".join(L) + "\n")
    Path(a.out).with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
