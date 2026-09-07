#!/usr/bin/env python3
"""PREREG 6 P-A -- predict arm b's head saving from webu's captured control tools array.
Spends nothing. Run BEFORE launch; the prediction is registered, not fitted."""
import glob, json, sys

CPT = 4.627
WEBU = sys.argv[1] if len(sys.argv) > 1 else \
    "/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-webu-phase2"
ARM_A_DEFERS = {"delegate", "edit_file", "glob", "grep", "read_file", "write_file",
                "web_fetch", "web_search", "load_skill", "mode", "recipes"}
ARM_B_KEEPS = {"write_file", "edit_file", "delegate"}
WEBU_SAVING = 6313.5   # webu FINDINGS table 1, pinned cache_read t0 -> t1

c = lambda o: json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
tools = None
for f in glob.glob(f"{WEBU}/runs/t0-01/all-sessions/**/sessions/*/events.jsonl", recursive=True):
    if "/context-intelligence/" in f:
        continue
    for line in open(f, encoding="utf-8", errors="replace"):
        try: e = json.loads(line)
        except Exception: continue
        if (e.get("event") or "") == "llm:request":
            t = ((e.get("data") or {}).get("raw") or {}).get("tools")
            if isinstance(t, list) and t:
                tools = t
                break
    if tools: break

size = {x.get("name") or x.get("type"): round(len(c(x)) / CPT, 1) for x in tools}
defer_a = sum(v for k, v in size.items() if k in ARM_A_DEFERS)
defer_b = sum(v for k, v in size.items() if k in ARM_A_DEFERS - ARM_B_KEEPS)
overhead = defer_a - WEBU_SAVING
print("per-schema wire tokens (webu control request 0):")
for k, v in sorted(size.items(), key=lambda kv: -kv[1]):
    print(f"  {k:14} {v:8.1f}{'   [arm b keeps LOADED]' if k in ARM_B_KEEPS else ''}")
print(f"\narm a defers {defer_a:.1f} tok; webu measured saving {WEBU_SAVING} -> namespace overhead {overhead:.1f}")
print(f"arm b defers {defer_b:.1f} tok")
print(f"  proportional model: {WEBU_SAVING * defer_b / defer_a:8.1f} tok = "
      f"{100 * defer_b / defer_a:.1f}% of arm a's saving")
print(f"  overhead model    : {defer_b - overhead:8.1f} tok = "
      f"{100 * (defer_b - overhead) / WEBU_SAVING:.1f}% of arm a's saving")
print("PREDICTION P-A: clause 2 (>=50% of arm a's saving) FAILS.")
