#!/usr/bin/env bash
# Example 03: Foundation on SWE-bench Multimodal (orchestrator).
#
# End-to-end runner: samples one SWE-bench Multimodal instance on the host
# (pinned by default), launches a DTU with amplifier + foundation@main, clones
# the repo at base_commit inside the DTU, stages the issue, runs the agent,
# extracts the patch via `git diff`, then grades the patch in the official
# swebench harness on the host (Docker-based).
#
# Idempotent. Re-running creates a fresh dated results/<YYYY-MM-DD>/ directory.
# The instance id is pinned in swebench/PINNED_INSTANCE_ID; delete that file
# to re-sample with seed=42.
#
# Prerequisites (script aborts with a clear message if missing):
#   - amplifier-digital-twin, amplifier on PATH
#   - Docker daemon running (used by BOTH the DTU and the host-side swebench harness)
#   - ANTHROPIC_API_KEY in env or in ~/.amplifier/keys.env
#   - uv on PATH (used to run sampler + grader with isolated deps)
#
# Run from this directory:
#     ./run.sh

set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
RESULTS="$EXAMPLE_DIR/results/$DATE/run-1"
PINNED_FILE="$EXAMPLE_DIR/swebench/PINNED_INSTANCE_ID"

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
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    if [ -f "$HOME/.amplifier/keys.env" ]; then
        set -a
        # shellcheck disable=SC1091
        . "$HOME/.amplifier/keys.env"
        set +a
    fi
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"

mkdir -p "$RESULTS/sample" "$RESULTS/solver" "$RESULTS/grader"

# ---- 1. sample on the host ----------------------------------------------
log "sampling SWE-bench Multimodal instance (pinned=$( [ -s "$PINNED_FILE" ] && echo yes || echo no ))"
uv run --quiet --with huggingface_hub --with pyarrow \
    python3 "$EXAMPLE_DIR/swebench/sample_swebench.py" \
        --output "$RESULTS/sample" \
        --pinned-file "$PINNED_FILE" \
        --seed 42

INSTANCE_ID="$(python3 -c "import json; print(json.load(open('$RESULTS/sample/instance.json'))['instance_id'])")"
REPO="$(python3 -c "import json; print(json.load(open('$RESULTS/sample/instance.json'))['repo'])")"
BASE_COMMIT="$(python3 -c "import json; print(json.load(open('$RESULTS/sample/instance.json'))['base_commit'])")"
log "instance=$INSTANCE_ID repo=$REPO base_commit=${BASE_COMMIT:0:12}..."

# ---- 2. launch the solver DTU -------------------------------------------
DTU="eval03-foundation"
log "destroying any prior DTU named $DTU"
amplifier-digital-twin destroy "$DTU" >/dev/null 2>&1 || true

log "launching DTU from profiles/foundation.yaml"
amplifier-digital-twin launch "$EXAMPLE_DIR/profiles/foundation.yaml" --name "$DTU" >/dev/null

# ---- 3. stage the task inside the DTU -----------------------------------
log "cloning $REPO @ $BASE_COMMIT into /work/swe-task/repo (in DTU)"
amplifier-digital-twin exec "$DTU" -- bash -c "
    set -e
    cd /work/swe-task
    rm -rf repo
    git clone --quiet https://github.com/$REPO.git repo
    cd repo
    git checkout --quiet $BASE_COMMIT
    git status --short
    echo 'CLONE_OK'
" 2>&1 | tee "$RESULTS/solver/clone.log" >&2

grep -q CLONE_OK "$RESULTS/solver/clone.log" || die "git clone or checkout failed inside DTU"

log "staging problem_statement.md into /work/swe-task/"
amplifier-digital-twin file-push "$DTU" \
    "$RESULTS/sample/problem_statement.md" /work/swe-task/problem_statement.md >/dev/null

# ---- 4. build the solver prompt -----------------------------------------
SOLVER_PROMPT="$(python3 -c "
import sys
sys.path.insert(0, '$EXAMPLE_DIR/swebench')
from prompts import build_solver_prompt
print(build_solver_prompt())
")"

log "solver prompt ($(echo "$SOLVER_PROMPT" | wc -c) chars)"
printf '%s\n' "$SOLVER_PROMPT" | sed 's/^/    /' >&2

# ---- 5. run the solver --------------------------------------------------
# amplifier-digital-twin exec has a hard 600s timeout. A real SWE-bench
# attempt easily takes 10-30 min, so we use the setsid + sentinel + poll
# pattern documented in the 20260512 learnings.
log "starting solver in DTU (detached via setsid; will poll for completion)"
amplifier-digital-twin exec "$DTU" -- bash -c "
    rm -f /work/swe-task/.sentinel
    cat > /work/swe-task/run_solver.sh <<'SOLVER_EOF'
