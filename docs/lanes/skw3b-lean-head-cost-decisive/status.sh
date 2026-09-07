#!/bin/bash
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-g7h3-lean-head-decisive
python3 - "$CAP" <<'PY'
import json,glob,os,sys,statistics
cap=sys.argv[1]; rows=[]
for d in sorted(glob.glob(os.path.join(cap,"g7h3-*"))):
    p=os.path.join(d,"driver_record.json")
    if not os.path.isdir(d) or not os.path.exists(p): continue
    r=json.load(open(p)); sc=r.get("scorecard") or {}
    arm="stock" if "/g7h3-s-" in d+"/" or os.path.basename(d).startswith("g7h3-s-") else "v1"
    rows.append((arm,float(r.get("session_cost_usd_last") or 0),bool(sc.get("valid"))))
void=sum(json.load(open(os.path.join(d,"driver_record.json"))).get("session_cost_usd_last") or 0
         for d in glob.glob(os.path.join(cap,"VOID-*")) if os.path.exists(os.path.join(d,"driver_record.json")))
tot=sum(c for _,c,_ in rows)+void
for a in ("stock","v1"):
    sub=[r for r in rows if r[0]==a]; val=[c for _,c,v in sub if v]
    print(f"{a:5s} launched {len(sub):3d} valid {len(val):3d}  mean_valid ${statistics.mean(val):.3f}" if val
          else f"{a:5s} launched {len(sub):3d} valid   0")
print(f"SPEND ${tot:.2f} / $930.00   runs={len(rows)}")
PY
grep -cE "^=== BLOCK" "$CAP/blocks.log"; tail -1 "$CAP/blocks.log"
