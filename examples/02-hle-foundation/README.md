# Example 02: Amplifier Foundation on Humanity's Last Exam

A worked example measuring Amplifier foundation's correctness on a single, pinned question from [Humanity's Last Exam](https://huggingface.co/datasets/cais/hle) (HLE).

Unlike example 01 (A/B before/after), this is a single-variant capability measurement. Extend to A/B by adding a second profile and a second variant arm to `run.sh`.

## Target of evaluation

`amplifier-foundation @ main` (off-the-shelf) running a single HLE question inside a Digital Twin Universe. `question.md` (and an optional `question_image.<ext>`) is staged in `/work/hle-task/`, the agent writes its final answer to `answer.txt`, and the result is judged in a separate Amplifier session on the host using HLE's published judge prompt.

## Question selection

Pinned by id in `hle/PINNED_SAMPLE_ID`. The first run picks one with seed=42 from the full HLE test set and writes that id to the pinned file; subsequent runs reuse it. Delete the file to re-sample. To restrict the pool to a specific `answer_type`, pass `--filter-answer-type` to `sample_hle.py`. The LLM judge handles every `answer_type` (exact, multiple-choice, numerical, free-form) semantically.

## Setup

```
Foundation:       git+https://github.com/microsoft/amplifier-foundation@main
Sample source:    cais/hle parquet (gated; needs HF_TOKEN)
Judge:            HLE's published judge prompt, run as a separate amplifier session on the host
Sample count:     1
```

Solver prompt: see `hle/prompts.py` — adapted from HLE's reference solo prompt, pointed at the staged file paths, with web search and out-of-dir exploration forbidden. Judge prompt: asks for `extracted_final_answer`, `reasoning`, `correct: yes|no`; regex-parsed into `verdict.json`.

## How to run

```
./run.sh
```

Stands up the DTU, samples (or reuses the pin), runs the agent, pulls `answer.txt` and the session dir, judges on the host, writes `meta.json`.

## How to read results

**Start here:** `verdict-correct.md` or `verdict-incorrect.md` at the run root — rendered human-readable summary (outcome, agent's final answer, ground truth, session sizes, timings). The filename itself signals the verdict.

```
results/<date>/run-1/
  verdict-{correct|incorrect}.md             rendered summary — start here
  meta.json                                  pinned id, SHAs, wall times, verdict summary
  sample/{sample.json, question.md, question_image.*}
  solver/{answer.txt, stdout.txt, sessions/sessions/<sid>/{events,transcript}.jsonl}
  judge/{verdict.json, judge_prompt.txt, stdout.txt, sessions/sessions/<sid>/}
```

```
python3 metrics/extract_metrics.py results/<date>/run-1/  # structured JSON
python3 metrics/summarize_run.py   results/<date>/run-1/  # re-renders verdict-*.md
```

## Shortcuts taken (v1)

- **No Gitea.** Foundation installed straight from GitHub @main. To evaluate local foundation changes, copy the Gitea mirror block from `01-explorer-removal/run.sh`.
- **Text-only judge.** Images are pushed to the solver but not to the judge. Image-dependent verification is a v2 follow-up.
- **Single sample (n=1).** No batching, no pass-rate. To extend, loop in `run.sh` and add an aggregator in `metrics/`.

## Prerequisites

`amplifier-digital-twin`, `amplifier`, `uv`, `git`, `docker` on PATH; Docker running; `ANTHROPIC_API_KEY` and `HF_TOKEN` in env or `~/.amplifier/keys.env`. The `cais/hle` dataset is gated: accept terms at https://huggingface.co/datasets/cais/hle and create a read token.
