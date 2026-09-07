#!/usr/bin/env bash
# 2gxp -- one S3 run for one arm inside an ALREADY-LAUNCHED DTU.
# Usage: run_cell.sh <dtu> <arm a|b|c> <runid>
set -u
DTU="$1"; ARM="$2"; RUNID="$3"
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-2gxp-tool-vanishing
SCN="$CAP/scenario/s3"
HARN=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/scenarios/_harness
WS=/home/bkrabach/dev/openai-evals-team-ci
OUT="$CAP/runs/$RUNID"
PID=terra; MODEL=gpt-5.6-terra; EFFORT=medium
mkdir -p "$OUT"
adt(){ amplifier-digital-twin "$@"; }
exec_c(){ adt exec "$DTU" -- bash -lc "$1" 2>/dev/null | python3 -c 'import sys,json;sys.stdout.write(json.load(sys.stdin).get("stdout",""))' 2>/dev/null; }
{
echo "=== [$RUNID] arm=$ARM dtu=$DTU cell=$PID/$MODEL/$EFFORT $(date -u +%FT%TZ) ==="
DRVMD5=$(md5sum "$SCN/scripted_driver.py" | awk '{print $1}')
echo "driver_md5=$DRVMD5  (expect dc307c50090b11d981eee44382668431)"
echo "$DRVMD5" > "$OUT/driver_md5.txt"
echo "--- reset workspace + prior sessions ---"
exec_c 'rm -rf /root/s3-work /root/.amplifier/projects/*/sessions/* 2>/dev/null; mkdir -p /root/s3-work; echo RESET_OK'
echo "--- push harness + scenario ---"
adt file-push "$DTU" "$HARN/configure_cell.py" /root/configure_cell.py >/dev/null 2>&1
adt file-push "$DTU" "$SCN" /root/ -r >/dev/null 2>&1
adt file-push "$DTU" "$CAP/set_arm.py" /root/set_arm.py >/dev/null 2>&1
echo "--- configure cell ---"
exec_c "PY=\$(ls /root/.local/share/uv/tools/amplifier*/bin/python|head -1); \$PY /root/configure_cell.py --provider-id $PID --model $MODEL --effort $EFFORT | tail -3"
echo "--- SET ARM $ARM ---"
ARMSET=$(exec_c "PY=\$(ls /root/.local/share/uv/tools/amplifier*/bin/python|head -1); \$PY /root/set_arm.py $ARM")
echo "  $ARMSET"
echo "$ARMSET" > "$OUT/arm_set.txt"
case "$ARMSET" in *ARM_SET*) : ;; *) echo "ARM_SET_FAIL -- aborting run"; echo '{"invalid":"ARM_SET_FAIL"}' > "$OUT/driver_record.json"; exit 4 ;; esac
echo "--- seed reference ---"
exec_c 'mkdir -p /root/s3-work/reference; echo MKDIR_OK'
for fn in provider_openai__init__.py provider_anthropic__init__.py; do
  adt file-push "$DTU" "$SCN/reference_seed/$fn" "/root/s3-work/reference/$fn" >/dev/null 2>&1
done
SEEDED=$(exec_c 'ls /root/s3-work/reference/ 2>/dev/null | wc -l' | tr -d '[:space:]')
echo "  seeded reference files: $SEEDED (expect 2)"
[ "$SEEDED" = "2" ] || { echo "SEED_FAIL -- aborting run"; echo '{"invalid":"SEED_FAIL"}' > "$OUT/driver_record.json"; exit 3; }
echo "--- drive 5 turns (fixed driver) ---"
t0=$(date +%s)
python3 "$SCN/scripted_driver.py" --dtu "$DTU" --scenario-dir "$SCN" --outdir "$OUT" > "$OUT/driver.log" 2>&1
echo $(( $(date +%s) - t0 )) > "$OUT/host_wall.txt"
tail -8 "$OUT/driver.log"
echo "--- grade (in container) ---"
[ -f "$OUT/transcript.txt" ] && adt file-push "$DTU" "$OUT/transcript.txt" /root/s3-transcript.txt >/dev/null 2>&1
exec_c 'cd /root && python3 /root/s3/grader.py --deliverables /root/s3-work --transcript /root/s3-transcript.txt --scenario-dir /root/s3 --out /root/s3-scorecard.json >/root/s3-grade.log 2>&1; echo GRADED'
exec_c 'cat /root/s3-scorecard.json 2>/dev/null' > "$OUT/scorecard.json" 2>/dev/null
exec_c 'tail -5 /root/s3-grade.log 2>/dev/null' > "$OUT/grade.log" 2>/dev/null
echo "--- pull sessions ---"
mkdir -p "$OUT/all-sessions"
adt file-pull "$DTU" /root/.amplifier/projects "$OUT/all-sessions" -r >/dev/null 2>&1
prefer=""
[ -f "$OUT/driver_record.json" ] && prefer="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("root_session_id") or "")' "$OUT/driver_record.json" 2>/dev/null)"
root_sid="$(python3 /home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-8rugb/find_root.py "$OUT/all-sessions" "$prefer" 2>/dev/null)"
echo "$root_sid" > "$OUT/root_sid.txt"
python3 "$WS/probes/dw_measure.py" "$OUT/all-sessions" "$root_sid" > "$OUT/measure.json" 2>"$OUT/measure.err"
echo "  root_sid=$root_sid"
python3 -c "
import json
try:
    m=json.load(open('$OUT/measure.json'))
    print('  cost_usd=%s wall_s=%s llm_calls=%s' % (m.get('cost_usd'),m.get('wall_s'),m.get('llm_calls')))
except Exception as e: print('  measure unreadable:',e)
"
cat > "$OUT/meta.json" <<METAEOF
{"run":"$RUNID","arm":"$ARM","dtu":"$DTU","provider_id":"$PID","model":"$MODEL","effort":"$EFFORT",
 "driver_md5":"$DRVMD5","root_sid":"$root_sid","arm_set":"$ARMSET",
 "provider_openai_pin":"702b361a4d4d178da70cef96300591dc4015b9b1","prereg":"a4506d3a96b5bee27eb16576e1aa859a67c6593a",
 "finished_at":"$(date -u +%FT%TZ)"}
METAEOF
echo "=== [$RUNID] DONE $(date -u +%FT%TZ) ==="
} >> "$OUT/run.log" 2>&1
tail -4 "$OUT/run.log"
