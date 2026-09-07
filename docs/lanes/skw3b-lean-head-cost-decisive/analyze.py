#!/usr/bin/env python3
"""g7h3 — analysis of the opus-5/S7-17 lean-head Delta-total A/B.

Implements PREREGISTRATION.md section 7 exactly and nothing else:

  primary       Welch's unequal-variance t on $/run, VALID runs only, 95% CI,
                reported in dollars and as a percentage of the STOCK mean,
                with the achieved MDE printed beside every verdict so a HOLD
                is always labelled `measured wash` or `underpowered`.
  secondary 1   ALL-runs sensitivity (VALID + invalid).
  secondary 2   block-paired estimator (immune to a monotone time trend).
  secondary 3   B = Delta_total - D, with D = -$0.762/run taken from skw3 3.4
                (measured on the wire, 8 significant figures, not re-estimated).
  secondary 4   B via the request-count channel, reported as a PROXY and NOT
                converted to dollars.
  secondary 5   cold starts and boundary counts per arm.

Reads only committed capture files. No API call, no network, $0.
"""

from __future__ import annotations

import json
import math
import pathlib
import statistics
import sys

CAP = pathlib.Path(
    sys.argv[1]
    if len(sys.argv) > 1
    else "/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/"
    "treatment-validation/20260906-g7h3-lean-head-decisive"
)

# skw3 FINDINGS 3.4 -- measured on the wire, not re-estimated here.
D_OPUS5_S7 = -0.762
# skw3 5.1 -- the largest behavioural term ever observed anywhere in the program.
B_MAX_OBSERVED_PCT = 12.6
Z975, Z80 = 1.959964, 0.841621
K = (Z975 + Z80) ** 2  # 7.8489


