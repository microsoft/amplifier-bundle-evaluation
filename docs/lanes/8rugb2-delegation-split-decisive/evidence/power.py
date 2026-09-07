#!/usr/bin/env python3
"""What n does the FROZEN condition 1 actually require -- at the OBSERVED success rate?

8rugb's power calc used  best-case LB = -(1 - wilson_lower(n, n)),  which is the LB
attained ONLY when BOTH arms score 100%. It gives n=73 -> -5.00 pp. S3 does not
produce 100% success in either arm. This recomputes the required n at the success
rate actually measured, holding the arms EQUAL (the most favourable real case:
a true difference of exactly zero).
"""
import json, glob, math, statistics, sys
Z = 1.959963985

def wilson(x, n):
    if n == 0: return (0.0, 1.0)
    p = x / n; d = 1 + Z*Z/n
    c = (p + Z*Z/(2*n)) / d
    h = Z*math.sqrt(p*(1-p)/n + Z*Z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))

def newcombe_lo(x1, n1, x2, n2):
    p1, p2 = x1/n1, x2/n2
    l1, u1 = wilson(x1, n1); l2, u2 = wilson(x2, n2)
    return (p1 - p2) - math.sqrt((p1-l1)**2 + (u2-p2)**2)

def lb_at(n, p):
    """LB in pp for two equal arms of size n each at success rate p."""
    x = round(p * n)
    return newcombe_lo(x, n, x, n) * 100

def required_n(p, floor=-5.0, hi=20000):
    lo, hi_ = 2, hi
    if lb_at(hi_, p) < floor: return None
    while lo < hi_:
        mid = (lo + hi_) // 2
        if lb_at(mid, p) >= floor: hi_ = mid
        else: lo = mid + 1
    return lo

def main(cap):
    runs = [json.loads(open(p).read()) for p in glob.glob(cap + "/runs/*/summary.json")]
    prior = [json.loads(open(p).read()) for p in
             glob.glob("/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-8rugb/runs/*/summary.json")]
    v = [r for r in runs if r["valid"]]
    allv = v + [r for r in prior if r["valid"]]
    spent = sum(r.get("cost_usd") or 0 for r in runs)
    A = [r for r in allv if r["arm"] == "A"]; B = [r for r in allv if r["arm"] == "B"]
    xa, na = sum(1 for r in A if r["pass"]), len(A)
    xb, nb = sum(1 for r in B if r["pass"]), len(B)
    p_pool = (xa + xb) / (na + nb) if (na + nb) else 0
    po = statistics.mean([r["cost_usd"] for r in v if r["provider"] == "opus"]) if v else 0
    pt = statistics.mean([r["cost_usd"] for r in v if r["provider"] == "terra"]) if v else 0
    blend = (po + pt) / 2
    out = {
        "observed": {"success_A": f"{xa}/{na}", "success_B": f"{xb}/{nb}",
                     "rate_A": round(xa/na, 4) if na else None,
                     "rate_B": round(xb/nb, 4) if nb else None,
                     "rate_pooled": round(p_pool, 4)},
        "LB_pp_now": round(newcombe_lo(xb, nb, xa, na) * 100, 2) if na and nb else None,
        "8rugb_power_calc_assumption": {
            "formula": "best-case LB = -(1 - wilson_lower(n,n)) -- attained ONLY at 100% success in BOTH arms",
            "n_73_best_case_LB_pp": round(lb_at(73, 1.0), 2),
            "n_73_LB_pp_at_OBSERVED_rate": round(lb_at(73, p_pool), 2),
        },
        "required_n_per_arm_for_LB_ge_-5pp": {
            "at_success_rate_1.00_(8rugb's assumption)": required_n(1.0),
            "at_success_rate_0.857_(8rugb's own observed 6/7)": required_n(6/7),
            "at_success_rate_%.4f_(measured here)" % p_pool: required_n(p_pool),
        },
        "cost_of_required_n": {},
        "measured_price_per_launch": {"opus": round(po, 4), "terra": round(pt, 4), "blended_50_50": round(blend, 4)},
        "njpd_spend_so_far": round(spent, 4),
    }
    for k, n in out["required_n_per_arm_for_LB_ge_-5pp"].items():
        out["cost_of_required_n"][k] = (f"n={n}/arm -> {2*n} runs x ${blend:.4f} = ${2*n*blend:,.2f}"
                                        if n else "unreachable")
    print(json.dumps(out, indent=2))

main(sys.argv[1] if len(sys.argv) > 1 else ".")
