#!/usr/bin/env bash
# .amplifier/evaluations/run.sh
#
# Wrapper that runs the bundle's meta-evaluations via the amplifier_evaluation
# harness. Discovers a running amplifier-gitea instance, deploys the local
# branch HEAD into the mirror AS the `main` branch (simulating the changes
# being merged and active), and threads GITEA_URL / GITEA_TOKEN /
# EVAL_BUNDLE_REF to every trial via the harness `--launch-var` flag.
#
# Why deploy as `main`: at session start Amplifier re-composes its app bundles
# by cloning the bundle's DEFAULT branch (`main`). If the mirror only carries a
# feature branch, that clone fails ("Remote branch main not found"), the
# evaluation bundle drops out of composition, and `/evaluation` mode silently
# disappears. Publishing the local HEAD as `main` makes the agent under test
# behave exactly as if these changes were already deployed.
#
# Usage:
#   ./run.sh                # both evals (01 + 02)
#   ./run.sh 02             # just one eval by id prefix
#   ./run.sh 01 02 03       # explicit list
#
# Environment overrides:
#   EVAL_BUNDLE_REF   LOCAL git ref whose HEAD to deploy (default: the
#                     currently checked-out branch). Its HEAD is published
#                     into the Gitea mirror AS `main`, so the agent under
#                     test composes it exactly as a deployed/active bundle.
#   AMPLIFIER_GITEA_ID
#                     pick a specific gitea instance instead of the first
#   ANTHROPIC_API_KEY required; falls back to ~/.amplifier/keys.env
#   MAX_PARALLEL      passed to the harness; default 1 (these evals are
#                     resource-heavy and should not run concurrently)
#   TRIALS_PER_PAIR   default 1
#
# Prerequisites:
#   amplifier-digital-twin, amplifier-gitea, git, python3, docker on PATH
#   Docker daemon running
#   amplifier_evaluation package installed in the active Python env (use the
#   bundle's .venv or `uv pip install -e .` against the bundle root)

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_ROOT="$(cd "$HERE/../.." && pwd)"
RESULTS_ROOT="$HERE/results"

# Local ref whose HEAD gets deployed into the mirror as `main`. Defaults to the
# branch currently checked out in the bundle repo.
EVAL_BUNDLE_REF="${EVAL_BUNDLE_REF:-$(cd "$BUNDLE_ROOT" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)}"
# The branch the agent under test composes from. Always `main` so the bundle
# resolves like a deployed/active default branch.
DEPLOY_BRANCH="main"
MAX_PARALLEL="${MAX_PARALLEL:-1}"
TRIALS_PER_PAIR="${TRIALS_PER_PAIR:-1}"
REPO_NAME="amplifier-bundle-evaluation"

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

python3 -c "import amplifier_evaluation" 2>/dev/null \
    || die "amplifier_evaluation not importable; activate the bundle .venv or 'uv pip install -e .' in $BUNDLE_ROOT"

if [ -z "${ANTHROPIC_API_KEY:-}" ] && [ -f "$HOME/.amplifier/keys.env" ]; then
    set -a; . "$HOME/.amplifier/keys.env"; set +a
fi
[ -n "${ANTHROPIC_API_KEY:-}" ] || die "ANTHROPIC_API_KEY not set and not in ~/.amplifier/keys.env"

# ---- 1. selection --------------------------------------------------------
ALL_TASKS=("01-evaluate-amplifier-bundle" "02-industry-benchmark-routing" "03-cli-run-benchmark" "04-build-clawbench-nanoclaw-harness")
SELECTED=()
if [ "$#" -eq 0 ]; then
    SELECTED=("${ALL_TASKS[@]}")
else
    for arg in "$@"; do
        case "$arg" in
            -h|--help)
                sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
                exit 0 ;;
        esac
        match=""
        for t in "${ALL_TASKS[@]}"; do
            if [[ "$t" == "$arg" || "$t" == "$arg-"* ]]; then
                match="$t"; break
            fi
        done
        [ -n "$match" ] || die "unknown task '$arg' (known: ${ALL_TASKS[*]})"
        SELECTED+=("$match")
    done
fi

# Both evals exercise the same agent: amplifier with amplifier-foundation
# and amplifier-bundle-evaluation composed. The agent under test is the
# bundle's /evaluation mode in both cases; the harness, scoring, and
# fixtures differ per task.
AGENT_ID="amplifier-evalbundle"

log "selection: ${SELECTED[*]}"

# ---- 2. gitea: discover and start ---------------------------------------
log "discovering gitea instance"
GITEA_ID="${AMPLIFIER_GITEA_ID:-}"
if [ -z "$GITEA_ID" ]; then
    GITEA_ID="$(amplifier-gitea list | python3 -c \
        'import json,sys; d=json.load(sys.stdin); print(d[0]["id"] if d else "")')"
fi
[ -n "$GITEA_ID" ] || die "no amplifier-gitea instance found. Create one with 'amplifier-gitea create --port 10110'."

STATUS_JSON="$(amplifier-gitea status "$GITEA_ID")"
RUNNING="$(echo "$STATUS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["container_running"])')"
if [ "$RUNNING" != "True" ]; then
    log "starting stopped gitea container amplifier-gitea-$GITEA_ID"
    docker start "amplifier-gitea-$GITEA_ID" >/dev/null
    sleep 3
