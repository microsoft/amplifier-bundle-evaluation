#!/usr/bin/env bash
# Example 01: Foundation Explorer Agent Removal (orchestrator).
#
# End-to-end runner: stands up Gitea + mirrors, launches both DTUs, runs the
# eval prompt in each, captures stdout + events.jsonl + meta.json.
#
# Idempotent. Re-running creates a fresh dated results/<YYYY-MM-DD>/ directory.
#
# Prerequisites (script aborts with a clear message if missing):
#   - amplifier-gitea, amplifier-digital-twin on PATH
#   - Docker daemon running
#   - ANTHROPIC_API_KEY in env (or in ~/.amplifier/keys.env)
#
# Run from this directory:
#     ./run.sh

set -euo pipefail

EXAMPLE_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
RESULTS="$EXAMPLE_DIR/results/$DATE"
PROMPT='Explore /work/agent-framework. Explain how it handles switching between AI providers (e.g. OpenAI vs Anthropic). Include code references in file:line form as evidence for each claim.'

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-gitea >/dev/null || die "amplifier-gitea not on PATH"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
command -v gh >/dev/null || die "gh not on PATH"
command -v git >/dev/null || die "git not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"
[ -n "${ANTHROPIC_API_KEY:-}" ] || {
    [ -f "$HOME/.amplifier/keys.env" ] && set -a && . "$HOME/.amplifier/keys.env" && set +a
}
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"

# ---- 1. gitea: reuse or create ------------------------------------------
log "ensuring a Gitea instance is running"
GITEA_LIST="$(amplifier-gitea list)"
GITEA_ID="$(echo "$GITEA_LIST" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')"
if [ -z "$GITEA_ID" ]; then
    log "no Gitea instance, creating one"
    GITEA_JSON="$(amplifier-gitea create --port 10110)"
    GITEA_ID="$(echo "$GITEA_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
fi
GITEA_PORT="$(amplifier-gitea status "$GITEA_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["port"])')"
RUNNING="$(amplifier-gitea status "$GITEA_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["container_running"])')"
if [ "$RUNNING" != "True" ]; then
    log "starting stopped Gitea container"
    docker start "amplifier-gitea-$GITEA_ID" >/dev/null
    sleep 4
fi
GITEA_TOKEN="$(amplifier-gitea token "$GITEA_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
GITEA_URL="http://localhost:$GITEA_PORT"
log "gitea: $GITEA_URL  id=$GITEA_ID"

# ---- 2. mirror upstream repos to gitea (idempotent) ---------------------
mirror_if_needed() {
    local repo="$1"
    local exists
    exists="$(curl -sS -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/repos/admin/$repo" -o /dev/null -w '%{http_code}')"
    if [ "$exists" = "200" ]; then
        log "  $repo already mirrored"
    else
        log "  mirroring $repo"
        amplifier-gitea mirror-from-github "$GITEA_ID" \
            --github-repo "https://github.com/microsoft/$repo" \
            --github-token "$(gh auth token)" \
            --no-issues --no-prs --no-labels >/dev/null
    fi
}
log "ensuring mirrors"
mirror_if_needed amplifier-foundation
mirror_if_needed amplifier-bundle-context-intelligence

# ---- 3. build remove-explorer branch in gitea (no workspace impact) ----
#
# The AFTER variant of this eval needs a foundation install with the
# foundation:explorer agent and ALL its delegation-guidance references
# stripped, no substitute agent named in their place. We build that
# branch in a throwaway clone of the Gitea mirror, push it back to
# Gitea, and discard the temp clone.
#
# Strategy: clean removal. Every line in the active delegation guidance
# that mentions foundation:explorer is deleted entirely. No replacement,
# no orphans.
#
# The user's workspace amplifier-foundation submodule is never touched.
build_remove_explorer_in_gitea() {
    log "building remove-explorer branch in gitea mirror"
    local tmp
    tmp="$(mktemp -d)"
    (
        cd "$tmp"
        git clone --quiet \
            "http://admin:$GITEA_TOKEN@localhost:$GITEA_PORT/admin/amplifier-foundation.git" \
            foundation
        cd foundation

        # Branch off whatever Gitea's main currently points to (which is
        # what the BEFORE arm will install). Build remove-explorer from
        # the same parent so before/after share a parent commit.
        git checkout main --quiet
        git checkout -b remove-explorer --quiet

        # 1. Delete the agent file outright.
        rm -f agents/explorer.md

        # 2. Drop the explorer entry from the bundle's agents.include list.
        sed -i '/^    - foundation:explorer$/d' bundle.md

        # 3. Delete EVERY line referencing foundation:explorer from the
        #    active delegation guidance. No substitute agent is named.
        sed -i '/foundation:explorer/d' \
            context/agents/delegation-instructions.md \
            context/agents/multi-agent-patterns.md

        git -c user.email=eval@local -c user.name=eval add -A
        git -c user.email=eval@local -c user.name=eval commit -q \
            -m "remove foundation:explorer agent and all delegation-guidance references

Auto-generated by amplifier-bundle-evaluation/examples/01-explorer-removal/run.sh."

        git push origin remove-explorer --force --quiet
    )
    rm -rf "$tmp"
}
build_remove_explorer_in_gitea

