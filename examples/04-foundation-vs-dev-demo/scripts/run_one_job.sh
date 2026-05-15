#!/usr/bin/env bash
# Per-job worker for example 04.
#
# Runs ONE (variant, benchmark, task_idx) combination end-to-end:
#   1. Launch a dedicated DTU
#   2. Stage the task into /work/task/
#   3. Run the solver (setsid + sentinel + poll pattern; HLE caps at 20 min,
#      SWE-bench at 45 min)
#   4. Pull artifacts (answer.txt or patch.diff, plus the amplifier session dir)
#   5. Judge (HLE) or grade (SWE-bench) on the host
#   6. Write meta.json
#   7. Destroy the DTU
#
# Usage:
#   run_one_job.sh <variant> <benchmark> <task_idx> <top_results_dir>
#
# Where:
#   variant     ::= foundation | amplifier-dev
#   benchmark   ::= hle | swebench
#   task_idx    ::= 1 | 2 | 3
#   top_results ::= absolute path to results/<date>/ (already exists, with _samples/<bench>/task-<idx>/ populated)
#
# All output goes to stdout/stderr of this script; the parent orchestrator
# captures it into a per-job log file.

set -euo pipefail

VARIANT="$1"
BENCHMARK="$2"
TASK_IDX="$3"
TOP_RESULTS="$4"

EXAMPLE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JOB_ID="${VARIANT}-${BENCHMARK}-${TASK_IDX}"
DTU="demo04-${JOB_ID}"
JOB_RESULTS="${TOP_RESULTS}/${VARIANT}/${BENCHMARK}/task-${TASK_IDX}/run-1"
SAMPLE_DIR="${TOP_RESULTS}/_samples/${BENCHMARK}/task-${TASK_IDX}"
PROFILE="${EXAMPLE_DIR}/profiles/${VARIANT}.yaml"
SWE_DATASET="${AMPLIFIER_DEMO_SWE_DATASET:-multimodal}"

log() { printf '[%s] [%s] %s\n' "$(date +%H:%M:%S)" "$JOB_ID" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- preconditions ------------------------------------------------------
[ -d "$SAMPLE_DIR" ] || die "sample dir $SAMPLE_DIR not found"
[ -f "$PROFILE" ] || die "profile $PROFILE not found"
case "$BENCHMARK" in
    hle)
        [ -f "$SAMPLE_DIR/sample.json" ] || die "missing $SAMPLE_DIR/sample.json"
        [ -f "$SAMPLE_DIR/question.md" ] || die "missing $SAMPLE_DIR/question.md"
        ;;
    swebench)
        [ -f "$SAMPLE_DIR/instance.json" ] || die "missing $SAMPLE_DIR/instance.json"
        [ -f "$SAMPLE_DIR/problem_statement.md" ] || die "missing $SAMPLE_DIR/problem_statement.md"
        ;;
    *) die "unknown benchmark $BENCHMARK" ;;
esac

mkdir -p "$JOB_RESULTS/solver"
# Symlink the shared sample dir into this run dir so metrics + report tools
# can find sample.json / instance.json at JOB_RESULTS/sample/.
ln -sfn "$SAMPLE_DIR" "$JOB_RESULTS/sample"

# ---- helpers ------------------------------------------------------------
parse_exec_stdout() {
    # Pull the stdout field out of an amplifier-digital-twin exec JSON output,
    # falling back to raw content. Reads from $1 (file path).
    python3 - "$1" <<'PY'
import json, sys
p = sys.argv[1]
try:
    d = json.load(open(p))
    print(d.get("stdout") or "")
except Exception:
    try:
        print(open(p).read())
    except Exception:
        print("")
PY
}

# ---- 1. launch DTU ------------------------------------------------------
log "destroying any prior DTU named $DTU"
amplifier-digital-twin destroy "$DTU" >/dev/null 2>&1 || true

log "launching DTU from $(basename "$PROFILE")"
amplifier-digital-twin launch "$PROFILE" --name "$DTU" >/dev/null

