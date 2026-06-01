The agent is the Amplifier CLI. Each scenario is ONE continuous
conversation: the first call starts a session, and every follow-up MUST
resume that same session.

## First message (starts a new session)

    amplifier run "<your message>" --output-format json

The response is JSON. Capture two fields:
  - `session_id` -- you MUST reuse this for every follow-up.
  - `response`   -- the agent's reply text.

## Follow-up messages (resume the SAME session)

    amplifier run --resume <session_id> "<your message>" --output-format json

The resumed call returns the same `session_id` and a session that remembers
all earlier turns. Use the captured id for every message after the first.

## Continuity is mandatory

A scenario is one conversation, not a series of fresh starts. Two failure
modes silently invalidate the run -- avoid both:

- Do NOT run `amplifier run "<msg>"` WITHOUT `--resume` for a follow-up.
  That starts a brand-new session with no memory of the earlier turns.
- Do NOT concatenate earlier messages into one new prompt. Send only the
  new message and let `--resume` carry the history.

Watch for signs that continuity broke: the agent re-introduces itself, asks
for something you already told it, or replies as if earlier turns never
happened. If you see that, you are spawning fresh sessions -- stop, confirm
you captured `session_id` from the first response, and resume that exact id
before sending anything else.

## Output format

Always pass `--output-format json`. The default text mode includes a TUI
banner, token usage footer, and thinking blocks that bloat your context and
add nothing useful.

## If a task needs a mode or a gated action

This `--resume` flow works because the plain foundation agent has no
interactive mode and no confirmation gate. It does NOT cover two cases:

- Activating a mode (e.g. `/evaluation`). Single-shot `amplifier run` does
  not parse slash commands, so a mode typed as a prompt never activates.
- Clearing a "warn" confirmation gate. Each `amplifier run --resume` is a
  fresh process, and the gate's "retry proceeds" state is process-scoped,
  so the retry is denied again every turn.

If a task ever requires either, do NOT use `amplifier run --resume`.
Instead drive ONE long-lived interactive TUI, kept alive across your
separate exec calls with `tmux`, and send every message into that same
session. The pattern (the `amplifier-evalbundle` agent uses this for its
`/evaluation` mode):

1. Start the agent once in a detached tmux session named `agent`:

       tmux kill-server 2>/dev/null; tmux new-session -d -s agent -x 220 -y 50 'cd /workspace && amplifier'

   The TUI is slow to start (allow 15-20 seconds). Poll until the input
   prompt `>` appears before sending anything:

       tmux capture-pane -p -t agent

   A warning that the terminal does not support cursor position requests
   (CPR) is harmless; ignore it.

2. Activate the mode by sending its slash command into the same session:

       tmux send-keys -t agent '/<mode>' Enter

   Wait a few seconds, capture again, and confirm a `Mode: <mode>` line
   appears and the prompt indicator changes to `[<mode>]>`. If the prompt
   does not change, the mode is NOT active and the run is invalid.

3. Send each message into the same session:

       tmux send-keys -t agent '<your message>' Enter

   Responses take 20-60 seconds. Poll until the `[<mode>]>` prompt returns
   with no `Thinking...` spinner, which means the reply is complete:

       tmux capture-pane -p -t agent

   To read a long reply that scrolled off-screen, capture scrollback too:

       tmux capture-pane -p -t agent -S -400

   For a message with tricky quoting (quotes, newlines), write it to a file
   and type it from there instead of inlining it:

       echo '<your message>' > /tmp/msg.txt
       tmux send-keys -t agent "$(cat /tmp/msg.txt)" Enter

4. Continuity: every follow-up MUST go to the SAME `tmux ... -t agent`
   session. Do NOT relaunch `amplifier`, do NOT start a second tmux
   session, and do NOT fall back to `amplifier run` -- each starts a fresh,
   memoryless session and silently breaks the conversation. One scenario =
   one tmux `agent` session from start to finish; the `[<mode>]>` prompt
   staying put and the agent remembering earlier turns confirm you are
   still in it.
