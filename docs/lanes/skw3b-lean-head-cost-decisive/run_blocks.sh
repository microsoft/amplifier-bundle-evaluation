#!/bin/bash
# g7h3: ABBA arm-blocked block runner (PREREGISTRATION.md section 5).
#
# ONE arm is live at a time, across all DTUs. A block is N concurrent runs of a
# single arm. Between blocks of DIFFERENT arms it sleeps DRAIN_S (> Anthropic's
# 5-minute cache TTL) so the outgoing head's entries expire before the incoming
# head is written -- the structural form of skw3's single-arm control.
#
# Blocks are bought on BUDGET AND CLOCK ALONE. This script never reads a
# scorecard to decide whether to continue: no interim analysis of the primary.
#
# Usage: run_blocks.sh <seq> <start-block-index>
#   seq e.g. "s v v s s v v s"
set -uo pipefail
LANE_DIR="$(cd "$(dirname "$0")" && pwd)"
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-g7h3-lean-head-decisive
ARM="$CAP/opus5-medium.json"
DTUS=(val-g7h3-a val-g7h3-b val-g7h3-c)
DRAIN_S="${DRAIN_S:-360}"
BUDGET="${BUDGET:-930.00}"
WORST="${WORST:-6.50}"
SEQ=(${1:?seq required})
BI="${2:-3}"

spent() { python3 - "$CAP" <<'PY'
import json,glob,os,sys
tot=0.0
for p in glob.glob(os.path.join(sys.argv[1],"*","driver_record.json")):
    try: tot+=float(json.load(open(p)).get("session_cost_usd_last") or 0)
    except Exception: pass
print(f"{tot:.4f}")
PY
}

prev=""
for a in "${SEQ[@]}"; do
  cum=$(spent)
  need=$(python3 -c "print(f'{${cum}+${#DTUS[@]}*${WORST}:.2f}')")
  ok=$(python3 -c "print(1 if ${need} <= ${BUDGET} else 0)")
  if [ "$ok" != "1" ]; then
    echo "STOP: cum=$cum + ${#DTUS[@]}x\$$WORST = $need > \$$BUDGET"; exit 0
  fi
  if [ -n "$prev" ] && [ "$prev" != "$a" ]; then
    echo "drain ${DRAIN_S}s (arm switch $prev -> $a) at $(date -u +%H:%M:%SZ)"; sleep "$DRAIN_S"
  fi
  var=stock; [ "$a" = "v" ] && var=v1
  echo "=== BLOCK $(printf %02d $BI) arm=$var cum=\$$cum at $(date -u +%H:%M:%SZ) ==="
  r=1
  for d in "${DTUS[@]}"; do
    "$LANE_DIR/run_arm.sh" "$d" "$var" "g7h3-$a-b$(printf %02d $BI)-r0$r" "$ARM" || echo "LAUNCH-FAIL $d"
    r=$((r+1))
  done
  waited=0
  while pgrep -f "scripted_driver.py --dtu val-g7h3" >/dev/null; do
    sleep 30; waited=$((waited+30))
    if [ "$waited" -gt "${BLOCK_TIMEOUT_S:-2700}" ]; then
      echo "BLOCK TIMEOUT after ${waited}s -- killing stragglers"
      pkill -f "scripted_driver.py --dtu val-g7h3" || true; sleep 10; break
    fi
  done
  # capture each DTU's per-request head log BEFORE the next run resets it.
  # line count == request count; the variant/sha fields prove which head shipped.
  r=1
  for d in "${DTUS[@]}"; do
    amplifier-digital-twin exec "$d" -- bash -lc "cat /root/bji_head_log.jsonl 2>/dev/null" \
      | python3 -c "import sys,json;sys.stdout.write(json.load(sys.stdin)['stdout'])" \
      > "$CAP/g7h3-$a-b$(printf %02d $BI)-r0$r.headlog.jsonl" 2>/dev/null || true
    r=$((r+1))
  done
  echo "block $(printf %02d $BI) drained at $(date -u +%H:%M:%SZ) cum=\$$(spent)"
  prev="$a"; BI=$((BI+1))
done
echo "SEQUENCE COMPLETE cum=\$$(spent) at $(date -u +%H:%M:%SZ)"
