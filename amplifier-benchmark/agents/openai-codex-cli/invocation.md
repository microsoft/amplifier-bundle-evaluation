The agent is the `codex` CLI from the `@openai/codex` npm package. The
container has `CODEX_UNSAFE_ALLOW_NO_SANDBOX=1` set in `/root/.bashrc` so
it can run unsandboxed inside the Digital Twin Universe.

## One-shot per message

Codex runs as a one-shot per turn via `codex exec`:

    codex exec "<your message>"

The CLI prints the agent's response to stdout and exits. Capture the
response from stdout. Pass `--skip-git-repo-check` if codex complains about
not being inside a git repository.

## Multi-turn conversations

`codex exec` does NOT persist conversation context between separate
invocations by default. Each `codex exec` call is a fresh session.

For simple scenarios where each message is independent (greeting, asking a
factual question), run `codex exec` per turn and don't worry about
continuity.

If a scenario genuinely requires shared context (e.g. "now improve the
function you just wrote"), include the necessary prior context in the
message text itself, or use `codex resume --last` which picks up the most
recent rollout.
