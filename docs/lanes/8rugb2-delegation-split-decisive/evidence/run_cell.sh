#!/usr/bin/env bash
# 8rugb -- one S3 run for one {arm, provider} cell in an already-launched DTU.
# Usage: run_cell.sh <dtu> <A|B> <provider_id> <model> <effort> <runid>
set -u
DTU="$1"; ARM="$2"; PID="$3"; MODEL="$4"; EFFORT="$5"; RUNID="$6"
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-njpd
SCN=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/scenarios
TK=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260901-threeknob
WS=/home/bkrabach/dev/openai-evals-team-ci
OUT="$CAP/runs/$RUNID"
mkdir -p "$OUT"
adt(){ amplifier-digital-twin "$@"; }
exec_c(){ adt exec "$DTU" -- bash -lc "$1" 2>/dev/null | python3 -c 'import sys,json;sys.stdout.write(json.load(sys.stdin).get("stdout",""))' 2>/dev/null; }
{
echo "=== [$RUNID] arm=$ARM dtu=$DTU cell=$PID/$MODEL/$EFFORT $(date -u +%FT%TZ) ==="
echo "--- reset workspace + prior sessions ---"
exec_c 'rm -rf /root/s3-work /root/.amplifier/projects/*/sessions/* 2>/dev/null; mkdir -p /root/s3-work; echo RESET_OK'
echo "--- push harness + scenario ---"
adt file-push "$DTU" "$SCN/_harness/configure_cell.py" /root/configure_cell.py >/dev/null 2>&1
adt file-push "$DTU" "$SCN/s3" /root/ -r >/dev/null 2>&1
echo "--- configure cell ---"
exec_c "PY=\$(ls /root/.local/share/uv/tools/amplifier*/bin/python|head -1); \$PY /root/configure_cell.py --provider-id $PID --model $MODEL --effort $EFFORT | tail -2"
echo "--- seed + drive (background) ---"
t0=$(date +%s)
bash "$TK/seed_and_run_s3.sh" "$DTU" "$OUT" >>"$OUT/seed.log" 2>&1
waited=0
while [ "$waited" -lt 4200 ]; do
  [ -f "$OUT/driver_record.json" ] && break
  sleep 30; waited=$((waited+30))
done
echo $(( $(date +%s) - t0 )) > "$OUT/host_wall.txt"
if [ -f "$OUT/driver_record.json" ]; then echo "  driver_record present after ${waited}s"; else echo "  DRIVER CAP HIT after ${waited}s"; fi
echo "--- wait for the final prompt:complete to FLUSH before pulling (capture race) ---"
# The CLI process exits before the session writer has flushed that turn's
# prompt:complete: measured lag 100-200 s on this host. Pulling immediately
# captures 5 prompt:submit and only 4 prompt:complete, which the PRE-REGISTERED
# validity gate correctly rejects. This waits for the evidence to exist before
# reading it. It can only make the capture more faithful -- a turn that never
# completed still times out here and still fails the gate.
prefer=""
[ -f "$OUT/driver_record.json" ] && prefer="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("root_session_id") or "")' "$OUT/driver_record.json" 2>/dev/null)"
pc=0; w=0
if [ -n "$prefer" ]; then
  while [ "$w" -lt 600 ]; do
    pc=$(exec_c "cat /root/.amplifier/projects/*/sessions/$prefer/events.jsonl 2>/dev/null | grep -c '\"prompt:complete\"'" | tr -d '[:space:]')
    case "$pc" in ''|*[!0-9]*) pc=0 ;; esac
    [ "$pc" -ge 5 ] && break
    sleep 15; w=$((w+15))
  done
fi
echo "  prompt:complete=$pc after ${w}s (sid=$prefer)"
echo "--- grade (in container) ---"
[ -f "$OUT/transcript.txt" ] && adt file-push "$DTU" "$OUT/transcript.txt" /root/s3-transcript.txt >/dev/null 2>&1
exec_c 'cd /root && python3 /root/s3/grader.py --deliverables /root/s3-work --transcript /root/s3-transcript.txt --scenario-dir /root/s3 --out /root/s3-scorecard.json >/root/s3-grade.log 2>&1; echo GRADED'
exec_c 'cat /root/s3-scorecard.json 2>/dev/null' > "$OUT/scorecard.json" 2>/dev/null
exec_c 'tail -5 /root/s3-grade.log 2>/dev/null' > "$OUT/grade.log" 2>/dev/null
echo "--- pull sessions + measure ---"
mkdir -p "$OUT/all-sessions"
adt file-pull "$DTU" /root/.amplifier/projects "$OUT/all-sessions" -r >/dev/null 2>&1
prefer=""
[ -f "$OUT/driver_record.json" ] && prefer="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1])).get("root_session_id") or "")' "$OUT/driver_record.json" 2>/dev/null)"
root_sid="$(python3 "$CAP/find_root.py" "$OUT/all-sessions" "$prefer" 2>/dev/null)"
python3 "$WS/probes/dw_measure.py" "$OUT/all-sessions" "$root_sid" > "$OUT/measure.json" 2>"$OUT/measure.err"
echo "  root_sid=$root_sid"
python3 "$CAP/summarize_run.py" "$OUT" "$RUNID" "$ARM" "$PID" 2>&1 | tail -3
python3 "$CAP/fanout.py" "$OUT" "$root_sid" 2>&1 | tail -1
echo "=== [$RUNID] DONE $(date -u +%FT%TZ) ==="
} >> "$OUT/run.log" 2>&1
tail -4 "$OUT/run.log"
