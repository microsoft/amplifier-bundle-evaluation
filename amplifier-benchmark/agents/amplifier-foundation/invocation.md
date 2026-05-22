The agent is the Amplifier CLI.

## First message (starts a new session)

    amplifier run "<your message>" --output-format json

The response is JSON. Capture `session_id` for follow-ups.

## Follow-up messages (resume the same session)

    amplifier run --resume <session_id> "<your message>" --output-format json

Always pass `--output-format json`. The default text mode includes a TUI
banner, token usage footer, and thinking blocks that bloat your context and
add nothing useful.

## What "broken" looks like

- The command exits non-zero.
- The output is not valid JSON.
- The command hangs past a generous timeout (say, 10 minutes).

In any of those cases, conclude with `verdict=failure`.

## What you do NOT do

You are roleplaying a user. Do not read the agent's session files, peek at
its workspace, or run anything that is not "talk to the CLI." Verification
of side effects is somebody else's job.
