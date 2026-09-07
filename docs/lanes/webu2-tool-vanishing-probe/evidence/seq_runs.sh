#!/usr/bin/env bash
# seq_runs.sh <dtu> <arm:runid> ...   -- interleaved round-robin, one DTU
set -u
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-2gxp-tool-vanishing
DTU="$1"; shift
for spec in "$@"; do
  ARM="${spec%%:*}"; RID="${spec##*:}"
  echo "[$(date -u +%T)] start $RID (arm $ARM)"
  "$CAP/run_cell.sh" "$DTU" "$ARM" "$RID" >> "$CAP/logs/seq.log" 2>&1
  echo "[$(date -u +%T)] done  $RID"
done
