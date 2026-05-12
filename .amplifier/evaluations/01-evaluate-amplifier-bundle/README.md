# 01-evaluate-amplifier-bundle

A self-evaluation of `amplifier-bundle-evaluation`. Hands the bundle a
realistic user request — "I have a new bundle, help me validate it" —
and measures whether the agent it equips produces a useful evaluation
harness.

This lives under `.amplifier/evaluations/` because it is bundle-internal
dogfooding, not a user-facing template. Templates live in `examples/`.

## Layers

```
target          this bundle (amplifier-bundle-evaluation)
this evaluation .amplifier/evaluations/01-evaluate-amplifier-bundle/
agent-under-    Amplifier session running INSIDE an outer DTU,
test            with the evaluation bundle composed in
inner artifact  inner-artifact/ (the crusty-reminder bundle)
                the "new bundle" the user is asking about
```

The crusty-reminder bundle source lives at `inner-artifact/` inside
this directory. Everything for this evaluation is self-contained here.

## How it runs

```
host
  amplifier-digital-twin launch profiles/outer.yaml
  └── OUTER DTU (security.nesting=true)
        runs Incus + Docker + Amplifier with
        foundation + evaluation + DTU + Gitea bundles composed
        staged at /work/amplifier-bundle-crusty-reminder/
        staged at /root/eval-stage/{prompt.txt, run-amplifier.sh}

        nohup run-amplifier.sh > /root/eval-stage/log
        └── amplifier run "$(cat prompt.txt)"
              └── agent does whatever it does for this prompt
                  produces files under /work/eval-output/
```

The host polls every 60s for `/root/eval-stage/exit` to detect
completion. amplifier-digital-twin's exec command has an internal
600s subprocess timeout, which is why we detach with setsid instead
of running amplifier run in the foreground.

## Run it

```
./run.sh
```

Single script. Idempotent. Creates `results/<YYYY-MM-DD>/run-1/` with:

```
meta.json          run metadata (wall time, exit code, session id, SHAs)
stdout.txt         what amplifier run wrote to stdout inside the DTU
sessions/...       the Amplifier session dir pulled out of the DTU
                   (events.jsonl + transcript.jsonl)
produced/          /work/eval-output/ pulled out of the DTU —
                   the artifacts the agent actually wrote
metrics.json       structured presence-based metrics
report.md          human-readable report
```

## What it measures (v1 — presence-based)

Seven binary signals:

```
reached_evaluation_mode      did /evaluation activate?
session_completed            did the orchestrator finish cleanly?
produced_dir_present         did the agent write anything?
produced_profiles            is there a profile (yaml) under produced/?
produced_runner              is there a runner (sh)?
produced_metrics_script      is there a metrics extractor (py)?
references_inner_artifact    do produced files mention crusty-reminder?
```

No quality scoring yet. We measure that the agent did the shape of the
right thing; whether it did it WELL is a future rubric / LLM-as-judge
layer.

## Deferred (per "less is more")

These are not built yet. Each should land only if a real run reveals
the need:

```
- A/B comparison vs another bundle version
- Running the agent's produced harness end-to-end (nested-nested DTU)
- LLM-as-judge scoring of the produced files
- Multiple sample prompts to estimate variance
- A negative-control prompt where no implementation is expected
```

## Architecture decisions worth knowing

These came out of iterating to get the eval working end-to-end:

```
1. The outer DTU pulls all bundles directly from GitHub. The host
   does not run a Gitea. Gitea is only relevant inside the outer DTU,
   where the agent under test creates one if it decides to mirror the
   inner artifact.

2. All four bundles (foundation, evaluation, DTU, gitea) are added
   with --app. A bundle added without --app is registered but its
   includes/agents/modes do NOT compose into the running session.
   Verified empirically: /evaluation mode does not appear in /modes
   unless the evaluation bundle is --app.

3. amplifier-digital-twin file-push retains the source basename when
   pushing a directory. To land a directory at a specific path, stage
   it on host with the target basename, then push to the PARENT path.
   The host stage uses /tmp/<random>/amplifier-bundle-crusty-reminder/
   pushed to /work/.

4. amplifier-digital-twin exec has an internal 600s timeout. For
   long-running prompts, run amplifier in a setsid-detached background
   process inside the DTU and poll for an exit-code file. setsid
   prevents SIGHUP from the exec session killing the agent.

5. The prompt explicitly tells the agent "treat me as if I am asleep"
   so it does not stop mid-run to ask the user for confirmation.
   Without this, the agent activates /evaluation mode and waits for
   confirmation, then the non-interactive session ends in ~90s with
   nothing produced. With it, the agent runs to completion and
   produces real artifacts.
```
