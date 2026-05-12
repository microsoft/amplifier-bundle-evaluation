# Example 02: Amplifier Foundation on Humanity's Last Exam

A worked example of the evaluation bundle measuring Amplifier foundation's correctness on a single, randomly sampled question from [Humanity's Last Exam](https://huggingface.co/datasets/cais/hle) (HLE).

Unlike example 01 (an A/B before/after of a foundation change), this is a single-variant capability measurement. The same shape can be extended to A/B by adding a second profile and a second variant arm to `run.sh`.

## Target of evaluation

`amplifier-foundation @ main` (off-the-shelf, no local changes) running a single HLE question end-to-end inside a Digital Twin Universe. The question is staged as `question.md` (and an optional `question_image.<ext>`) in `/work/hle-task/`, the agent is told to write its final answer to `answer.txt` in the same directory, and the result is judged in a separate Amplifier session on the host using HLE's published judge prompt.

## Question

The HLE sample is **pinned** by id in `hle/PINNED_SAMPLE_ID`. The first run picks one with seed=42 from the full HLE test set (all `answer_type` values: `exactMatch`, `multipleChoice`, free-form) and writes that id to the pinned file. Every subsequent run reuses the same question, so results are comparable across runs.

The judge prompt is an LLM doing semantic comparison, not a regex over the response, so it handles every `answer_type` HLE ships with: exact strings, multiple-choice letters, numerical answers (the judge prompt says "within a small margin of error"), and free-form text. To restrict the sampling pool to a specific `answer_type`, pass `--filter-answer-type` to `sample_hle.py`.

To force re-sampling, delete `hle/PINNED_SAMPLE_ID` and run again. The newly chosen id will be pinned in its place.

## Setup

```
Amplifier CLI:    installed from github.com/microsoft/amplifier (master)
Foundation:       git+https://github.com/microsoft/amplifier-foundation@main (resolved SHA recorded in meta.json)
Sample source:    cais/hle parquet from HuggingFace (gated; needs HF_TOKEN)
Sample selection: pinned id (see hle/PINNED_SAMPLE_ID), no answer_type filter
Judge:            HLE's published judge prompt, run as a separate amplifier session on the host
Sample count:     1
```

## Solver prompt (in DTU)

Adapted from the HLE reference's solo prompt, pointed at the staged file paths:

```
I have a question I would like you to answer for me to the best of your ability.

The question is in the file 'question.md' in the current directory.
[If the sample has an image, an image note is appended naming question_image.<ext>]

Write the final answer to 'answer.txt' in the current directory. The file must
have a clear, definitive final answer on the last line, formatted as:
ANSWER: <your answer>

You should write tools, run code, and so forth where appropriate to figure out
the answer, but DO NOT search the web or explore files outside of your current
directory.

The answer must be precise and unambiguous.
```

## Judge prompt (on host)

Asks for `extracted_final_answer`, `reasoning`, and `correct: yes|no`. Parsed via regex into `verdict.json`.

## Measurements

Captured per run from `events.jsonl`, `transcript.jsonl`, and `verdict.json`:

```
Verdict:      correct (yes/no), extracted_final_answer, judge_response
Solver:       root-context tokens, wall time, tool-call count, tool mix,
              delegation targets, exit code, final answer.txt text
Judge:        root-context tokens, wall time
Reproducibility: pinned sample id, parquet sha256, foundation sha
```

`metrics/extract_metrics.py` reads a captured run directory and emits the structured summary as JSON. `metrics/summarize_run.py` renders the same data as the human-readable markdown summary at the run root (`verdict-correct.md` or `verdict-incorrect.md`).

```
python3 metrics/extract_metrics.py results/<date>/run-1/
python3 metrics/summarize_run.py   results/<date>/run-1/
```

## How to run

```
./run.sh
```

Stands up the DTU, samples (or reuses the pinned sample), runs the agent, pulls `answer.txt` and the session dir, judges in a separate amplifier session on the host, and writes `meta.json`.

## How to read results

**Start here:** the `verdict-correct.md` (or `verdict-incorrect.md`) file at the run root is a rendered human-readable summary covering the outcome, the agent's final answer, the ground truth, session sizes, and timings. The filename itself signals the verdict, so a casual `ls` shows it.

```
results/<date>/run-1/
  verdict-{correct|incorrect}.md             rendered summary — start here
  meta.json                                  pinned sample id, SHAs, wall times, exit codes, verdict summary
  sample/
    sample.json                              full HLE record including ground-truth answer
    question.md                              what got pushed into the DTU
    question_image.<ext>                     present iff the sample has an image
  solver/
    answer.txt                               the agent's final answer file
    stdout.txt                               full amplifier-run stdout
    exec.json                                raw amplifier-digital-twin exec output
    sessions/sessions/<sid>/events.jsonl     structured events from the solver session
    sessions/sessions/<sid>/transcript.jsonl LLM conversation
  judge/
    verdict.json                             correct, extracted_final_answer, judge_response, judge_session_id
    stdout.txt                               full judge amplifier-run stdout
    judge_prompt.txt                         the exact prompt sent to the judge
    sessions/sessions/<sid>/                 judge session dir (if locatable)
```

## Shortcuts taken (v1)

These are deliberate v1 simplifications; the example shape supports adding any of them as a follow-up.

- **No Gitea.** Foundation is installed directly from `git+https://github.com/microsoft/amplifier-foundation@main`. There is no Gitea mirror and no `url_rewrites` in `profiles/foundation.yaml`. To evaluate **local** foundation changes, copy the Gitea mirror block from `01-explorer-removal/run.sh` and add `url_rewrites` to the profile, just like example 01 does.
- **Text-only judge.** When the sample includes an image, the image is pushed into the DTU and described to the solver, but the **judge** sees only text (question, response, ground-truth answer). The HLE reference passes the image to the judge as well. For most questions the text is enough for the judge to decide correctness, but image-dependent verification (e.g. spatial reasoning that requires seeing the image) is a v2 follow-up.
- **Single sample (n=1).** No batching, no pass-rate. To extend to n>1, add a `run-2/`, `run-3/`, etc. loop in `run.sh` and an aggregator in `metrics/`.

## Prerequisites

- `amplifier-digital-twin`, `amplifier`, `uv`, `git`, `docker` on PATH.
- Docker daemon running.
- `ANTHROPIC_API_KEY` set (or in `~/.amplifier/keys.env`).
- `HF_TOKEN` set (or in `~/.amplifier/keys.env`). The `cais/hle` dataset is **gated**: you must visit https://huggingface.co/datasets/cais/hle, accept the terms, then create a read token at https://huggingface.co/settings/tokens.

## Using as a template for a new HLE-style benchmark example

Copy this directory and replace:

- `hle/sample_hle.py` with whatever pulls a sample from your benchmark
- `hle/prompts.py` with your task and judge prompts
- `hle/judge.py` (if your judge differs structurally) or just point it at new prompts
- `README.md` and the pinned sample id

The `profiles/`, `run.sh`, and `metrics/` shapes are intentionally generic and worth keeping.
