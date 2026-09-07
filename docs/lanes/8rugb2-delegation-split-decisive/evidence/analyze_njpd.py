#!/usr/bin/env python3
"""njpd -- apply the FROZEN rule verbatim, exactly as PREREGISTRATION.md fixes it.

  SHIP iff success LB >= -5 pp AND delegation count within +/-30% of main.

Pre-registered operationalisation (PREREGISTRATION.md, committed 68b3b68 BEFORE run 1):
  success        = the S3 grader's own `pass` field
  success LB     = Newcombe/Wilson lower bound on p(B) - p(A), pp, Z=1.959963985
  delegation     = dw_measure root_delegate_calls (delegate:agent_spawned, root session)
  COND 1         = POOLED across providers   (per-provider n makes it unsatisfiable)
  COND 2         = PER-PROVIDER, both must pass; ratio mean(B)/mean(A) in [0.70,1.30]
  ties           = >= -5.00 passes; band inclusive; evaluated on UNROUNDED floats
  strata         = njpd (this lane) + 8rugb prior stratum (identical harness/SHAs);
                   reported pooled AND njpd-only
  fan-out width  = SECONDARY, reported, never gating
"""
import json, math, statistics, sys, importlib.util
from pathlib import Path

NJPD = Path("/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-njpd")
PRIOR = Path("/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-8rugb")
Z = 1.959963985
BAND_LO, BAND_HI, LB_FLOOR = 0.70, 1.30, -5.0

_spec = importlib.util.spec_from_file_location("fanout", NJPD / "fanout.py")
_fan = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_fan)


def wilson(x, n):
    if n == 0: return (0.0, 1.0)
    p = x / n; d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def newcombe_diff(x1, n1, x2, n2):
    """CI for p1 - p2  (arm B minus arm A)."""
    p1 = x1 / n1 if n1 else 0.0
    p2 = x2 / n2 if n2 else 0.0
    l1, u1 = wilson(x1, n1); l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)


def fan_for(rundir: Path, root_sid: str):
    f = rundir / "fanout.json"
    if f.exists():
        try: return json.loads(f.read_text())
        except Exception: pass
    if not root_sid: return None
    path = _fan.root_events_path(str(rundir / "all-sessions"), root_sid)
    if not path: return None
    turn = 0; per_turn = {}; spawn_ts = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"delegate:agent_spawned"' not in line and '"prompt:complete"' not in line: continue
            try: e = json.loads(line)
            except Exception: continue
            if e.get("event") == "delegate:agent_spawned":
                per_turn[turn] = per_turn.get(turn, 0) + 1
                t = _fan.parse_ts(e.get("ts"))
                if t: spawn_ts.append(t)
            elif e.get("event") == "prompt:complete":
                turn += 1
    widths = [per_turn[k] for k in sorted(per_turn) if per_turn[k] > 0]
    spawn_ts.sort(); bursts = []
    for t in spawn_ts:
        if bursts and (t - bursts[-1][-1]).total_seconds() <= _fan.BURST_GAP_S: bursts[-1].append(t)
        else: bursts.append([t])
    return {"measurable": True, "fanout_per_turn": widths, "fanout_burst": [len(b) for b in bursts],
            "delegating_turns": len(widths), "spawns_total": sum(widths)}


def load(root: Path, stratum: str):
    out = []
    for p in sorted((root / "runs").glob("*/summary.json")):
        try: r = json.loads(p.read_text())
        except Exception: continue
        r["stratum"] = stratum
        r["_fan"] = fan_for(p.parent, r.get("root_sid") or "")
        out.append(r)
    return out


def cond2(A, B):
    da = [r["delegate_calls"] or 0 for r in A]
    db = [r["delegate_calls"] or 0 for r in B]
    ma = statistics.mean(da) if da else 0.0
    mb = statistics.mean(db) if db else 0.0
    med_a = statistics.median(da) if da else 0
    nonzero_a = sum(1 for v in da if v >= 1)
    degenerate = (med_a == 0) or (nonzero_a < 2)
    ratio = (mb / ma) if ma else None
    return {"delegation_mean_A": round(ma, 4), "delegation_mean_B": round(mb, 4),
            "delegation_median_A": med_a, "arm_A_runs_with_delegation": f"{nonzero_a}/{len(da)}",
            "delegation_ratio_B_over_A": round(ratio, 4) if ratio is not None else None,
            "ratio_unrounded": ratio,
            "cond2_within_30pct": (ratio is not None) and (BAND_LO <= ratio <= BAND_HI),
            "UNEVALUABLE": degenerate,
            "delegation_A_per_run": da, "delegation_B_per_run": db}


