#!/usr/bin/env bash
# Example 01: Foundation Explorer Agent Removal (new-library version).
#
# Runs the explorer-removal A/B eval through the amplifier_evaluation harness.
# Stands up TWO independent Gitea mirror repos of amplifier-foundation --
#   admin/amplifier-foundation-with-explorer     (foundation as-is)
#   admin/amplifier-foundation-without-explorer  (explorer agent + all its
#                                                 delegation-guidance refs removed)
# -- each carrying its state on `main`, then hands off to harness.py which runs
# one trial per variant and writes the root-context metric comparison.
#
# Two separate repos (not two branches of one repo) so the variants never
# conflict and both resolve cleanly under Amplifier's default-branch
# (`main`) re-resolution at session start.
#
# Idempotent: re-running refreshes the mirrors and writes a fresh dated run.
#
# Usage:
#   ./run.sh
#
# Environment overrides:
#   FOUNDATION_GIT     git source to mirror (default: upstream GitHub). Point at
#                      a local checkout to test local foundation changes.
#   AMPLIFIER_GITEA_ID pick a specific gitea instance instead of the first/new
#   ANTHROPIC_API_KEY  required; falls back to ~/.amplifier/keys.env
#
# Prerequisites:
#   amplifier-digital-twin, amplifier-gitea, git, python3, docker on PATH
#   Docker daemon running
#   amplifier_evaluation importable (the bundle .venv is auto-activated if present)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
FOUNDATION_GIT="${FOUNDATION_GIT:-https://github.com/microsoft/amplifier-foundation}"
REPO_WITH="amplifier-foundation-with-explorer"
REPO_WITHOUT="amplifier-foundation-without-explorer"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

# ---- 0. preflight --------------------------------------------------------
log "preflight checks"
command -v amplifier-digital-twin >/dev/null || die "amplifier-digital-twin not on PATH"
command -v amplifier-gitea >/dev/null || die "amplifier-gitea not on PATH"
command -v git >/dev/null || die "git not on PATH"
command -v python3 >/dev/null || die "python3 not on PATH"
command -v docker >/dev/null || die "docker not on PATH"
docker info >/dev/null 2>&1 || die "Docker is not running"

# Activate the bundle venv so `import amplifier_evaluation` resolves.
if [ -f "$BUNDLE_ROOT/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    . "$BUNDLE_ROOT/.venv/bin/activate"
fi
python3 -c "import amplifier_evaluation" 2>/dev/null \
    || die "amplifier_evaluation not importable; activate the bundle .venv or 'uv pip install -e .' in $BUNDLE_ROOT"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f "$HOME/.amplifier/keys.env" ]; then
    set -a; . "$HOME/.amplifier/keys.env"; set +a
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"

# ---- 1. gitea: discover, create, or start -------------------------------
log "ensuring a Gitea instance is running"
GITEA_ID="${AMPLIFIER_GITEA_ID:-}"
if [ -z "$GITEA_ID" ]; then
    GITEA_ID="$(amplifier-gitea list | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')"
fi
if [ -z "$GITEA_ID" ]; then
    log "no gitea instance, creating one on port 10110"
    GITEA_ID="$(amplifier-gitea create --port 10110 | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
fi
STATUS_JSON="$(amplifier-gitea status "$GITEA_ID")"
RUNNING="$(echo "$STATUS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["container_running"])')"
if [ "$RUNNING" != "True" ]; then
    log "starting stopped gitea container amplifier-gitea-$GITEA_ID"
    docker start "amplifier-gitea-$GITEA_ID" >/dev/null
    sleep 4
fi
GITEA_PORT="$(echo "$STATUS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["port"])')"
GITEA_TOKEN="$(amplifier-gitea token "$GITEA_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
GITEA_URL="http://localhost:$GITEA_PORT"
log "gitea: $GITEA_URL  id=$GITEA_ID"

# ---- 2. build the two foundation mirror repos ----------------------------
ensure_repo() {
    local name="$1" code
    code="$(curl -sS -H "Authorization: token $GITEA_TOKEN" \
        "$GITEA_URL/api/v1/repos/admin/$name" -o /dev/null -w '%{http_code}')"
    if [ "$code" != "200" ]; then
        log "creating admin/$name"
        curl -sS -X POST "$GITEA_URL/api/v1/admin/users/admin/repos" \
            -H "Authorization: token $GITEA_TOKEN" -H "Content-Type: application/json" \
            -d "{\"name\":\"$name\",\"default_branch\":\"main\",\"auto_init\":false}" -o /dev/null
    fi
}
push_main() {  # repo
    git -c credential.helper= push --force \
        "http://admin:$GITEA_TOKEN@localhost:$GITEA_PORT/admin/$1.git" \
        "HEAD:refs/heads/main" >/dev/null 2>&1
}

log "mirroring foundation -> $REPO_WITH and $REPO_WITHOUT"
ensure_repo "$REPO_WITH"
ensure_repo "$REPO_WITHOUT"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
# Full history (NOT --depth 1): Gitea rejects pushing a shallow clone
# ("shallow update not allowed"). amplifier-foundation is small, so this is cheap.
git clone --quiet "$FOUNDATION_GIT" "$WORK/found"
(
    cd "$WORK/found"
    # WITH: deploy foundation as-is to the with-explorer mirror's main.
    push_main "$REPO_WITH"

    # WITHOUT: clean removal of the explorer agent and every delegation-guidance
    # reference to it -- no substitute agent named in its place.
    rm -f agents/explorer.md
    sed -i '/^    - foundation:explorer$/d' bundle.md
    sed -i '/foundation:explorer/d' \
        context/agents/delegation-instructions.md \
        context/agents/multi-agent-patterns.md
    git -c user.email=eval@local -c user.name=eval add -A
    git -c user.email=eval@local -c user.name=eval commit --quiet \
        -m "remove foundation:explorer agent and all delegation-guidance references"
    push_main "$REPO_WITHOUT"
)
log "mirrors ready"

# ---- 3. run the custom A/B harness --------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT_DIR="$HERE/results/$RUN_ID"
mkdir -p "$OUTPUT_DIR"

log "running harness, output=$OUTPUT_DIR"
python3 "$HERE/harness.py" \
    --output "$OUTPUT_DIR" \
    --gitea-url "$GITEA_URL" \
    --gitea-token "$GITEA_TOKEN" \
    --with-repo "$REPO_WITH" \
    --without-repo "$REPO_WITHOUT"
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - with-explorer/  without-explorer/  -- per-trial state.json, ai_user.json, extraction/, grader/"
log "  - comparison.md / comparison.json    -- root-context A/B metric diff"
log "  - summary.json                       -- per-trial state + grader score"
exit "$HARNESS_EXIT"
