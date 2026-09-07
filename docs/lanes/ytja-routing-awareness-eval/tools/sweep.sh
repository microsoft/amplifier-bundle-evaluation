#!/usr/bin/env bash
# One arm, both providers, a range of reps. Two of these run concurrently (one per
# container); within a container runs are serial so the two providers never contend.
set -u
ARM_NAME="$1"; DTU="$2"; REP_START="$3"; REPS="$4"
D="$(cd "$(dirname "$0")/.." && pwd)"
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260907-ytja-routing-awareness
for R in $(seq "$REP_START" $((REP_START+REPS-1))); do
  for CELL in "terra gpt-5.6-terra 600" "opus claude-opus-5 900"; do
    set -- $CELL
    python3 "$D/tools/run_cell.py" --dtu "$DTU" --arm "$ARM_NAME" --provider "$1" --model "$2" \
      --prompts "$D/scenarios/prompts.json" --out "$CAP" --reps 1 --rep-start "$R" --timeout "$3"
  done
done