# ---- 2. stage task in DTU + build solver prompt -------------------------
if [ "$BENCHMARK" = "hle" ]; then
    HAS_IMAGE="$(python3 -c "import json; print('1' if json.load(open('$SAMPLE_DIR/sample.json')).get('has_image') else '0')")"
    IMAGE_NAME=""
    if [ "$HAS_IMAGE" = "1" ]; then
        IMAGE_NAME="$(python3 -c "import json; print(json.load(open('$SAMPLE_DIR/sample.json')).get('image_filename', ''))")"
    fi
    log "staging question.md into /work/task/ (image=$HAS_IMAGE)"
    amplifier-digital-twin file-push "$DTU" \
        "$SAMPLE_DIR/question.md" /work/task/question.md >/dev/null
    if [ -n "$IMAGE_NAME" ]; then
        amplifier-digital-twin file-push "$DTU" \
            "$SAMPLE_DIR/$IMAGE_NAME" "/work/task/$IMAGE_NAME" >/dev/null
    fi
    SOLVER_PROMPT="$(python3 -c "
import sys; sys.path.insert(0, '$EXAMPLE_DIR/hle')
from prompts import build_solver_prompt
print(build_solver_prompt('$IMAGE_NAME' if '$IMAGE_NAME' else None))
")"
    WORK_SUBDIR=""
    MAX_WAIT=$((20 * 60))   # HLE cap: 20 min
else
    REPO="$(python3 -c "import json; print(json.load(open('$SAMPLE_DIR/instance.json'))['repo'])")"
    BASE_COMMIT="$(python3 -c "import json; print(json.load(open('$SAMPLE_DIR/instance.json'))['base_commit'])")"
    log "cloning $REPO @ ${BASE_COMMIT:0:12} into /work/task/repo"
    amplifier-digital-twin exec "$DTU" -- bash -c "
        set -e
        cd /work/task
        rm -rf repo
        git clone --quiet https://github.com/$REPO.git repo
        cd repo
        git checkout --quiet $BASE_COMMIT
        echo CLONE_OK
    " > "$JOB_RESULTS/solver/clone.json" 2>&1 || die "clone exec failed"
    parse_exec_stdout "$JOB_RESULTS/solver/clone.json" > "$JOB_RESULTS/solver/clone.log"
    grep -q CLONE_OK "$JOB_RESULTS/solver/clone.log" || die "git clone failed inside DTU"

    log "staging problem_statement.md into /work/task/"
    amplifier-digital-twin file-push "$DTU" \
        "$SAMPLE_DIR/problem_statement.md" /work/task/problem_statement.md >/dev/null

    SOLVER_PROMPT="$(python3 -c "
import sys; sys.path.insert(0, '$EXAMPLE_DIR/swebench')
from prompts import build_solver_prompt
print(build_solver_prompt('$SWE_DATASET'))
")"
    WORK_SUBDIR="/repo"   # cd /work/task/repo for SWE-bench
    # SWE-bench Verified Python instances often take longer than Multimodal JS.
    if [ "$SWE_DATASET" = "verified" ]; then
        MAX_WAIT=$((60 * 60))   # Verified cap: 60 min
    else
        MAX_WAIT=$((45 * 60))   # Multimodal cap: 45 min
    fi
fi

log "solver prompt: $(printf '%s' "$SOLVER_PROMPT" | wc -c) chars"

# ---- 3. run solver (setsid + sentinel + poll) ---------------------------
log "launching solver in DTU (detached via setsid)"
amplifier-digital-twin exec "$DTU" -- bash -c "
    rm -f /work/task/.sentinel
    cat > /work/task/run_solver.sh <<'SOLVER_EOF'
#!/usr/bin/env bash
export PATH=/root/.local/bin:\$PATH
cd /work/task${WORK_SUBDIR}
amplifier run \"\$1\" > /work/task/solver.log 2>&1
echo \$? > /work/task/.sentinel
SOLVER_EOF
    chmod +x /work/task/run_solver.sh
    setsid /work/task/run_solver.sh \"$SOLVER_PROMPT\" < /dev/null >/dev/null 2>&1 &
    disown || true
    echo SOLVER_LAUNCHED
" > "$JOB_RESULTS/solver/launch.json" 2>&1 || die "exec failed at solver launch"

