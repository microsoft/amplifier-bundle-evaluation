# Driving amplifier-foundation

This agent is the Amplifier CLI with amplifier-foundation composed. The eval is
a SINGLE, non-interactive turn: hand the task message to `amplifier run` and let
it work to completion.

## IMPORTANT: the turn can take many minutes

A real task turn takes several minutes, and foundation may delegate to
sub-agents that take 10+ minutes. Do NOT run `amplifier run` as a single
blocking command -- it will hit a command timeout and you will wrongly conclude
failure. Instead launch it in the BACKGROUND with a completion sentinel and POLL
until it finishes.

## Step 1 -- launch in the background

Run the user's message verbatim as the quoted argument. Redirect output to a
file and write a sentinel when it exits:

```
cd /workspace && rm -f eval-run.out eval-run.done && \
nohup bash -lc 'PATH=/root/.local/bin:$PATH amplifier run "<the user's message>" > /workspace/eval-run.out 2>&1; echo "EXIT:$?" > /workspace/eval-run.done' >/dev/null 2>&1 &
echo launched
```

If the user's message contains a double quote, first write it to
`/workspace/eval-prompt.txt` and use `amplifier run "$(cat /workspace/eval-prompt.txt)"`.

## Step 2 -- poll until the sentinel appears

Repeat this check, sleeping ~30s between checks, for as long as it takes (be
patient -- up to ~25 minutes; delegation runs are slow):

```
if [ -f /workspace/eval-run.done ]; then echo "COMPLETE $(cat /workspace/eval-run.done)"; else echo RUNNING; tail -c 200 /workspace/eval-run.out 2>/dev/null; fi
```

Do NOT conclude while it still prints `RUNNING`. Keep polling. The run spawning
a sub-session is expected, not an error.

## Step 3 -- confirm the deliverable and conclude

Once you see `COMPLETE`, confirm the agent produced its deliverable (for this
eval, an `answer.txt` written into /workspace):

```
cat /workspace/eval-run.out; echo '--- answer.txt ---'; cat /workspace/answer.txt 2>/dev/null
```

Then conclude:

- verdict `success` -- the sentinel shows `EXIT:0` and the agent produced its
  deliverable (the answer file / edited files the task asked for)
- verdict `failure` -- the sentinel shows a non-zero exit, or the run errored
  with no deliverable

Put a short note about what was produced in your summary. Do NOT judge
correctness yourself -- the grader does that.