fi
GITEA_PORT="$(echo "$STATUS_JSON" | python3 -c 'import json,sys; print(json.load(sys.stdin)["port"])')"
GITEA_TOKEN="$(amplifier-gitea token "$GITEA_ID" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
GITEA_URL="http://localhost:$GITEA_PORT"
log "gitea: $GITEA_URL  id=$GITEA_ID"

# ---- 3. ensure repo exists in gitea, deploy working-tree snapshot -------
EXISTS="$(curl -sS -H "Authorization: token $GITEA_TOKEN" \
    "$GITEA_URL/api/v1/repos/admin/$REPO_NAME" -o /dev/null -w '%{http_code}')"
if [ "$EXISTS" != "200" ]; then
    log "creating admin/$REPO_NAME on gitea"
    curl -sS -X POST "$GITEA_URL/api/v1/admin/users/admin/repos" \
        -H "Authorization: token $GITEA_TOKEN" -H "Content-Type: application/json" \
        -d "{\"name\":\"$REPO_NAME\",\"default_branch\":\"main\",\"auto_init\":false}" \
        -o /dev/null
fi

# Deploy the developer's exact WORKING TREE (committed + staged + unstaged +
# untracked + deletions) into the mirror as `main`, WITHOUT committing anything
# in the user's repo. We clone the bundle into a throwaway snapshot dir, overlay
# the working-tree state there, make a single throwaway commit IN THE SNAPSHOT,
# and force-push that to gitea/main. The user's repo, index, and HEAD are never
# touched. (Method mirrors the amplifier-tester setup-digital-twin snapshot
# flow.) This is what lets the agent under test compose/clone the bundle exactly
# as if the local changes were merged and deployed -- no commit required.
log "deploying working-tree snapshot of $BUNDLE_ROOT into gitea as '$DEPLOY_BRANCH' (no commit to your repo)"
command -v rsync >/dev/null || die "rsync not on PATH (needed for the snapshot deploy)"
SNAP_PARENT="$(mktemp -d)"
SNAP_DIR="$SNAP_PARENT/$REPO_NAME"
trap 'rm -rf "$SNAP_PARENT"' EXIT
git clone --local --no-hardlinks "$BUNDLE_ROOT" "$SNAP_DIR" >/dev/null 2>&1 \
    || die "failed to clone working-tree snapshot from $BUNDLE_ROOT"
# Overlay staged + unstaged + untracked (non-ignored) files from the working tree.
( cd "$BUNDLE_ROOT" && git ls-files -z --cached --modified --others --exclude-standard ) \
    | rsync -a --files-from=- --from0 "$BUNDLE_ROOT/" "$SNAP_DIR/"
# Mirror tracked-file deletions from the working tree into the snapshot.
( cd "$BUNDLE_ROOT" && git ls-files -z --deleted ) \
    | ( cd "$SNAP_DIR" && xargs -0 --no-run-if-empty rm -f )
(
    cd "$SNAP_DIR"
    git -c user.email=dtu@local -c user.name="DTU Snapshot" add -A
    git -c user.email=dtu@local -c user.name="DTU Snapshot" \
        commit --allow-empty -q -m "DTU snapshot of working tree" >/dev/null 2>&1
    git -c credential.helper= push --force \
        "http://admin:$GITEA_TOKEN@localhost:$GITEA_PORT/admin/$REPO_NAME.git" \
        "HEAD:refs/heads/$DEPLOY_BRANCH" >/dev/null 2>&1
)
EVAL_SHA="$(cd "$SNAP_DIR" && git rev-parse HEAD)"
rm -rf "$SNAP_PARENT"
trap - EXIT
log "deployed working-tree snapshot ($EVAL_SHA) as gitea/$DEPLOY_BRANCH"

# ---- 4. run the harness -------------------------------------------------
RUN_ID="$(date -u +%Y%m%dT%H%M%SZ)-$(head -c 4 /dev/urandom | xxd -p)"
OUTPUT_DIR="$RESULTS_ROOT/$RUN_ID"
mkdir -p "$OUTPUT_DIR"

# Build the --pair flags from the selection.
PAIR_FLAGS=()
for t in "${SELECTED[@]}"; do
    PAIR_FLAGS+=("--pair" "$AGENT_ID:$t")
done

log "running harness, output=$OUTPUT_DIR"
log "selection: $(printf '%s ' "${PAIR_FLAGS[@]}")"

python3 -m amplifier_evaluation run \
    --agents-dir "$HERE/agents" \
    --tasks-dir  "$HERE/tasks" \
    --output-dir "$RESULTS_ROOT" \
    --run-id "$RUN_ID" \
    --max-parallel "$MAX_PARALLEL" \
    --trials-per-pair "$TRIALS_PER_PAIR" \
    "${PAIR_FLAGS[@]}" \
    --launch-var "GITEA_URL=$GITEA_URL" \
    --launch-var "GITEA_TOKEN=$GITEA_TOKEN" \
    --launch-var "EVAL_BUNDLE_REF=$DEPLOY_BRANCH" \
    --verbose
HARNESS_EXIT=$?

log "harness exit: $HARNESS_EXIT"
log "results: $OUTPUT_DIR"
log "  - run.json     -- run plan + launch_variables (secrets redacted)"
log "  - summary.json -- per-trial state, score, elapsed_s"
log "  - trials/      -- per-trial state.json, install.log, ai_user.json, grader/, extraction/"

exit "$HARNESS_EXIT"