parse_exec_stdout "$JOB_RESULTS/solver/launch.json" > "$JOB_RESULTS/solver/launch.log"
grep -q SOLVER_LAUNCHED "$JOB_RESULTS/solver/launch.log" || die "solver did not launch"

log "polling for solver completion (60s interval, $((MAX_WAIT/60))min cap)"
SOLVER_START=$(date +%s)
SOLVER_EXIT=-1
while true; do
    elapsed=$(( $(date +%s) - SOLVER_START ))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "WARNING: solver exceeded ${MAX_WAIT}s -- abandoning"
        SOLVER_EXIT=124
        break
    fi
    if amplifier-digital-twin exec "$DTU" -- bash -c "test -f /work/task/.sentinel && cat /work/task/.sentinel" \
        > "$JOB_RESULTS/solver/sentinel.json" 2>/dev/null; then
        SENTINEL_TEXT="$(parse_exec_stdout "$JOB_RESULTS/solver/sentinel.json" | tr -d '[:space:]')"
        if [ -n "$SENTINEL_TEXT" ] && [[ "$SENTINEL_TEXT" =~ ^-?[0-9]+$ ]]; then
            SOLVER_EXIT="$SENTINEL_TEXT"
            break
        fi
    fi
    log "  ... ${elapsed}s elapsed, still running"
    sleep 60
done
SOLVER_END=$(date +%s)
SOLVER_WALL=$((SOLVER_END - SOLVER_START))
log "solver finished wall=${SOLVER_WALL}s exit=$SOLVER_EXIT"

# ---- 4. pull artifacts --------------------------------------------------
log "pulling solver.log -> solver/stdout.txt"
amplifier-digital-twin file-pull "$DTU" \
    /work/task/solver.log "$JOB_RESULTS/solver/stdout.txt" >/dev/null 2>&1 \
    || log "WARNING: could not pull solver.log"

SOLVER_SID="$(grep -oE 'Session ID: [a-f0-9-]{36}' "$JOB_RESULTS/solver/stdout.txt" 2>/dev/null | head -1 | awk '{print $3}' || true)"
[ -n "$SOLVER_SID" ] || log "WARNING: no Session ID in solver stdout"

if [ "$BENCHMARK" = "hle" ]; then
    log "pulling answer.txt"
    amplifier-digital-twin file-pull "$DTU" \
        /work/task/answer.txt "$JOB_RESULTS/solver/answer.txt" >/dev/null 2>&1 \
        || log "WARNING: no answer.txt produced"
else
    log "extracting patch via git diff inside DTU"
    amplifier-digital-twin exec "$DTU" -- bash -c "
        cd /work/task/repo
        git add -N . >/dev/null 2>&1 || true
        git diff
    " > "$JOB_RESULTS/solver/patch_exec.json" 2>&1 || log "WARNING: git diff exec failed"
    parse_exec_stdout "$JOB_RESULTS/solver/patch_exec.json" > "$JOB_RESULTS/solver/patch.diff"
    log "patch chars: $(wc -c < "$JOB_RESULTS/solver/patch.diff")"
fi

# Pull the amplifier session directory.
if [ -n "$SOLVER_SID" ]; then
    log "pulling solver session dir (id=$SOLVER_SID)"
    rm -rf "$JOB_RESULTS/solver/sessions"
    # Discover the project slug in the DTU and pull its sessions/ subtree.
    amplifier-digital-twin exec "$DTU" -- bash -c "ls /root/.amplifier/projects/ 2>/dev/null" \
        > "$JOB_RESULTS/solver/projects_ls.json" 2>&1 || true
    PROJ_SLUG="$(parse_exec_stdout "$JOB_RESULTS/solver/projects_ls.json" | head -1 | tr -d '[:space:]')"
    if [ -n "$PROJ_SLUG" ]; then
        amplifier-digital-twin file-pull "$DTU" -r \
            "/root/.amplifier/projects/${PROJ_SLUG}/sessions/" \
            "$JOB_RESULTS/solver/sessions/" >/dev/null 2>&1 \
            || log "WARNING: failed to pull session dir"
    else
        log "WARNING: could not resolve amplifier projects slug"
    fi
fi

# ---- 5. resolve foundation sha so the run is reproducible --------------
FOUNDATION_SHA="$(git ls-remote https://github.com/microsoft/amplifier-foundation refs/heads/main 2>/dev/null | awk '{print $1}' || true)"