def fanstats(runs):
    pt = [w for r in runs if r.get("_fan") for w in r["_fan"].get("fanout_per_turn", [])]
    bt = [w for r in runs if r.get("_fan") for w in r["_fan"].get("fanout_burst", [])]
    dt = [r["_fan"]["delegating_turns"] for r in runs if r.get("_fan")]
    f = lambda v: {"n": len(v), "mean": round(statistics.mean(v), 3) if v else None,
                   "median": statistics.median(v) if v else None, "max": max(v) if v else None,
                   "dist": dict(sorted({x: v.count(x) for x in set(v)}.items()))}
    return {"fanout_per_turn": f(pt), "fanout_burst": f(bt),
            "delegating_turns_per_run": f(dt)}


def analyse(runs, label):
    valid = [r for r in runs if r["valid"]]
    rep = {"label": label, "runs_launched": len(runs), "runs_valid": len(valid),
           "validity_rate": round(len(valid) / len(runs), 4) if runs else None,
           "n_A": sum(1 for r in valid if r["arm"] == "A"),
           "n_B": sum(1 for r in valid if r["arm"] == "B")}
    A = [r for r in valid if r["arm"] == "A"]; B = [r for r in valid if r["arm"] == "B"]
    xa, na = sum(1 for r in A if r["pass"]), len(A)
    xb, nb = sum(1 for r in B if r["pass"]), len(B)
    d, lo, hi = newcombe_diff(xb, nb, xa, na)
    rep["COND1_pooled_GATING"] = {
        "success_A": f"{xa}/{na}", "success_B": f"{xb}/{nb}",
        "rate_A": round(xa / na, 4) if na else None, "rate_B": round(xb / nb, 4) if nb else None,
        "diff_pp": round(d * 100, 2), "LB_pp": round(lo * 100, 2), "UB_pp": round(hi * 100, 2),
        "LB_pp_unrounded": lo * 100, "PASS": (lo * 100) >= LB_FLOOR,
        "best_attainable_LB_pp_at_this_n": round(-(1 - wilson(min(na, nb), min(na, nb))[0]) * 100, 2) if min(na, nb) else None,
    }
    provs = sorted({r["provider"] for r in valid})
    rep["COND2_per_provider_GATING"] = {}
    rep["per_provider_diagnostics"] = {}
    for p in provs:
        Ap = [r for r in A if r["provider"] == p]; Bp = [r for r in B if r["provider"] == p]
        rep["COND2_per_provider_GATING"][p] = cond2(Ap, Bp) | {"n_A": len(Ap), "n_B": len(Bp)}
        xap, nap = sum(1 for r in Ap if r["pass"]), len(Ap)
        xbp, nbp = sum(1 for r in Bp if r["pass"]), len(Bp)
        dp, lop, hip = newcombe_diff(xbp, nbp, xap, nap)
        nmin = min(nap, nbp)
        rep["per_provider_diagnostics"][p] = {
            "NOTE": "NON-GATING by pre-registration: per-provider n cannot satisfy a -5pp floor",
            "success_A": f"{xap}/{nap}", "success_B": f"{xbp}/{nbp}",
            "diff_pp": round(dp * 100, 2), "LB_pp": round(lop * 100, 2), "UB_pp": round(hip * 100, 2),
            "best_attainable_LB_pp_at_this_n": round(-(1 - wilson(nmin, nmin)[0]) * 100, 2) if nmin else None,
            "cost_mean_A": round(statistics.mean([r["cost_usd"] or 0 for r in Ap]), 4) if Ap else None,
            "cost_mean_B": round(statistics.mean([r["cost_usd"] or 0 for r in Bp]), 4) if Bp else None,
            "score_mean_A": round(statistics.mean([r["score_total"] or 0 for r in Ap]), 2) if Ap else None,
            "score_mean_B": round(statistics.mean([r["score_total"] or 0 for r in Bp]), 2) if Bp else None,
            "FANOUT_SECONDARY_A": fanstats(Ap), "FANOUT_SECONDARY_B": fanstats(Bp),
        }
    pooled2 = cond2(A, B)
    pooled2["NOTE"] = ("DISCLOSED, NON-GATING. Pre-registration fixed condition 2 as PER-PROVIDER. "
                       "Shown so the consequence of that choice is visible.")
    rep["COND2_pooled_DISCLOSED_NON_GATING"] = pooled2
    unevaluable = any(rep["COND2_per_provider_GATING"][p]["UNEVALUABLE"] for p in provs)
    c1 = rep["COND1_pooled_GATING"]["PASS"]
    c2 = bool(provs) and all(rep["COND2_per_provider_GATING"][p]["cond2_within_30pct"] for p in provs)
    rep["VERDICT"] = "UNEVALUABLE" if unevaluable else ("SHIP" if (c1 and c2) else "NO-SHIP")
    fails = []
    if not c1: fails.append(f"COND1 pooled success LB = {rep['COND1_pooled_GATING']['LB_pp']} pp (floor -5.00)")
    for p in provs:
        g = rep["COND2_per_provider_GATING"][p]
        if not g["cond2_within_30pct"]:
            fails.append(f"COND2 {p} delegation ratio = {g['delegation_ratio_B_over_A']} (band 0.70-1.30)")
    rep["DECIDING_NUMBERS"] = fails or ["all gating conditions passed"]
    rep["target_n_per_arm"] = 73
    rep["target_met"] = (rep["n_A"] >= 73 and rep["n_B"] >= 73)
    return rep


