# Driving amplifier-foundation

This agent is the Amplifier CLI with amplifier-foundation composed. The eval is
a SINGLE, non-interactive exploration turn.

## IMPORTANT: the turn can take many minutes

A real exploration turn takes several minutes, and when foundation delegates to
the `foundation:explorer` sub-agent it can take 10+ minutes. Do NOT run
`amplifier run` as a single blocking command -- it will hit a command timeout
and you will wrongly conclude failure. Instead launch it in the BACKGROUND with
a completion sentinel and POLL until it finishes.

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
a sub-session (you may see explorer activity) is expected, not an error.

## Step 3 -- read the answer and conclude

Once you see `COMPLETE`, read the full answer:

```
cat /workspace/eval-run.out
```

Then conclude:

- verdict `success` -- the sentinel shows `EXIT:0` and the output contains an
  exploration answer
- verdict `failure` -- the sentinel shows a non-zero exit, or the output is an
  error with no answer

Put the final answer text (or its tail) in your summary.