# ---- 6. judge or grade on host -----------------------------------------
VERDICT_KEY="correct"
if [ "$BENCHMARK" = "hle" ]; then
    log "judging answer in a separate amplifier session (host)"
    JUDGE_START=$(date +%s)
    mkdir -p "$JOB_RESULTS/judge"
    python3 "$EXAMPLE_DIR/hle/judge.py" \
        --sample "$SAMPLE_DIR/sample.json" \
        --answer "$JOB_RESULTS/solver/answer.txt" \
        --output "$JOB_RESULTS/judge" \
        || log "WARNING: judge exited non-zero"
    JUDGE_WALL=$(( $(date +%s) - JUDGE_START ))
    if [ -f "$JOB_RESULTS/judge/verdict.json" ]; then
        OUTCOME="$(python3 -c "import json; print('true' if json.load(open('$JOB_RESULTS/judge/verdict.json')).get('correct') else 'false')")"
    else
        OUTCOME="false"
    fi
    GRADER_WALL=0
else
    log "grading patch via official swebench harness (Docker)"
    GRADER_START=$(date +%s)
    mkdir -p "$JOB_RESULTS/grader"
    MODEL_NAME="amplifier-${VARIANT}-${TASK_IDX}"
    uv run --quiet --with swebench python3 "$EXAMPLE_DIR/swebench/grade.py" \
        --instance "$SAMPLE_DIR/instance.json" \
        --patch "$JOB_RESULTS/solver/patch.diff" \
        --output "$JOB_RESULTS/grader" \
        --model-name "$MODEL_NAME" \
        --dataset "$SWE_DATASET" \
        || log "WARNING: grader exited non-zero (see grader/harness_stderr.txt)"
    GRADER_WALL=$(( $(date +%s) - GRADER_START ))
    if [ -f "$JOB_RESULTS/grader/verdict.json" ]; then
        OUTCOME="$(python3 -c "import json; print('true' if json.load(open('$JOB_RESULTS/grader/verdict.json')).get('resolved') else 'false')")"
    else
        OUTCOME="false"
        cat > "$JOB_RESULTS/grader/verdict.json" <<JSON
{"resolved": false, "error": "harness did not produce verdict.json", "status": {}}
JSON
    fi
    VERDICT_KEY="resolved"
    JUDGE_WALL=0
fi
log "verdict: ${VERDICT_KEY}=$OUTCOME"

# ---- 7. write meta.json -------------------------------------------------
python3 - <<PY
import json, datetime, pathlib

results = pathlib.Path("$JOB_RESULTS")
meta = {
    "example": "04-foundation-vs-dev-demo",
    "variant": "$VARIANT",
    "benchmark": "$BENCHMARK",
    "task_idx": int("$TASK_IDX"),
    "ran_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "solver": {
        "session_id": ("$SOLVER_SID" or None),
        "dtu_id": "$DTU",
        "wall_seconds": int("$SOLVER_WALL"),
        "exit_code": (int("$SOLVER_EXIT") if "$SOLVER_EXIT".lstrip("-").isdigit() else None),
        "foundation_branch": "main",
        "foundation_sha": "$FOUNDATION_SHA",
        "profile": "profiles/${VARIANT}.yaml",
    },
    "judge": {"wall_seconds": int("$JUDGE_WALL")} if "$BENCHMARK" == "hle" else {},
    "grader": {"wall_seconds": int("$GRADER_WALL")} if "$BENCHMARK" == "swebench" else {},
    "verdict": {"$VERDICT_KEY": ("$OUTCOME" == "true")},
}
(results / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
PY

# ---- 8. destroy DTU -----------------------------------------------------
log "destroying DTU"
amplifier-digital-twin destroy "$DTU" >/dev/null 2>&1 || true

# ---- 9. render per-run verdict.html -------------------------------------
log "rendering verdict.html"
python3 "$EXAMPLE_DIR/metrics/render_verdict.py" "$JOB_RESULTS" \
    || log "WARNING: render_verdict.py failed"

log "job complete: ${VERDICT_KEY}=$OUTCOME, results in $JOB_RESULTS"