#!/usr/bin/env bash
export PATH=/root/.local/bin:\$PATH
cd /work/swe-task/repo
amplifier run \"\$1\" > /work/swe-task/solver.log 2>&1
echo \$? > /work/swe-task/.sentinel
SOLVER_EOF
    chmod +x /work/swe-task/run_solver.sh
    setsid /work/swe-task/run_solver.sh \"$SOLVER_PROMPT\" < /dev/null >/dev/null 2>&1 &
    disown || true
    echo SOLVER_LAUNCHED
" 2>&1 | tee -a "$RESULTS/solver/launch.log" >&2

grep -q SOLVER_LAUNCHED "$RESULTS/solver/launch.log" || die "failed to launch solver in DTU"

# Poll for the sentinel. We check every 30s. Cap at 45 minutes — a real
# SWE-bench attempt that runs longer than that is probably stuck.
log "polling for solver completion (30s interval, 45min max)"
SOLVER_START=$(date +%s)
MAX_WAIT=$((45 * 60))
SOLVER_EXIT=-1
while true; do
    elapsed=$(( $(date +%s) - SOLVER_START ))
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "WARNING: solver exceeded ${MAX_WAIT}s timeout — abandoning"
        SOLVER_EXIT=124
        break
    fi
    # Test for sentinel via a single short exec; if found, read its content.
    if amplifier-digital-twin exec "$DTU" -- bash -c "test -f /work/swe-task/.sentinel && cat /work/swe-task/.sentinel" \
        > "$RESULTS/solver/sentinel.txt" 2>/dev/null; then
        # exec's stdout JSON wrapping varies; pull the digit out.
        SOLVER_EXIT="$(python3 -c "
import json, sys
try:
    d = json.load(open('$RESULTS/solver/sentinel.txt'))
    s = (d.get('stdout') or '').strip()
except Exception:
    s = open('$RESULTS/solver/sentinel.txt').read().strip()
print(s if s.isdigit() else '')
" 2>/dev/null || true)"
        if [ -n "$SOLVER_EXIT" ]; then
            break
        fi
    fi
    log "  ... ${elapsed}s elapsed, still running"
    sleep 30
done
SOLVER_END=$(date +%s)
SOLVER_WALL=$((SOLVER_END - SOLVER_START))
log "solver finished wall=${SOLVER_WALL}s exit=$SOLVER_EXIT"

# ---- 6. pull solver log + extract patch ---------------------------------
log "pulling solver.log"
amplifier-digital-twin file-pull "$DTU" \
    /work/swe-task/solver.log "$RESULTS/solver/stdout.txt" >/dev/null 2>&1 || \
    log "WARNING: failed to pull solver.log"

SOLVER_SID="$(grep -oE 'Session ID: [a-f0-9-]{36}' "$RESULTS/solver/stdout.txt" 2>/dev/null | head -1 | awk '{print $3}' || true)"
[ -n "$SOLVER_SID" ] || log "WARNING: could not find Session ID in solver stdout"

log "extracting patch via git diff inside DTU"
amplifier-digital-twin exec "$DTU" -- bash -c "
    cd /work/swe-task/repo
    git add -N . >/dev/null 2>&1 || true
    git diff
" > "$RESULTS/solver/patch_exec.json" 2>&1 || log "WARNING: git diff exec failed"

# Pull the diff text out of the exec wrapper.
python3 -c "
import json, sys
try:
    d = json.load(open('$RESULTS/solver/patch_exec.json'))
    text = d.get('stdout', '')
except Exception:
    text = open('$RESULTS/solver/patch_exec.json').read()
open('$RESULTS/solver/patch.diff', 'w').write(text)
print(f'patch chars: {len(text)}', file=sys.stderr)
"

if [ -n "$SOLVER_SID" ]; then
    log "pulling solver session dir (id=$SOLVER_SID)"
    rm -rf "$RESULTS/solver/sessions"
    # The amplifier session lives under projects/-work-swe-task-repo because the
    # solver ran from /work/swe-task/repo. The project slug is derived from cwd.
    PROJ_SLUG="$(amplifier-digital-twin exec "$DTU" -- bash -c "
        ls /root/.amplifier/projects/ 2>/dev/null | head -1
    " 2>/dev/null | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print((d.get('stdout') or '').strip())
except Exception:
    print('')
" 2>/dev/null || true)"
    if [ -n "$PROJ_SLUG" ]; then
        amplifier-digital-twin file-pull "$DTU" -r \
            "/root/.amplifier/projects/$PROJ_SLUG/sessions/" \
            "$RESULTS/solver/sessions/" >/dev/null 2>&1 || \
            log "WARNING: failed to pull session dir"
    else
        log "WARNING: could not resolve amplifier projects slug"
    fi
fi

# ---- 7. resolve foundation sha so the run is reproducible --------------
FOUNDATION_SHA="$(git ls-remote https://github.com/microsoft/amplifier-foundation refs/heads/main | awk '{print $1}')"

