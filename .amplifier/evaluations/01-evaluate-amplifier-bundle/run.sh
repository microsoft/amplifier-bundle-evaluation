#!/usr/bin/env bash
# Evaluation 01: Evaluate the evaluation bundle.
#
# Single-script orchestrator. Launches an outer DTU with the
# evaluation bundle composed in, mounts the crusty-reminder bundle
# as the inner artifact at /work/amplifier-bundle-crusty-reminder/,
# feeds the agent under test a realistic "validate this bundle"
# prompt, and captures everything for analysis.
#
# What we measure is what the agent produces, not whether the
# produced harness actually runs (that's a deferred Phase 3).
#
# Idempotent. Re-running creates a fresh dated results/<YYYY-MM-DD>/.
#
# Prerequisites:
#   - amplifier-digital-twin on PATH
#   - Docker daemon running on host
#   - ANTHROPIC_API_KEY in env (or in ~/.amplifier/keys.env)
#
# Run from this directory:
#     ./run.sh

set -euo pipefail

EVAL_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
RESULTS="$EVAL_DIR/results/$DATE/run-1"
DTU_NAME="eval-outer"
PROMPT_PATH="$EVAL_DIR/prompt.md"

# The inner artifact source: the crusty-reminder bundle, co-located
# with this evaluation under inner-artifact/.
INNER_SRC="$EVAL_DIR/inner-artifact"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"
[ -d "$INNER_SRC" ] || die "inner artifact not found at $INNER_SRC"
[ -f "$PROMPT_PATH" ] || die "prompt.md missing"
[ -n "${ANTHROPIC_API_KEY:-}" ] || {
    [ -f "$HOME/.amplifier/keys.env" ] && set -a && . "$HOME/.amplifier/keys.env" && set +a
}
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"

mkdir -p "$RESULTS"

# ---- 1. stage on host: inner artifact AND prompt+runner -----------------
# file-push copies the source DIRECTORY into the destination, retaining
# the source basename. We stage everything under names that will land
# at the right paths once pushed.
HOST_STAGE="$(mktemp -d)"
trap 'rm -rf "$HOST_STAGE"' EXIT

# Inner artifact: stage as amplifier-bundle-crusty-reminder so it lands
# at /work/amplifier-bundle-crusty-reminder/ when pushed to /work/.
mkdir -p "$HOST_STAGE/amplifier-bundle-crusty-reminder"
cp -r "$INNER_SRC/." "$HOST_STAGE/amplifier-bundle-crusty-reminder/"

# Prompt + runner: stage as eval-stage so it lands at /root/eval-stage/
# when pushed to /root/. The runner reads /root/eval-stage/prompt.txt,
# invokes amplifier run, captures stdout+exit code, all inside the DTU.
mkdir -p "$HOST_STAGE/eval-stage"
cp "$PROMPT_PATH" "$HOST_STAGE/eval-stage/prompt.txt"
cat > "$HOST_STAGE/eval-stage/run-amplifier.sh" <<'INNER_EOF'
#!/usr/bin/env bash
# Runs inside the outer DTU. Reads prompt.txt, invokes amplifier run,
# writes stdout to log and the exit code to exit.
export PATH=/root/.local/bin:$PATH
cd /work
exec_rc=0
amplifier run "$(cat /root/eval-stage/prompt.txt)" 2>&1
exec_rc=$?
echo "$exec_rc" > /root/eval-stage/exit
INNER_EOF
chmod +x "$HOST_STAGE/eval-stage/run-amplifier.sh"

# ---- 2. outer DTU: destroy any prior, launch fresh ----------------------
log "destroying any prior outer DTU named $DTU_NAME"
amplifier-digital-twin destroy "$DTU_NAME" >/dev/null 2>&1 || true

log "launching outer DTU (this can take a few minutes)"
amplifier-digital-twin launch "$EVAL_DIR/profiles/outer.yaml" --name "$DTU_NAME" >/dev/null

# ---- 3. push staged files into outer DTU --------------------------------
log "pushing inner artifact to /work/amplifier-bundle-crusty-reminder/"
amplifier-digital-twin file-push "$DTU_NAME" \
    "$HOST_STAGE/amplifier-bundle-crusty-reminder" /work/ >/dev/null

log "pushing prompt + runner to /root/eval-stage/"
amplifier-digital-twin file-push "$DTU_NAME" \
    "$HOST_STAGE/eval-stage" /root/ >/dev/null

# Sanity check: inner artifact bundle.md is directly under that path,
# and the runner script is staged correctly.
amplifier-digital-twin exec "$DTU_NAME" -- bash -c '
test -f /work/amplifier-bundle-crusty-reminder/bundle.md || { echo "MISSING: bundle.md"; exit 1; }
test -f /root/eval-stage/prompt.txt || { echo "MISSING: prompt.txt"; exit 1; }
test -x /root/eval-stage/run-amplifier.sh || { echo "MISSING: run-amplifier.sh executable"; exit 1; }
echo OK
' | python3 -c '
import json, sys
d = json.load(sys.stdin)
out = d["stdout"].strip()
if "OK" not in out:
    raise SystemExit(f"stage push verification failed: {out}")
