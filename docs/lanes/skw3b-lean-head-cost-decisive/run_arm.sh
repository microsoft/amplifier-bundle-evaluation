#!/bin/bash
# g7h3: launch ONE S7-17 arm run, fully detached, into a NAMED container.
#
# Driver parameters are byte-identical to 3d2/vbs/5zp (SPEC.md 9.1 freezes the
# S7-17 profile). TWO deliberate differences, both forced and both disclosed:
#
#  1. --arm-file is a caller-supplied path, so this lane can use its own
#     opus5-medium cell without writing into the shared scenarios/ tree
#     (GOAL.md 0rg hazard).
#  2. The cell is configured HERE, with this lane's own patched
#     configure_cell_g7h3.py, and the driver is then run with
#     --skip-configure. The shipped _harness/configure_cell.py cannot set
#     max_tokens against today's amplifier-foundation@main (its
#     find_bundle_md() is pinned to anchors-amp-dev/bundle.md, which no longer
#     carries the line), and scripted_driver.py SWALLOWS that failure -- see
#     FINDINGS.md. The shared file is NOT edited; the fix is emitted as
#     skw3b-configure-cell-anchors-fallback.diff for the manager to apply.
#
# The configure step FAILS LOUD here: if it does not print MAXTOK_OK the run is
# not launched, because that is exactly the silent-invalid-run failure mode
# this lane paid $3.85 to discover.
#
# Usage: run_arm.sh <dtu> <variant> <outname> <arm-file>
set -euo pipefail
DTU="${1:?dtu required}"
VARIANT="${2:?variant required (stock|v1)}"
OUTNAME="${3:?outname required}"
ARMFILE="${4:?arm-file required}"
CAP="${CAP:-/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-g7h3-lean-head-decisive}"
SCEN_ROOT="/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/scenarios"
TOOL_PY=/root/.local/share/uv/tools/amplifier/bin/python
mkdir -p "$CAP"

PID=$(python3 -c "import json,sys;print(json.load(open('$ARMFILE'))['provider_id'])")
MODEL=$(python3 -c "import json,sys;print(json.load(open('$ARMFILE'))['model'])")
EFFORT=$(python3 -c "import json,sys;print(json.load(open('$ARMFILE'))['effort'])")

# 1. select the arm variant and start this run's head log from empty.
amplifier-digital-twin exec "$DTU" -- bash -lc \
  "printf '%s' '{\"variant\":\"$VARIANT\"}' > /root/bji_variant.json; rm -f /root/bji_head_log.jsonl; rm -rf /root/s7-archive /root/s7-work; cat /root/bji_variant.json" \
  > "$CAP/$OUTNAME.armsel.json" 2>&1

# 2. configure the cell OURSELVES, and refuse to launch unless it really took.
CFG=$(amplifier-digital-twin exec "$DTU" -- bash -lc \
  "$TOOL_PY /root/configure_cell_g7h3.py --provider-id $PID --model $MODEL --effort $EFFORT --max-tokens 90000" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['stdout'].strip())")
echo "$CFG" > "$CAP/$OUTNAME.configure.txt"
case "$CFG" in
  *MAXTOK_OK*max_tokens=90000*) : ;;
  *) echo "REFUSING TO LAUNCH $OUTNAME -- configure did not take: $CFG" >&2; exit 9 ;;
esac
case "$CFG" in
  *"PRIMARY_OK id=$PID model=$MODEL effort=$EFFORT"*) : ;;
  *) echo "REFUSING TO LAUNCH $OUTNAME -- wrong cell: $CFG" >&2; exit 10 ;;
esac

# 3. drive it, detached. setsid is load-bearing (bji's disclosed voided run).
cd "$SCEN_ROOT"
setsid nohup python3 s7-retention-headroom/scripted_driver.py \
    --dtu "$DTU" \
    --scenario-dir s7-retention-headroom \
    --outdir "$CAP/$OUTNAME" \
    --arm-file "$ARMFILE" \
    --skip-configure \
    --max-tokens 90000 \
    --max-turns 17 \
    --constraints-file s7-retention-headroom/constraints_t17.json \
    --min-boundaries 5 \
    > "$CAP/$OUTNAME.log" 2>&1 < /dev/null &
echo "launched dtu=$DTU variant=$VARIANT out=$OUTNAME cfg=OK pid=$! at $(date -u +%H:%M:%SZ)"
