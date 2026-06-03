#!/usr/bin/env bash
# examples/03-swebench-multimodal-foundation/run.sh
#
# Runs the SWE-bench Multimodal benchmark task through the amplifier_evaluation
# harness. Thin wrapper: samples the pinned instance onto disk, stages the
# problem statement + instance record, derives the repo/commit launch variables
# (the task profile clones the repo at the buggy commit), and dispatches the
# stock harness which handles DTU launch, agent install, the solver turn,
# extraction, and grading (the grader runs the official swebench Docker harness).
#
# Usage:
#   ./run.sh
#
# Environment overrides:
#   ANTHROPIC_API_KEY  required; falls back to ~/.amplifier/keys.env
#   MAX_PARALLEL       passed to the harness; default 1
#
# Prerequisites:
#   amplifier-digital-twin, uv, python3, docker on PATH; Docker daemon running
#   (used by BOTH the DTU and the swebench grader harness); amplifier_evaluation
#   importable (activate the bundle .venv or `uv pip install -e .`).

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
TASK_DIR="$HERE/tasks/swebench"
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

# ---- 1. sample the pinned SWE-bench instance -----------------------------
# problem_statement.md -> task workspace (for the SOLVER).
# instance.json (incl. gold patch + test_patch) -> grader-data ONLY.
log "sampling pinned SWE-bench instance"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
uv run --quiet --with huggingface_hub --with pyarrow python3 "$HERE/swebench/sample_swebench.py" \
    --output "$TMP" --pinned-file "$HERE/swebench/PINNED_INSTANCE_ID" --seed 42

mkdir -p "$TASK_DIR/workspace" "$TASK_DIR/grader-data"
cp "$TMP/problem_statement.md" "$TASK_DIR/workspace/problem_statement.md"
cp "$TMP/instance.json" "$TASK_DIR/grader-data/instance.json"

# Derive the repo clone variables for the task profile.
REPO="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo"])' "$TMP/instance.json")"
BASE_COMMIT="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_commit"])' "$TMP/instance.json")"
SWE_REPO="https://github.com/${REPO}.git"
log "instance repo=$REPO base_commit=$BASE_COMMIT"

# ---- 2. run the harness --------------------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"

log "running harness, output=$OUTPUT_DIR"
cd "$HERE"
python3 -m amplifier_evaluation run \
    --agents-dir "$HERE/agents" \
    --tasks-dir  "$HERE/tasks" \
    --pair   amplifier-foundation:swebench \
    --output-dir "$RESULTS_ROOT" \
    --run-id "$RUN_ID" \
    --max-parallel "$MAX_PARALLEL" \
    --trials-per-pair 1 \
    --launch-var "SWE_REPO=$SWE_REPO" \
    --launch-var "SWE_COMMIT=$BASE_COMMIT" \
    --verbose
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - summary.json -- per-trial state, score, elapsed_s"
log "  - trials/      -- state.json, install.log, ai_user.json, grader/, extraction/"
exit "$HARNESS_EXIT"