print("staged files verified")
'

# ---- 4. prepare output directory inside outer DTU -----------------------
amplifier-digital-twin exec "$DTU_NAME" -- bash -c 'mkdir -p /work/eval-output' >/dev/null

# ---- 5. feed the prompt to amplifier run (background + poll) ------------
# amplifier-digital-twin exec has an internal 600s timeout from the
# underlying subprocess.run(timeout=...). For an agent that may chew
# on a real evaluation design for 10-30 minutes, we run amplifier as a
# detached background process inside the DTU and poll for completion.
MAX_AGENT_SECONDS=2400   # 40 min ceiling so a wedged run still ends
POLL_SECONDS=60

log "starting amplifier run in background inside outer DTU"
# Spawn the runner with setsid + < /dev/null so it fully detaches from
# the exec session. Without setsid, killing the parent exec process
# (e.g. by a host-side timeout) propagates SIGHUP to the child and
# terminates the agent mid-run.
amplifier-digital-twin exec "$DTU_NAME" -- bash -c '
set -e
rm -f /root/eval-stage/log /root/eval-stage/exit /root/eval-stage/pid
setsid /root/eval-stage/run-amplifier.sh > /root/eval-stage/log 2>&1 < /dev/null &
echo $! > /root/eval-stage/pid
echo "started pid=$(cat /root/eval-stage/pid)"
' >/dev/null

start=$(date +%s)
log "polling every ${POLL_SECONDS}s (ceiling ${MAX_AGENT_SECONDS}s)"
while :; do
    now=$(date +%s)
    elapsed=$((now - start))
    done_check="$(amplifier-digital-twin exec "$DTU_NAME" -- bash -c \
        'test -f /root/eval-stage/exit && cat /root/eval-stage/exit || echo NOT_DONE' \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["stdout"].strip())')"
    if [ "$done_check" != "NOT_DONE" ]; then
        exit_code="$done_check"
        log "agent run finished after ${elapsed}s (inner exit=$exit_code)"
        break
    fi
    if [ "$elapsed" -ge "$MAX_AGENT_SECONDS" ]; then
        log "ceiling hit at ${elapsed}s, killing agent"
        amplifier-digital-twin exec "$DTU_NAME" -- bash -c \
            'kill -TERM $(cat /root/eval-stage/pid) 2>/dev/null; sleep 5; kill -KILL $(cat /root/eval-stage/pid) 2>/dev/null; echo killed' >/dev/null
        exit_code=124
        break
    fi
    log "  still running (${elapsed}s elapsed)"
    sleep "$POLL_SECONDS"
done
end=$(date +%s)
wall=$((end - start))

# Pull the captured log
amplifier-digital-twin file-pull "$DTU_NAME" /root/eval-stage/log "$RESULTS/stdout.txt" >/dev/null

# ---- 6. extract session id from stdout ----------------------------------
sid="$(grep -oE 'Session ID: [a-f0-9-]{36}' "$RESULTS/stdout.txt" | head -1 | awk '{print $3}')"
[ -n "$sid" ] || die "could not find Session ID in stdout (check $RESULTS/stdout.txt)"
log "session id: $sid"

# ---- 7. pull session dir out of outer DTU -------------------------------
log "pulling session dir"
rm -rf "$RESULTS/sessions"
amplifier-digital-twin file-pull "$DTU_NAME" -r \
    "/root/.amplifier/projects/-work/sessions/" "$RESULTS/sessions/" >/dev/null

# ---- 8. pull /work/eval-output/ (what the agent produced) ---------------
log "pulling /work/eval-output/ (produced artifacts)"
rm -rf "$RESULTS/produced"
amplifier-digital-twin file-pull "$DTU_NAME" -r \
    /work/eval-output/ "$RESULTS/produced/" >/dev/null 2>&1 || \
    log "  no produced directory to pull (agent may not have created /work/eval-output/)"

# ---- 9. write meta.json -------------------------------------------------
cat > "$RESULTS/meta.json" <<META
{
  "evaluation": "01-evaluate-amplifier-bundle",
  "run": 1,
  "session_id": "$sid",
  "wall_seconds": $wall,
  "exit_code": $exit_code,
  "dtu_id": "$DTU_NAME",
  "profile": "profiles/outer.yaml",
  "prompt_path": "prompt.md",
  "events_jsonl": "sessions/sessions/$sid/events.jsonl",
  "transcript_jsonl": "sessions/sessions/$sid/transcript.jsonl",
  "produced_dir": "produced",
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
META

# ---- 10. run metrics extraction + report -------------------------------
log "extracting metrics"
python3 "$EVAL_DIR/metrics/extract_metrics.py" "$RESULTS" > "$RESULTS/metrics.json"
python3 "$EVAL_DIR/metrics/extract_metrics.py" "$RESULTS" --report > "$RESULTS/report.md"

log "done. results in $RESULTS/"
log "report: $RESULTS/report.md"
