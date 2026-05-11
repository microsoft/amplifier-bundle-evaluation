# Example 01: Foundation Explorer Agent Removal

A worked example of the evaluation bundle in use. Compares the `foundation:explorer` agent's contribution by running the same prompt against two Amplifier installs: one with the agent, one without.

Also serves as the prescribed template for new evaluation examples.

## Target of evaluation

The `foundation:explorer` agent in `amplifier-foundation`, the "deep local-context reconnaissance" specialist for multi-file exploration. We measure whether removing it changes outputs, resource cost, and delegation behavior on a real exploration task.

## Hypothesis

With the agent available, the root session delegates exploration to it. Without it, the root either does the work inline (consuming root context tokens) or improvises with less-suited agents. Expected signal: lower root-context tokens in the "before" run, different tool-call shape, possibly higher answer quality.

## Setup

```
Target repo:    microsoft/agent-framework
Pinned SHA:     recorded at run-time in results/<date>/meta.json
Cloned to:      /work/agent-framework inside the DTU
Bundles loaded: foundation, context-intelligence

Variants:
  before  →  amplifier-foundation @ main
  after   →  amplifier-foundation @ remove-explorer   (see change.md)

Sample count: 1 each side for v1.
```

Single-turn user prompt, identical in both runs:

```
Explore /work/agent-framework. Explain how it handles switching
between AI providers (e.g. OpenAI vs Anthropic). Include code
references in file:line form as evidence for each claim.
```

## Measurements

Captured per run from `events.jsonl` and stdout:

```
Quantitative:  root-context tokens, wall time, root tool-call count,
               delegate() targets attempted, exit code
Qualitative:   final answer text + all file:line citations
```

`metrics/extract_metrics.py` reads a captured run directory and emits the structured metrics as JSON for further analysis or visualization:

```
python3 metrics/extract_metrics.py results/<date>/before/run-1/
```

## How to run

```
./run.sh
```

Launches both DTUs, runs the prompt in each, copies session dirs into `results/<date>/{before,after}/run-1/`, and writes a `meta.json` per side.

## How to read results

```
results/<date>/
  before/run-1/    events.jsonl, stdout.txt, meta.json
  after/run-1/     events.jsonl, stdout.txt, meta.json
```

Use `metrics/extract_metrics.py` against either run directory to get a structured summary, or read the captured `stdout.txt` to see the agent's full session output.

## Using as a template

Copy `01-explorer-removal/` to `02-<your-example>/`. Replace `README.md`, `change.md`, `profiles/`, and `run.sh`. The `results/` shape stays the same, and `metrics/extract_metrics.py` is general enough to reuse unchanged.
