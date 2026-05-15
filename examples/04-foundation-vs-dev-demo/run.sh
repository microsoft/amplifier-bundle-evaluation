#!/usr/bin/env bash
# Example 04: Foundation vs Amplifier Dev demo.
#
# Runs 3 HLE tasks and 3 SWE-bench Multimodal tasks against TWO variants of
# the amplifier bundle (foundation and amplifier-dev), for 12 total
# (variant, benchmark, task) jobs. Jobs run in parallel, capped at
# AMPLIFIER_DEMO_MAX_PARALLEL DTUs (default 5).
#
# Idempotent. Re-running on the same day appends/overwrites the dated
# results/<YYYY-MM-DD>/ tree.
#
# Prerequisites:
#   - amplifier-digital-twin, amplifier, uv, git on PATH; Docker running
#   - ANTHROPIC_API_KEY (env or ~/.amplifier/keys.env)
#   - HF_TOKEN         (env or ~/.amplifier/keys.env) for the HLE sampler
#
# Usage:
#   ./run.sh
#
# Environment overrides:
#   AMPLIFIER_DEMO_MAX_PARALLEL=5        # max concurrent DTUs
#   AMPLIFIER_DEMO_NUM_HLE=3             # number of HLE tasks
#   AMPLIFIER_DEMO_NUM_SWE=3             # number of SWE-bench tasks
#   AMPLIFIER_DEMO_SEED=42               # random seed for task selection
#   AMPLIFIER_DEMO_SWE_DATASET=multimodal  # 'multimodal' (JS, image-heavy,
#                                          # needs strong vision) or 'verified'
#                                          # (Python, broader code-fix signal).
#                                          # Default 'multimodal'.

set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
RESULTS="$EXAMPLE_DIR/results/$DATE"
LOGS_DIR="$RESULTS/_logs"
SAMPLES_DIR="$RESULTS/_samples"

MAX_PARALLEL="${AMPLIFIER_DEMO_MAX_PARALLEL:-5}"
NUM_HLE="${AMPLIFIER_DEMO_NUM_HLE:-3}"
NUM_SWE="${AMPLIFIER_DEMO_NUM_SWE:-3}"
SEED="${AMPLIFIER_DEMO_SEED:-42}"
SWE_DATASET="${AMPLIFIER_DEMO_SWE_DATASET:-multimodal}"
case "$SWE_DATASET" in
    multimodal|verified) ;;
    *) echo "ERROR: AMPLIFIER_DEMO_SWE_DATASET must be 'multimodal' or 'verified', got '$SWE_DATASET'" >&2; exit 2 ;;
esac
# Per-dataset pin file so multimodal and verified runs don't clobber each other.
if [ "$SWE_DATASET" = "verified" ]; then
    SWE_PIN_FILE="$EXAMPLE_DIR/swebench/PINNED_INSTANCE_IDS_VERIFIED"
else
    SWE_PIN_FILE="$EXAMPLE_DIR/swebench/PINNED_INSTANCE_IDS"
fi
export AMPLIFIER_DEMO_SWE_DATASET="$SWE_DATASET"   # so worker can read it

