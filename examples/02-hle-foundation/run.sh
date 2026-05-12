#!/usr/bin/env bash
# Example 02: Foundation on Humanity's Last Exam (orchestrator).
#
# End-to-end runner: samples one HLE question on the host (pinned), launches a
# DTU with amplifier + foundation@main, stages the question into the DTU,
# runs the agent, pulls the answer + session back, then judges the answer in
# a separate amplifier session on the host.
#
# Idempotent. Re-running creates a fresh dated results/<YYYY-MM-DD>/ directory.
# The sample id is pinned in hle/PINNED_SAMPLE_ID after the first run, so all
# subsequent runs use the same HLE question.
#
# Prerequisites (script aborts with a clear message if missing):
#   - amplifier-digital-twin, amplifier on PATH
#   - Docker daemon running
#   - ANTHROPIC_API_KEY in env or in ~/.amplifier/keys.env
#   - HF_TOKEN     in env or in ~/.amplifier/keys.env (cais/hle is gated)
#   - uv on PATH (used to run sample_hle.py with isolated deps)
#
# Run from this directory:
#     ./run.sh

set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
RESULTS="$EXAMPLE_DIR/results/$DATE/run-1"
PINNED_FILE="$EXAMPLE_DIR/hle/PINNED_SAMPLE_ID"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
command -v amplifier >/dev/null || die "amplifier not on PATH"
command -v uv >/dev/null || die "uv not on PATH"
command -v git >/dev/null || die "git not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"

# Load secrets from keys.env if needed.
if [ -z "${ANTHROPIC_API_KEY:-}" ] || [ -z "${HF_TOKEN:-}" ]; then
    if [ -f "$HOME/.amplifier/keys.env" ]; then
        set -a
        # shellcheck disable=SC1091
        . "$HOME/.amplifier/keys.env"
        set +a
    fi
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"
[ -n "${HF_TOKEN:-}" ] || die "HF_TOKEN not set and not in ~/.amplifier/keys.env (cais/hle is a gated dataset)"

mkdir -p "$RESULTS/sample" "$RESULTS/solver" "$RESULTS/judge"

# ---- 1. sample on the host ----------------------------------------------
log "sampling HLE question (pinned=$( [ -f "$PINNED_FILE" ] && echo yes || echo no ))"
uv run --quiet --with huggingface_hub --with pyarrow \
    python3 "$EXAMPLE_DIR/hle/sample_hle.py" \
        --output "$RESULTS/sample" \
        --pinned-file "$PINNED_FILE" \
        --seed 42

SAMPLE_ID="$(python3 -c "import json; print(json.load(open('$RESULTS/sample/sample.json'))['id'])")"
HAS_IMAGE="$(python3 -c "import json; print('1' if json.load(open('$RESULTS/sample/sample.json')).get('has_image') else '0')")"
IMAGE_NAME=""
if [ "$HAS_IMAGE" = "1" ]; then
    IMAGE_NAME="$(python3 -c "import json; print(json.load(open('$RESULTS/sample/sample.json')).get('image_filename', ''))")"
fi
log "sample id=$SAMPLE_ID  has_image=$HAS_IMAGE${IMAGE_NAME:+  image=$IMAGE_NAME}"

# ---- 2. launch the solver DTU -------------------------------------------
DTU="eval02-foundation"
log "destroying any prior DTU named $DTU"
amplifier-digital-twin destroy "$DTU" >/dev/null 2>&1 || true

log "launching DTU from profiles/foundation.yaml"
amplifier-digital-twin launch "$EXAMPLE_DIR/profiles/foundation.yaml" --name "$DTU" >/dev/null

# ---- 3. stage the task inside the DTU -----------------------------------
log "staging question into /work/hle-task/"
amplifier-digital-twin file-push "$DTU" \
    "$RESULTS/sample/question.md" /work/hle-task/question.md >/dev/null
if [ -n "$IMAGE_NAME" ]; then
    amplifier-digital-twin file-push "$DTU" \
        "$RESULTS/sample/$IMAGE_NAME" "/work/hle-task/$IMAGE_NAME" >/dev/null
fi

# ---- 4. build the solver prompt -----------------------------------------
SOLVER_PROMPT="$(python3 -c "
import sys
sys.path.insert(0, '$EXAMPLE_DIR/hle')
from prompts import build_solver_prompt
print(build_solver_prompt('$IMAGE_NAME' if '$IMAGE_NAME' else None))
")"