# ---- 4. launch both DTUs and run the prompt -----------------------------
launch_and_run() {
    local side="$1"     # "before" | "after"
    local profile="$EXAMPLE_DIR/profiles/$side.yaml"
    local dtu="eval01-$side"
    local out_dir="$RESULTS/$side/run-1"
    mkdir -p "$out_dir"

    log "[$side] destroying any prior DTU named $dtu"
    amplifier-digital-twin destroy "$dtu" >/dev/null 2>&1 || true

    log "[$side] launching DTU"
    amplifier-digital-twin launch "$profile" \
        --var "GITEA_URL=$GITEA_URL" \
        --var "GITEA_TOKEN=$GITEA_TOKEN" \
        --name "$dtu" >/dev/null

    log "[$side] running eval prompt (single turn)"
    local start end exit_code
    start=$(date +%s)
    amplifier-digital-twin exec "$dtu" -- bash -c \
        "export PATH=/root/.local/bin:\$PATH && cd /work && amplifier run \"$PROMPT\" 2>&1" \
        > "$out_dir/exec.json" 2>&1
    exit_code=$?
    end=$(date +%s)
    local wall=$((end - start))

    # extract stdout + session id
    local sid foundation_sha agent_framework_sha
    python3 -c "import json; d=json.load(open('$out_dir/exec.json')); open('$out_dir/stdout.txt','w').write(d['stdout'])"
    sid="$(grep -oE 'Session ID: [a-f0-9-]{36}' "$out_dir/stdout.txt" | head -1 | awk '{print $3}')"
    [ -n "$sid" ] || die "[$side] could not find Session ID in stdout"

    # Resolve the foundation SHA the DTU actually installed by querying the
    # Gitea mirror. Never touch the user's workspace submodule.
    local fbranch
    fbranch="$( [ "$side" = before ] && echo main || echo remove-explorer )"
    foundation_sha="$(git ls-remote \
        "http://admin:$GITEA_TOKEN@localhost:$GITEA_PORT/admin/amplifier-foundation.git" \
        "refs/heads/$fbranch" | awk '{print $1}')"
    agent_framework_sha="$(amplifier-digital-twin exec "$dtu" -- bash -c 'cd /work/agent-framework && git rev-parse HEAD' \
        | python3 -c 'import json,sys; print(json.load(sys.stdin)["stdout"].strip())')"

    log "[$side] pulling session dir (id=$sid)"
    amplifier-digital-twin file-pull "$dtu" -r \
        "/root/.amplifier/projects/-work/sessions/" "$out_dir/sessions/" >/dev/null

    cat > "$out_dir/meta.json" <<META
{
  "example": "01-explorer-removal",
  "side": "$side",
  "run": 1,
  "session_id": "$sid",
  "wall_seconds": $wall,
  "exit_code": $exit_code,
  "dtu_id": "$dtu",
  "profile": "profiles/$side.yaml",
  "foundation_sha": "$foundation_sha",
  "foundation_branch": "$( [ "$side" = before ] && echo main || echo remove-explorer )",
  "agent_framework_sha": "$agent_framework_sha",
  "agent_framework_repo": "microsoft/agent-framework",
  "prompt": $(printf '%s' "$PROMPT" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read()))'),
  "events_jsonl": "sessions/sessions/$sid/events.jsonl",
  "transcript_jsonl": "sessions/sessions/$sid/transcript.jsonl",
  "ran_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
META
    log "[$side] captured wall=${wall}s exit=$exit_code"
}

launch_and_run before
launch_and_run after

log "done, results captured under $RESULTS/"
log "to extract structured metrics: python3 $EXAMPLE_DIR/metrics/extract_metrics.py $RESULTS/<side>/run-1/"
