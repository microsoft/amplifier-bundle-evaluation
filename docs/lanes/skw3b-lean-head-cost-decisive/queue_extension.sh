#!/bin/bash
# Waits for the pre-registered 24-block sequence to exit, then runs the
# extension queued in RUNLOG.md entry 3 -- decided on clock and budget alone,
# before any analysis of any delta.
LANE_DIR="$(cd "$(dirname "$0")" && pwd)"
CAP=/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation/20260906-g7h3-lean-head-decisive
while pgrep -f "run_blocks.sh s s v" >/dev/null || pgrep -f "run_blocks.sh .* 4$" >/dev/null; do sleep 60; done
sleep 360   # drain across the boundary between the two sequences
cd "$LANE_DIR"
WORST=6.72 BUDGET=930.00 DRAIN_S=360 ./run_blocks.sh "v s s v v s s v" 27 >> "$CAP/blocks.log" 2>&1