def t_crit(df: float) -> float:
    """Two-sided 95% t critical value. Bisection on the Student-t CDF."""
    if df <= 0:
        return float("nan")

    def cdf(t: float) -> float:
        x = df / (df + t * t)
        return 1.0 - 0.5 * betainc(df / 2.0, 0.5, x) if t > 0 else 0.5 * betainc(df / 2.0, 0.5, x)

    lo, hi = 0.0, 100.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if cdf(mid) < 0.975:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta, continued fraction (Lentz)."""
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m, tiny = i // 2, 1e-30
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = tiny if abs(d) < tiny else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = tiny if abs(c) < tiny else c
        f *= c * d
        if abs(1.0 - c * d) < 1e-12:
            break
    val = front * (f - 1.0)
    return val if a > 1 or True else val


def load() -> list[dict]:
    runs = []
    for d in sorted(CAP.glob("g7h3-*")):
        if not d.is_dir():
            continue
        rec = d / "driver_record.json"
        if not rec.exists():
            continue
        r = json.loads(rec.read_text())
        sc = r.get("scorecard") or {}
        name = d.name
        arm = "stock" if name.startswith("g7h3-s-") else "v1"
        block = int(name.split("-b")[1].split("-")[0])
        hl = CAP / f"{name}.headlog.jsonl"
        reqs, hvar, ichars, tchars = None, None, None, None
        if hl.exists() and hl.stat().st_size:
            lines = [ln for ln in hl.read_text().splitlines() if ln.strip()]
            reqs = len(lines)
            try:
                j0 = json.loads(lines[0])
                hvar, ichars, tchars = j0.get("variant"), j0.get("instr_chars"), j0.get("tools_chars")
            except Exception:
                pass
        runs.append(
            {
                "name": name,
                "arm": arm,
                "block": block,
                "cost": float(r.get("session_cost_usd_last") or 0.0),
                "wall_s": r.get("wall_s"),
                "boundaries": r.get("final_boundaries"),
                "valid": bool(sc.get("valid")),
                "survival": sc.get("overall_survival"),
                "requests": reqs,
                "headlog_variant": hvar,
                "instr_chars": ichars,
                "tools_chars": tchars,
            }
        )
    return runs


def welch(a: list[float], b: list[float]) -> dict:
    """a = stock, b = v1. delta = mean(v1) - mean(stock); negative = V1 saves."""
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return {"n_stock": na, "n_v1": nb, "insufficient": True}
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    tc = t_crit(df)
    delta = mb - ma
    lo, hi = delta - tc * se, delta + tc * se
    sd_pooled = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    n_harm = 2 / (1 / na + 1 / nb)
    mde = math.sqrt(2 * sd_pooled**2 * K / n_harm)
    return {
        "n_stock": na,
        "n_v1": nb,
        "mean_stock": ma,
        "mean_v1": mb,
        "sd_stock": math.sqrt(va),
        "sd_v1": math.sqrt(vb),
        "sd_pooled": sd_pooled,
        "cv_stock": math.sqrt(va) / ma if ma else None,
        "delta": delta,
        "delta_pct": 100 * delta / ma if ma else None,
        "ci_lo": lo,
        "ci_hi": hi,
        "ci_lo_pct": 100 * lo / ma if ma else None,
        "ci_hi_pct": 100 * hi / ma if ma else None,
        "welch_t": delta / se if se else None,
        "df": df,
        "tcrit": tc,
        "ci_excludes_zero": (lo > 0) or (hi < 0),
        "n_harmonic": n_harm,
        "mde_usd": mde,
        "mde_pct": 100 * mde / ma if ma else None,
        "n_needed_5pct": 2 * sd_pooled**2 * K / (0.05 * ma) ** 2 if ma else None,
    }


def verdict(res: dict) -> str:
    """PREREGISTRATION.md section 1, applied verbatim. Cost primary only."""
    if res.get("insufficient"):
        return "NOT-EVALUABLE (n<2 in an arm)"
    p, excl = res["delta_pct"], res["ci_excludes_zero"]
    if p <= -5.0 and excl:
        return "SHIP (cost primary) -- quality co-primary must also clear"
    if p >= 5.0 and excl:
        return "REJECT"
    if -5.0 < p < 5.0:
        return "HOLD (point estimate inside +/-5%)"
    return "HOLD (point outside +/-5% but CI includes zero -- pre-registered gap rule)"


def main() -> int:
    runs = load()
    out: dict = {"n_runs": len(runs), "runs": runs}
    if not runs:
        print(json.dumps(out, indent=2))
        return 0

    v = [r for r in runs if r["valid"]]
    prim = welch([r["cost"] for r in v if r["arm"] == "stock"], [r["cost"] for r in v if r["arm"] == "v1"])
    allr = welch(
        [r["cost"] for r in runs if r["arm"] == "stock"], [r["cost"] for r in runs if r["arm"] == "v1"]
    )
    out["primary_VALID_only"] = prim
    out["primary_verdict"] = verdict(prim)
    out["sensitivity_ALL_runs"] = allr
    out["sensitivity_ALL_verdict"] = verdict(allr)

    # block-paired: each stock block matched to the nearest v1 block by index
    sb = {}
    for r in v:
        sb.setdefault((r["arm"], r["block"]), []).append(r["cost"])
    s_blocks = sorted(b for (a, b) in sb if a == "stock")
    v_blocks = sorted(b for (a, b) in sb if a == "v1")
    pairs = []
    for i in range(min(len(s_blocks), len(v_blocks))):
        pairs.append(
            statistics.mean(sb[("v1", v_blocks[i])]) - statistics.mean(sb[("stock", s_blocks[i])])
        )
    if len(pairs) >= 2:
        m, sd = statistics.mean(pairs), statistics.stdev(pairs)
        se = sd / math.sqrt(len(pairs))
        tc = t_crit(len(pairs) - 1)
        base = statistics.mean([r["cost"] for r in v if r["arm"] == "stock"])
        out["secondary_block_paired"] = {
            "n_pairs": len(pairs),
            "delta": m,
            "delta_pct": 100 * m / base,
            "ci_lo_pct": 100 * (m - tc * se) / base,
            "ci_hi_pct": 100 * (m + tc * se) / base,
            "ci_excludes_zero": (m - tc * se > 0) or (m + tc * se < 0),
        }

    # B = Delta_total - D  (D measured on the wire by skw3, not re-estimated)
    if not prim.get("insufficient"):
        b_usd = prim["delta"] - D_OPUS5_S7
        out["secondary_B_by_subtraction"] = {
            "D_usd_per_run_from_skw3": D_OPUS5_S7,
            "delta_total_usd": prim["delta"],
            "B_usd": b_usd,
            "B_pct_of_stock_mean": 100 * b_usd / prim["mean_stock"],
            "B_max_ever_observed_pct": B_MAX_OBSERVED_PCT,
            "B_exceeds_program_max": 100 * b_usd / prim["mean_stock"] > B_MAX_OBSERVED_PCT,
        }

    rs = [r["requests"] for r in v if r["arm"] == "stock" and r["requests"]]
    rv = [r["requests"] for r in v if r["arm"] == "v1" and r["requests"]]
    if len(rs) >= 2 and len(rv) >= 2:
        out["secondary_B_request_proxy"] = welch([float(x) for x in rs], [float(x) for x in rv])
        out["secondary_B_request_proxy"]["NOTE"] = (
            "PROXY. Deliberately NOT converted to dollars -- that conversion is the "
            "weakness skw3 section 5 named."
        )

    out["validity"] = {
        a: {
            "n_launched": sum(1 for r in runs if r["arm"] == a),
            "n_valid": sum(1 for r in runs if r["arm"] == a and r["valid"]),
            "rate": (
                sum(1 for r in runs if r["arm"] == a and r["valid"]) / max(1, sum(1 for r in runs if r["arm"] == a))
            ),
            "mean_boundaries": (
                statistics.mean([r["boundaries"] for r in runs if r["arm"] == a and r["boundaries"] is not None])
                if any(r["arm"] == a for r in runs)
                else None
            ),
        }
        for a in ("stock", "v1")
    }
    out["quality_within_lane"] = {
        a: {
            "n": len([r["survival"] for r in v if r["arm"] == a and r["survival"] is not None]),
            "mean_survival": (
                statistics.mean([r["survival"] for r in v if r["arm"] == a and r["survival"] is not None])
                if [r for r in v if r["arm"] == a and r["survival"] is not None]
                else None
            ),
        }
        for a in ("stock", "v1")
    }
    out["quality_NOTE"] = (
        "Within-lane consistency check ONLY. The co-primary quality gate is CITED from "
        "5zp (one-sided 95% LB -7.15 pp vs the frozen -10 pp margin), not re-derived here."
    )
    out["spend_usd_total_including_void"] = round(
        sum(r["cost"] for r in runs)
        + sum(
            json.loads((d / "driver_record.json").read_text()).get("session_cost_usd_last") or 0
            for d in CAP.glob("VOID-*")
            if (d / "driver_record.json").exists()
        ),
        4,
    )
    print(json.dumps(out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
