#!/usr/bin/env python3
"""PREREG 6a/6b -- power of the +/-30% clause and of the reach observable, at n=6.
Inputs are webu's PUBLISHED per-run figures only. Spends nothing. Run BEFORE launch."""
import random, statistics
from math import comb, exp, factorial

CTRL_AGG = [5, 13, 4, 6, 0, 11, 0, 0, 0, 2]   # webu t0 per-run write_file+edit_file+delegate
RATES = {"write_file": 1.2, "edit_file": 2.4, "delegate": 0.6, "apply_patch": 4.1}  # webu t0 calls/run

def poisson_inside(lam, band=0.30):
    lo, hi = (1 - band) * lam, (1 + band) * lam
    return sum(exp(-lam) * lam ** k / factorial(k) for k in range(0, 400) if lo <= k <= hi)

def bootstrap_clause1(n=6, band=0.30, trials=200_000, seed=20260906):
    random.seed(seed)
    inside = 0
    for _ in range(trials):
        b = statistics.mean(random.choice(CTRL_AGG) for _ in range(n))
        c = statistics.mean(random.choice(CTRL_AGG) for _ in range(n))
        if c > 0 and abs(b / c - 1) <= band:
            inside += 1
    return inside / trials

def fisher(a, b, c, d):
    n = a + b + c + d
    obs = comb(a + b, a) * comb(c + d, c)
    tot = 0
    for x in range(a + b + 1):
        y = a + c - x
        if 0 <= y <= c + d:
            v = comb(a + b, x) * comb(c + d, y)
            if v <= obs:
                tot += v
    return tot / comb(n, a + c)

if __name__ == "__main__":
    print("PER-TOOL Poisson P(inside +/-30% | perfect restoration), n=6:")
    for t, r in RATES.items():
        print(f"  {t:12} lambda={r*6:5.1f}  P={poisson_inside(r*6):.3f}")
    print(f"\nAGGREGATE-of-three bootstrap P(clause 1 PASSES | perfect restoration), n=6: "
          f"{bootstrap_clause1():.3f}")
    p_any = sum(1 for x in CTRL_AGG if x > 0) / len(CTRL_AGG)
    print(f"control P(run uses >=1 of the three) = {p_any:.2f}; "
          f"P(arm b shows >=1 such run | restored) = {1-(1-p_any)**6:.3f}")
    for k in (3, 4, 5, 6):
        print(f"  Fisher 2-tailed armB {k}/6 vs armA 0/6: p={fisher(k, 6-k, 0, 6):.4f}")
