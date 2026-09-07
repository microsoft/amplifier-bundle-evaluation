import math
from math import comb

Z = 1.959963984540054  # 95% two-sided

def wilson(x, n, z=Z):
    if n == 0: return (0.0, 1.0)
    p = x / n
    d = 1 + z*z/n
    c = (p + z*z/(2*n)) / d
    h = (z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))) / d
    return (max(0.0, c-h), min(1.0, c+h))

def newcombe(x1, n1, x2, n2, z=Z):
    """Newcombe score CI for p1 - p2 (arm - stock)."""
    l1, u1 = wilson(x1, n1, z); l2, u2 = wilson(x2, n2, z)
    p1, p2 = x1/n1, x2/n2
    lo = (p1 - p2) - math.sqrt((p1-l1)**2 + (u2-p2)**2)
    hi = (p1 - p2) + math.sqrt((u1-p1)**2 + (p2-l2)**2)
    return (lo, hi)

def n_for_lb(target_pp):
    """smallest n with BOTH arms perfect (n/n) whose Newcombe LB >= -target_pp/100"""
    for n in range(1, 5000):
        lo, hi = newcombe(n, n, n, n)
        if lo >= -target_pp/100: return n, lo*100
    return None, None

def n_for_ub_zero(target_pp):
    """smallest n with BOTH arms 0/n whose Newcombe UB <= +target_pp/100"""
    for n in range(1, 5000):
        lo, hi = newcombe(0, n, 0, n)
        if hi <= target_pp/100: return n, hi*100
    return None, None

print("=== BEST-CASE (perfect agreement) Newcombe bound on (lean - stock) ===")
print(f"{'obs/arm':>8} {'hidden LB (both n/n)':>24} {'control UB (both 0/n)':>24}")
for n in (25, 50, 75, 80, 100, 146, 150, 292):
    lo,_ = newcombe(n,n,n,n)
    _,hi = newcombe(0,n,0,n)
    print(f"{n:>8} {lo*100:>23.2f}pp {hi*100:>23.2f}pp")

n1, lb = n_for_lb(5.0)
n2, ub = n_for_ub_zero(5.0)
print()
print(f"SMALLEST obs/arm satisfying hidden-reach >= -5.00pp on the LB : n={n1}  (LB={lb:.2f}pp)")
print(f"SMALLEST obs/arm satisfying over-reach   <= +5.00pp on the UB : n={n2}  (UB={ub:.2f}pp)")

print()
print("=== the goal's registered design ===")
print("hidden : 10 prompts x n=5 = 50 obs/arm/provider")
print("control:  5 prompts x n=5 = 25 obs/arm/provider")
lo,_ = newcombe(50,50,50,50); print(f"  hidden  best-case LB @50 obs = {lo*100:.2f}pp  -> {'PASS' if lo>=-0.05 else 'FAIL'} vs -5pp")
_,hi = newcombe(0,25,0,25);   print(f"  control best-case UB @25 obs = {hi*100:+.2f}pp -> {'PASS' if hi<=0.05 else 'FAIL'} vs +5pp")

print()
print("=== n PER PROMPT required (per provider, per arm) ===")
print(f"  hidden : {n1} obs / 10 prompts = n={math.ceil(n1/10)} per prompt  -> {math.ceil(n1/10)*10} obs")
print(f"  control: {n2} obs /  5 prompts = n={math.ceil(n2/5)} per prompt  -> {math.ceil(n2/5)*5} obs")
per_arm_prov = math.ceil(n1/10)*10 + math.ceil(n2/5)*5
print(f"  launches per arm per provider = {per_arm_prov}")
for arms in (2,3):
    print(f"  x {arms} arms x 2 providers = {per_arm_prov*arms*2} launches")

print()
print("=== POOLED (2 providers) variant ===")
n1p, lbp = n_for_lb(5.0)
print(f"  pooled needs the same {n1p} obs/arm TOTAL, i.e. n={math.ceil(n1p/10/2)} per prompt per provider (10 prompts x 2 providers)")
ph = math.ceil(n1p/20); pc = math.ceil(n2/10)
print(f"  hidden  n={ph}/prompt/provider -> {ph*10*2} obs/arm ; control n={pc}/prompt/provider -> {pc*5*2} obs/arm")
print(f"  launches per arm = {ph*10*2 + pc*5*2}; x2 arms = {(ph*10*2+pc*5*2)*2}")

print()
print("=== COLLAPSE DETECTION (Fisher exact, one-sided) at small n ===")
def fisher_one_sided(a,b,c,d):
    # P(X <= a) hypergeometric, tests arm-lean reach < arm-stock reach
    n1_,n2_ = a+b, c+d; k = a+c; N = n1_+n2_
    p = 0.0
    for x in range(0, a+1):
        if x> n1_ or (k-x) > n2_ or (k-x) < 0: continue
        p += comb(n1_,x)*comb(n2_,k-x)/comb(N,k)
    return p
for n in (5,6,8,10):
    print(f"  n={n:>2}/prompt/arm: stock {n}/{n} -> lean 0/{n}: p={fisher_one_sided(0,n,n,0):.5f}"
          f" | stock {n}/{n} -> lean {n//2}/{n}: p={fisher_one_sided(n//2,n-n//2,n,0):.5f}")