# ---- 8. grade the patch with the official swebench harness on host -----
log "running official swebench harness (host-side; pulls Docker images on first run)"
GRADER_START=$(date +%s)
uv run --quiet --with swebench \
    python3 "$EXAMPLE_DIR/swebench/grade.py" \
        --instance "$RESULTS/sample/instance.json" \
        --patch "$RESULTS/solver/patch.diff" \
        --output "$RESULTS/grader" || \
    log "WARNING: grader exited non-zero (see grader/harness_stderr.txt)"
GRADER_END=$(date +%s)
GRADER_WALL=$((GRADER_END - GRADER_START))

if [ -f "$RESULTS/grader/verdict.json" ]; then
    RESOLVED="$(python3 -c "import json; print('true' if json.load(open('$RESULTS/grader/verdict.json'))['resolved'] else 'false')")"
else
    log "WARNING: verdict.json not produced; defaulting to unresolved"
    RESOLVED="false"
    cat > "$RESULTS/grader/verdict.json" <<JSON
{"resolved": false, "error": "harness did not produce verdict.json", "status": {}}
JSON
fi
log "verdict: resolved=$RESOLVED (grader wall=${GRADER_WALL}s)"

# ---- 9. post-run analysis (separate amplifier session on host) ----------
# Spins up a fresh amplifier session with cwd=$RESULTS so it can inspect
# all artifacts (sample, solver patch + session, grader verdict + harness
# output) and produce ANALYSIS.md + analysis_metadata.json.
log "running post-run analyzer (separate amplifier session, host-side)"
ANALYSIS_START=$(date +%s)
python3 "$EXAMPLE_DIR/swebench/analyze.py" \
    --run-dir "$RESULTS" \
    --output  "$RESULTS/analysis" || \
    log "WARNING: analyzer exited non-zero (see analysis/stderr.txt)"
ANALYSIS_END=$(date +%s)
ANALYSIS_WALL=$((ANALYSIS_END - ANALYSIS_START))

ANALYSIS_CLASSIFICATION="$(python3 -c "
import json
try:
    d = json.load(open('$RESULTS/analysis/analysis_metadata.json'))
    print(d.get('classification', 'UNKNOWN'))
except Exception:
    print('UNKNOWN')
")"
log "analyzer finished (wall=${ANALYSIS_WALL}s classification=$ANALYSIS_CLASSIFICATION)"

# ---- 10. write meta.json ------------------------------------------------
python3 - <<PY
import json, datetime
from pathlib import Path

results = Path("$RESULTS")
verdict = json.loads((results / "grader" / "verdict.json").read_text())
solver_sid = "$SOLVER_SID" or None

analysis_meta = {}
analysis_run = {}
amd = results / "analysis" / "analysis_metadata.json"
ari = results / "analysis" / "run_info.json"
if amd.exists():
    analysis_meta = json.loads(amd.read_text())
if ari.exists():
    analysis_run = json.loads(ari.read_text())

meta = {
    "example": "03-swebench-multimodal-foundation",
    "run": 1,
    "ran_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "instance": {
        "id": "$INSTANCE_ID",
        "repo": "$REPO",
        "base_commit": "$BASE_COMMIT",
    },
    "solver": {
        "session_id": solver_sid,
        "dtu_id": "$DTU",
        "wall_seconds": int("$SOLVER_WALL"),
        "exit_code": int("$SOLVER_EXIT") if "$SOLVER_EXIT".lstrip('-').isdigit() else None,
        "foundation_branch": "main",
        "foundation_sha": "$FOUNDATION_SHA",
        "profile": "profiles/foundation.yaml",
    },
    "grader": {
        "wall_seconds": int("$GRADER_WALL"),
        "harness_exit_code": verdict.get("harness_exit_code"),
        "harness_run_id": verdict.get("harness_run_id"),
        "resolved": bool(verdict.get("resolved")),
    },
    "analysis": {
        "wall_seconds": int("$ANALYSIS_WALL"),
        "session_id": analysis_run.get("analysis_session_id"),
        "classification": analysis_meta.get("classification"),
        "valid_trial": analysis_meta.get("valid_trial"),
        "summary": analysis_meta.get("summary"),
    },
}
(results / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
PY

log "rendering human-readable summary"
python3 "$EXAMPLE_DIR/metrics/summarize_run.py" "$RESULTS"

log "rendering HTML report"
python3 "$EXAMPLE_DIR/metrics/render_html.py" "$RESULTS"

log "done, results under $RESULTS/"
log "  outcome:            $RESULTS/verdict-$( [ "$RESOLVED" = "true" ] && echo resolved || echo unresolved ).md"
log "  visual report:      $RESULTS/verdict.html (open in a browser)"
log "  analysis:           $RESULTS/analysis/ANALYSIS.md ($ANALYSIS_CLASSIFICATION)"
log "  structured metrics: python3 $EXAMPLE_DIR/metrics/extract_metrics.py $RESULTS"
