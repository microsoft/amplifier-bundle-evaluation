#!/usr/bin/env bash
# examples/02-hle-foundation/run.sh
#
# Runs the HLE benchmark task through the amplifier_evaluation harness. This is
# a thin wrapper: it samples the pinned HLE question onto disk (the gated cais/hle
# dataset cannot be committed), stages it into the task, and dispatches the stock
# harness which handles DTU launch, agent install, the solver turn, extraction,
# and LLM-judge grading.
#
# Usage:
#   ./run.sh
#
# Environment overrides:
#   ANTHROPIC_API_KEY  required; falls back to ~/.amplifier/keys.env
#   HF_TOKEN           required (cais/hle is gated); falls back to ~/.amplifier/keys.env
#   MAX_PARALLEL       passed to the harness; default 1
#
# Prerequisites:
#   amplifier-digital-twin, uv, python3, docker on PATH; Docker daemon running;
#   amplifier_evaluation importable (activate the bundle .venv or
#   `uv pip install -e .` against the bundle root).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
TASK_DIR="$HERE/tasks/hle"
RESULTS_ROOT="$HERE/results"
MAX_PARALLEL="${MAX_PARALLEL:-1}"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
command -v uv >/dev/null || die "uv not on PATH"
command -v python3 >/dev/null || die "python3 not on PATH"
command -v docker >/dev/null || die "docker not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"
python3 -c "import amplifier_evaluation" 2>/dev/null \
    || die "amplifier_evaluation not importable; activate the bundle .venv or 'uv pip install -e .' in $BUNDLE_ROOT"

if [ -f "$HOME/.amplifier/keys.env" ]; then set -a; . "$HOME/.amplifier/keys.env"; set +a; fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"
[ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN not set (cais/hle is gated); set it or add to ~/.amplifier/keys.env"

# ---- 1. sample the pinned HLE question -----------------------------------
# The question (and image) go to the task workspace for the SOLVER. The full
# record -- which includes the ground-truth answer -- goes ONLY to grader-data,
# so the solver never sees the answer.
log "sampling pinned HLE question"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
uv run --quiet --with huggingface_hub --with pyarrow python3 "$HERE/hle/sample_hle.py" \
    --output "$TMP" --pinned-file "$HERE/hle/PINNED_SAMPLE_ID" --seed 42

mkdir -p "$TASK_DIR/workspace" "$TASK_DIR/grader-data"
rm -f "$TASK_DIR/workspace/question.md" "$TASK_DIR"/workspace/question_image.*
cp "$TMP/question.md" "$TASK_DIR/workspace/question.md"
cp "$TMP"/question_image.* "$TASK_DIR/workspace/" 2>/dev/null || true
cp "$TMP/sample.json" "$TASK_DIR/grader-data/reference.json"
log "staged question into task workspace; reference answer into grader-data"

# ---- 2. run the harness --------------------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"

log "running harness, output=$OUTPUT_DIR"
cd "$HERE"
python3 -m amplifier_evaluation run \
    --agents-dir "$HERE/agents" \
    --tasks-dir  "$HERE/tasks" \
    --pair   amplifier-foundation:hle \
    --output-dir "$RESULTS_ROOT" \
    --run-id "$RUN_ID" \
    --max-parallel "$MAX_PARALLEL" \
    --trials-per-pair 1 \
    --verbose
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - summary.json -- per-trial state, score, elapsed_s"
log "  - trials/      -- state.json, install.log, ai_user.json, grader/, extraction/"
exit "$HARNESS_EXIT"
