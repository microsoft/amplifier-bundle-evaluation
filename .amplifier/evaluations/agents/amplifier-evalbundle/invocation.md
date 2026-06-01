The agent is the Amplifier CLI with the amplifier-foundation and
amplifier-bundle-evaluation bundles composed.

The evaluation mode (`/evaluation`) only activates from a real interactive
session. The single-shot `amplifier run` command cannot clear the mode's
confirmation gate across separate invocations, so you MUST drive one
long-lived interactive TUI and send every message into that same session.
You keep the one TUI alive across your separate `exec` calls with `tmux`.

## Start the agent once (persistent tmux session)

Launch the TUI inside a detached tmux session named `agent`:

    tmux kill-server 2>/dev/null; tmux new-session -d -s agent -x 220 -y 50 'cd /workspace && amplifier'

The TUI is slow to start (allow 15-20 seconds). Poll the screen until the
input prompt `>` appears before sending anything:

    tmux capture-pane -p -t agent

You will see a session banner that ends in a `>` prompt. A warning that the
terminal does not support cursor position requests (CPR) is harmless; ignore
it.

## Activate the evaluation mode first (required)

Send the slash command into the same session:

    tmux send-keys -t agent '/evaluation' Enter

Wait a few seconds, then capture again. Confirm a line beginning
`Mode: evaluation` appears and the prompt indicator changes to
`[evaluation]>`. We always want to test this mode, so this is the required
first step. If the prompt does not change to `[evaluation]>`, the mode is
NOT active and the evaluation is invalid.

## Send each message into the same session

Type a message and submit it with Enter:

    tmux send-keys -t agent '<your message>' Enter

Responses take 20-60 seconds. Poll the screen until the `[evaluation]>`
prompt returns at the bottom with no `Thinking...` spinner, which means the
reply is complete:

    tmux capture-pane -p -t agent

To read a long reply that scrolled past the visible screen, capture
scrollback as well:

    tmux capture-pane -p -t agent -S -400

For a message with tricky quoting (quotes, newlines), write it to a file and
type it from there instead of inlining it:

    echo '<your message>' > /tmp/msg.txt
    tmux send-keys -t agent "$(cat /tmp/msg.txt)" Enter

## Continuity (critical)

Every follow-up MUST go to the SAME `tmux ... -t agent` session. Do NOT run
`amplifier` again, do NOT start a second tmux session, and do NOT use
`amplifier run` for follow-ups. Each of those starts a fresh agent session
with no memory and silently breaks the conversation -- the exact failure
this guide exists to prevent. One scenario = one tmux `agent` session from
start to finish. The `[evaluation]>` prompt staying put and the agent
remembering earlier turns are how you confirm you are still in the same
session.