def main():
    njpd = load(NJPD, "njpd")
    prior = load(PRIOR, "8rugb")
    spend = round(sum(r.get("cost_usd") or 0 for r in njpd), 4)
    report = {
        "prereg_sha": "68b3b68e7a28ba02d404675cf2d624bcb751a020",
        "rule": "SHIP iff success LB >= -5 pp AND delegation count within +/-30% of main",
        "arms": {"A": "amplifier-foundation@a0decc61f41ed78a92db6d5b70a71e15722a5624 (merge-base)",
                 "B": "amplifier-foundation@3d676d68d0e45620330c24ae0142de86efa39234 (PR #369 split)"},
        "njpd_measured_spend_usd": spend,
        "njpd_launches": len(njpd),
        "njpd_valid": sum(1 for r in njpd if r["valid"]),
        "njpd_validity_rate": round(sum(1 for r in njpd if r["valid"]) / len(njpd), 4) if njpd else None,
        "PRIMARY_pooled_strata": analyse(njpd + prior, "njpd + 8rugb prior stratum"),
        "SECONDARY_njpd_only": analyse(njpd, "njpd only"),
        "runs": [{k: r.get(k) for k in ("run", "stratum", "arm", "provider", "valid", "invalid_reasons",
                                        "score_total", "pass", "delegate_calls", "cost_usd", "wall_s")}
                 | {"fanout_per_turn": (r.get("_fan") or {}).get("fanout_per_turn"),
                    "fanout_burst": (r.get("_fan") or {}).get("fanout_burst")}
                 for r in (njpd + prior)],
    }
    (NJPD / "ANALYSIS.json").write_text(json.dumps(report, indent=2))
    slim = {k: report[k] for k in ("prereg_sha", "njpd_measured_spend_usd", "njpd_launches",
                                   "njpd_valid", "njpd_validity_rate")}
    slim["PRIMARY"] = {k: report["PRIMARY_pooled_strata"][k] for k in
                       ("runs_valid", "n_A", "n_B", "target_met", "COND1_pooled_GATING",
                        "COND2_per_provider_GATING", "VERDICT", "DECIDING_NUMBERS")}
    print(json.dumps(slim, indent=2))


if __name__ == "__main__":
    main()
