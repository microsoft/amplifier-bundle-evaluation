#!/usr/bin/env bash
# examples/04-foundation-vs-dev-demo/run.sh
#
# Foundation-vs-amplifier-dev demo, in the amplifier_evaluation library format.
# 3 HLE tasks + 3 SWE-bench Multimodal tasks, each run against TWO agent variants
# (amplifier-foundation and amplifier-dev) = 12 trials, dispatched through the
# stock harness with a configurable parallelism cap.
#
# This wrapper samples all 6 pinned tasks onto disk (the gated HLE data cannot be
# committed; SWE repos are cloned per-task by the profile via launch variables),
# then runs the harness over all 12 (agent, task) pairs.
#
# Usage:
#   ./run.sh
#
# Environment overrides:
#   ANTHROPIC_API_KEY  required; falls back to ~/.amplifier/keys.env
#   HF_TOKEN           required (cais/hle is gated); falls back to ~/.amplifier/keys.env
#   MAX_PARALLEL       concurrent trials; default 3
#
# Prerequisites:
#   amplifier-digital-twin, uv, python3, docker on PATH; Docker daemon running
#   (used by both the DTUs and the swebench grader); amplifier_evaluation importable.

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
RESULTS_ROOT="$HERE/results"
MAX_PARALLEL="${MAX_PARALLEL:-3}"

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

mapfile -t HLE_IDS < <(grep -v '^[[:space:]]*$' "$HERE/hle/PINNED_SAMPLE_IDS")
mapfile -t SWE_IDS < <(grep -v '^[[:space:]]*$' "$HERE/swebench/PINNED_INSTANCE_IDS")
[ "${#HLE_IDS[@]}" -ge 3 ] || die "expected 3 ids in hle/PINNED_SAMPLE_IDS"
[ "${#SWE_IDS[@]}" -ge 3 ] || die "expected 3 ids in swebench/PINNED_INSTANCE_IDS"

LAUNCH_VARS=()

# ---- 1. sample the 3 HLE questions --------------------------------------
for n in 1 2 3; do
    id="${HLE_IDS[$((n-1))]}"
    log "sampling HLE task $n: $id"
    TMP="$(mktemp -d)"
    uv run --quiet --with huggingface_hub --with pyarrow python3 "$HERE/hle/sample_hle.py" \
        --output "$TMP" --sample-id "$id"
    td="$HERE/tasks/hle-$n"
    mkdir -p "$td/workspace" "$td/grader-data"
    rm -f "$td/workspace/question.md" "$td"/workspace/question_image.*
    cp "$TMP/question.md" "$td/workspace/question.md"
    cp "$TMP"/question_image.* "$td/workspace/" 2>/dev/null || true
    cp "$TMP/sample.json" "$td/grader-data/reference.json"
    rm -rf "$TMP"
done

# ---- 2. sample the 3 SWE-bench instances --------------------------------
for n in 1 2 3; do
    id="${SWE_IDS[$((n-1))]}"
    log "sampling SWE-bench task $n: $id"
    TMP="$(mktemp -d)"
    uv run --quiet --with huggingface_hub --with pyarrow python3 "$HERE/swebench/sample_swebench.py" \
        --output "$TMP" --instance-id "$id"
    td="$HERE/tasks/swebench-$n"
    mkdir -p "$td/workspace" "$td/grader-data"
    cp "$TMP/problem_statement.md" "$td/workspace/problem_statement.md"
    cp "$TMP/instance.json" "$td/grader-data/instance.json"
    repo="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["repo"])' "$TMP/instance.json")"
    commit="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_commit"])' "$TMP/instance.json")"
    LAUNCH_VARS+=(--launch-var "SWE_REPO_$n=https://github.com/${repo}.git" --launch-var "SWE_COMMIT_$n=$commit")
    rm -rf "$TMP"
done

# ---- 3. build the 12 (agent, task) pairs --------------------------------
PAIRS=()
for agent in amplifier-foundation amplifier-dev; do
    for task in hle-1 hle-2 hle-3 swebench-1 swebench-2 swebench-3; do
        PAIRS+=(--pair "$agent:$task")
    done
done

RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"

log "running harness over 12 pairs (max_parallel=$MAX_PARALLEL), output=$OUTPUT_DIR"
cd "$HERE"
python3 -m amplifier_evaluation.harness.run \
    --agents "$HERE/agents" \
    --tasks  "$HERE/tasks" \
    "${PAIRS[@]}" \
    --output "$OUTPUT_DIR" \
    --max-parallel "$MAX_PARALLEL" \
    --trials-per-pair 1 \
    "${LAUNCH_VARS[@]}" \
    --verbose
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR (summary.json, trials/, dashboard)"
exit "$HARNESS_EXIT"
