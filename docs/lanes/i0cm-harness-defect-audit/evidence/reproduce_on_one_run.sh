#!/usr/bin/env bash
# Reproduce the continuity defect on ONE already-captured run. $0, read-only.
#
#   ./reproduce_on_one_run.sh [RUN_DIR]
#
# Default RUN_DIR is 8rugb's A-anth-01. Shows, in order:
#   1. what the driver recorded  (session_continuity_ok=false, sid=null on turns 2-5)
#   2. what each turn's stdout ACTUALLY printed  ("Session ID:" once, "Resuming session:" 4x, same id)
#   3. what the container's own session file says (5 prompt:complete in the ONE root session)
set -euo pipefail

RUN="${1:-/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-8rugb/runs/A-anth-01}"
[ -d "$RUN" ] || { echo "no such run dir: $RUN" >&2; exit 2; }

echo "RUN: $RUN"
echo
echo "--- 1. what the driver RECORDED -------------------------------------------"
python3 -c '
import json,sys
d=json.load(open(sys.argv[1]+"/driver_record.json"))
print("  session_continuity_ok :", d.get("session_continuity_ok"))
print("  root_session_id       :", d.get("root_session_id"))
for t in d["turns"]:
    print("  turn%s: done=%s marker=%s session_id=%s out_len=%s"
          % (t["n"], t["done"], t["marker"], t["session_id"], t["out_len"]))
' "$RUN"

echo
echo "--- 2. what each turn ACTUALLY printed ------------------------------------"
for i in 1 2 3 4 5; do
  [ -f "$RUN/turn$i.out" ] || continue
  printf '  turn%s: ' "$i"
  if grep -o -m1 -E 'Session ID:[[:space:]]*[0-9a-f-]{8,}' "$RUN/turn$i.out"; then :;
  elif grep -o -m1 -E 'Resuming session:[[:space:]]*[0-9a-f-]{8,}' "$RUN/turn$i.out"; then :;
  else echo "(no session line — empty or timed-out capture)"; fi
done

echo
echo "--- 3. what the CONTAINER's own session file says --------------------------"
SID=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]+"/driver_record.json"))["root_session_id"])' "$RUN")
EV="$RUN/all-sessions/projects/-root-s3-work/sessions/$SID/events.jsonl"
if [ -f "$EV" ]; then
  echo "  root session $SID"
  echo "  prompt:complete events: $(grep -c 'prompt:complete' "$EV")   (compare against the turn count above; the driver flag said continuity FAILED)"
else
  echo "  root session events.jsonl not present in this capture ($EV)"
fi