# Sanity-print the prompt so it shows up in the run log.
log "solver prompt ($(echo "$SOLVER_PROMPT" | wc -c) chars):"
printf '%s\n' "$SOLVER_PROMPT" | sed 's/^/    /' >&2

# ---- 5. run the solver --------------------------------------------------
log "running solver (amplifier run inside DTU)"
SOLVER_START=$(date +%s)
amplifier-digital-twin exec "$DTU" -- bash -c \
    "export PATH=/root/.local/bin:\$PATH && cd /work/hle-task && amplifier run \"$SOLVER_PROMPT\" 2>&1" \
    > "$RESULTS/solver/exec.json" 2>&1
SOLVER_EXIT=$?
SOLVER_END=$(date +%s)
SOLVER_WALL=$((SOLVER_END - SOLVER_START))
log "solver finished wall=${SOLVER_WALL}s exit=$SOLVER_EXIT"

# Extract stdout + session id from the exec wrapper output.
python3 -c "import json; d=json.load(open('$RESULTS/solver/exec.json')); open('$RESULTS/solver/stdout.txt','w').write(d.get('stdout',''))"
SOLVER_SID="$(grep -oE 'Session ID: [a-f0-9-]{36}' "$RESULTS/solver/stdout.txt" | head -1 | awk '{print $3}' || true)"
[ -n "$SOLVER_SID" ] || log "WARNING: could not find Session ID in solver stdout"

# ---- 6. pull answer + session out of the DTU ----------------------------
log "pulling answer.txt"
amplifier-digital-twin file-pull "$DTU" \
    /work/hle-task/answer.txt "$RESULTS/solver/answer.txt" >/dev/null || \
    log "WARNING: no answer.txt produced"

if [ -n "$SOLVER_SID" ]; then
    log "pulling solver session dir (id=$SOLVER_SID)"
    amplifier-digital-twin file-pull "$DTU" -r \
        "/root/.amplifier/projects/-work-hle-task/sessions/" \
        "$RESULTS/solver/sessions/" >/dev/null || \
        log "WARNING: failed to pull session dir"
fi

# ---- 7. resolve foundation sha so the run is reproducible --------------
FOUNDATION_SHA="$(git ls-remote https://github.com/microsoft/amplifier-foundation refs/heads/main | awk '{print $1}')"

# ---- 8. judge the answer in a separate amplifier session ---------------
log "judging answer in a separate amplifier session (host)"
python3 "$EXAMPLE_DIR/hle/judge.py" \
    --sample "$RESULTS/sample/sample.json" \
    --answer "$RESULTS/solver/answer.txt" \
    --output "$RESULTS/judge"

CORRECT="$(python3 -c "import json; print('true' if json.load(open('$RESULTS/judge/verdict.json'))['correct'] else 'false')")"
log "verdict: correct=$CORRECT"

# ---- 9. write meta.json --------------------------------------------------
# Build meta.json via Python so booleans, nulls, and Unicode are JSON-safe.
python3 - <<PY
import json, datetime
from pathlib import Path

results = Path("$RESULTS")
verdict = json.loads((results / "judge" / "verdict.json").read_text())
has_image = bool(int("$HAS_IMAGE"))
solver_sid = "$SOLVER_SID" or None

meta = {
    "example": "02-hle-foundation",
    "run": 1,
    "ran_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "sample": {
        "id": "$SAMPLE_ID",
        "has_image": has_image,
    },
    "solver": {
        "session_id": solver_sid,
        "dtu_id": "$DTU",
        "wall_seconds": int("$SOLVER_WALL"),
        "exit_code": int("$SOLVER_EXIT"),
        "foundation_branch": "main",
        "foundation_sha": "$FOUNDATION_SHA",
        "profile": "profiles/foundation.yaml",
    },
    "judge": {
        "session_id": verdict.get("judge_session_id"),
        "wall_seconds": verdict.get("judge_wall_seconds"),
        "correct": bool(verdict.get("correct")),
    },
}
(results / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
PY

log "rendering human-readable summary"
python3 "$EXAMPLE_DIR/metrics/summarize_run.py" "$RESULTS"

log "done, results under $RESULTS/"
log "  outcome:            $RESULTS/verdict-$( [ "$CORRECT" = "true" ] && echo correct || echo incorrect ).md"
log "  structured metrics: python3 $EXAMPLE_DIR/metrics/extract_metrics.py $RESULTS"