log() { printf '[%s] [run] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
command -v amplifier >/dev/null || die "amplifier not on PATH"
command -v uv >/dev/null || die "uv not on PATH"
command -v git >/dev/null || die "git not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"

if [ -z "${ANTHROPIC_API_KEY:-}" ] || [ -z "${HF_TOKEN:-}" ]; then
    if [ -f "$HOME/.amplifier/keys.env" ]; then
        set -a
        # shellcheck disable=SC1091
        . "$HOME/.amplifier/keys.env"
        set +a
    fi
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set"
[ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN not set (cais/hle is a gated dataset)"

mkdir -p "$LOGS_DIR" "$SAMPLES_DIR"

log "config: max_parallel=$MAX_PARALLEL num_hle=$NUM_HLE num_swe=$NUM_SWE seed=$SEED swe_dataset=$SWE_DATASET"
log "results dir: $RESULTS"

# ---- 1. sample tasks once on the host -----------------------------------
log "sampling $NUM_HLE HLE tasks (seed=$SEED)"
uv run --quiet --with huggingface_hub --with pyarrow \
    python3 "$EXAMPLE_DIR/hle/sample_hle.py" \
        --output "$SAMPLES_DIR/hle" \
        --num "$NUM_HLE" \
        --pinned-file "$EXAMPLE_DIR/hle/PINNED_SAMPLE_IDS" \
        --seed "$SEED"

log "sampling $NUM_SWE SWE-bench $SWE_DATASET tasks (seed=$SEED)"
uv run --quiet --with huggingface_hub --with pyarrow \
    python3 "$EXAMPLE_DIR/swebench/sample_swebench.py" \
        --output "$SAMPLES_DIR/swebench" \
        --num "$NUM_SWE" \
        --pinned-file "$SWE_PIN_FILE" \
        --dataset "$SWE_DATASET" \
        --seed "$SEED"

# ---- 2. build the job list ---------------------------------------------
JOBS_FILE="$LOGS_DIR/jobs.txt"
> "$JOBS_FILE"
for variant in foundation amplifier-dev; do
    for benchmark in hle swebench; do
        n=$NUM_HLE
        [ "$benchmark" = "swebench" ] && n=$NUM_SWE
        for idx in $(seq 1 "$n"); do
            echo "$variant $benchmark $idx" >> "$JOBS_FILE"
        done
    done
done
TOTAL_JOBS="$(wc -l < "$JOBS_FILE")"
log "queued $TOTAL_JOBS jobs"

# ---- 3. parallel dispatch (background jobs, capped) --------------------
RUN_START=$(date +%s)

# Bash semaphore: block while running-job count is at the cap.
sem() {
    while [ "$(jobs -r | wc -l)" -ge "$MAX_PARALLEL" ]; do
        wait -n 2>/dev/null || true
    done
}

run_one() {
    local v="$1" b="$2" i="$3"
    local job_id="${v}-${b}-${i}"
    local out="$LOGS_DIR/${job_id}.log"
    local start_ts end_ts
    start_ts=$(date +%s)
    log "STARTED $job_id (log: ${out})"
    # </dev/null is REQUIRED: without it the worker subprocess inherits
    # the parent's stdin (which is JOBS_FILE) and amplifier-digital-twin
    # tries to interpret "foundation hle 1" as YAML on Incus's stdin.
    if bash "$EXAMPLE_DIR/scripts/run_one_job.sh" "$v" "$b" "$i" "$RESULTS" \
            </dev/null >"$out" 2>&1; then
        end_ts=$(date +%s)
        log "FINISHED $job_id (wall=$((end_ts - start_ts))s)"
    else
        end_ts=$(date +%s)
        log "FAILED   $job_id (wall=$((end_ts - start_ts))s, see ${out})"
    fi
}

log "dispatching with max_parallel=$MAX_PARALLEL"
while read -r variant benchmark idx; do
    sem
    run_one "$variant" "$benchmark" "$idx" &
    # small stagger to avoid thundering Docker startup
    sleep 1
done < "$JOBS_FILE"

log "all jobs dispatched, waiting for completion"
wait
RUN_END=$(date +%s)
log "all jobs complete wall=$((RUN_END - RUN_START))s"

# ---- 4. build HTML report ----------------------------------------------
log "building HTML report"
python3 "$EXAMPLE_DIR/metrics/build_html_report.py" "$RESULTS" \
    --output "$RESULTS/report.html"

log "done. results: $RESULTS/"
log "  report.html:  $RESULTS/report.html"
log "  per-job logs: $LOGS_DIR/"
log "  per-run dirs: $RESULTS/{foundation,amplifier-dev}/{hle,swebench}/task-N/run-1/"