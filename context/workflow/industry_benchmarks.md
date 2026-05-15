# Industry Benchmarks

The key things to keep in mind when implementing industry benchmarks are:
a) Implement them faithfully and integrate the thing being evaluated so it actually uses the benchmark examples correctly.
b) Be mindful of how many benchmark examples to run. Often the user does not want, or does not have the budget to run all, or even a portion, of the entire benchmark. Instead, start by sampling only around 5 examples. From there, ask the user if they want more, making them aware of the potential cost.
c) Make sure that benchmark answers and evaluation logic are not leaked. Scores must be trusted when running these benchmark tasks.


## What Makes a Good Industry Benchmark

Not all benchmarks make good candidates. Ensure that they meet these criteria before even proposing to use one. The ones in this document are good candidates that are recommended.
- Make sure the benchmarks are recent as of today (no older than 1 year). As AI capabilities advance, older benchmarks become saturated and measure solved problems.
- Make sure that the benchmarks are not saturated. For example, if reported scores are already above ~85% on models alone, the benchmark is mostly saturated already. In this case, it is not useful for providing signal anymore, since most things will succeed at it.
- The exception to these rules might be for local models, which are often 3-12 months behind the frontier.

## Examples

Note this section is high level. You should clone these benchmark repos locally and use the install/run steps below as a starting point. In every case, you will need to customize the setup so the agent, bundle, or feature being evaluated is the thing answering each task.

### 1. SWE-bench (Verified or Multimodal)

SWE-bench evaluates the ability to fix real GitHub issues by producing a unified diff that makes the issue's tests pass. Two variants are recommended, and either is a reasonable starting point:

- **SWE-bench Verified** (`princeton-nlp/SWE-bench_Verified`, `test` split, 500 Python instances): human-validated subset of the original SWE-bench. The broadest signal, language-stable, and the most common reporting target in the literature.
- **SWE-bench Multimodal** (`princeton-nlp/SWE-bench_Multimodal`, `dev` split, 102 JavaScript instances): issues that include visual context such as screenshots, UI bugs, mockups, diagrams, or visual error messages. Typically harder because the agent must reason over images alongside code, so it requires a model with strong vision capabilities.

Pick Verified for a broad signal on code-fixing. Pick Multimodal when you specifically want to measure visual reasoning together with code-fixing. `@evaluation:examples/04-foundation-vs-dev-demo/` runs against either via `AMPLIFIER_DEMO_SWE_DATASET=verified|multimodal`.

#### Install

```bash
git clone https://github.com/princeton-nlp/SWE-bench.git
cd SWE-bench
pip install -e .
```

You also need Docker running; SWE-bench evaluates patches by applying them to real repositories and running tests inside Docker containers.

#### Load the dataset

```python
from datasets import load_dataset

# Verified (500 Python instances, test split)
ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

# Multimodal (102 JS instances, dev split, includes image_assets)
ds = load_dataset("princeton-nlp/SWE-bench_Multimodal", split="dev")

print(ds[0].keys())
print(ds[0]["problem_statement"])
```

Both variants share the core SWE-bench fields: `repo`, `instance_id`, `base_commit`, `problem_statement`, `patch`, `test_patch`, `FAIL_TO_PASS`, `PASS_TO_PASS`. Multimodal additionally provides an `image_assets` field with image URLs tied to the problem statement, patch, or test patch. ([SWE-bench][2])

#### Your model's job

For each instance, give the model:

```text
repo
base_commit
problem_statement
image_assets["problem_statement"]
```

Then ask it to produce a **unified diff patch**. Save predictions as JSONL:

```json
{"instance_id":"chartjs__Chart.js-10301","model_name_or_path":"my-model","model_patch":"diff --git a/..."}
```

SWE-bench expects each prediction line to contain `instance_id`, `model_name_or_path`, and `model_patch`.

#### Evaluate

Use the harness pattern, passing the dataset and split for your chosen variant:

```bash
# Verified
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --split test \
  --predictions_path predictions.jsonl \
  --max_workers 4 \
  --run_id verified_run

# Multimodal
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Multimodal \
  --split dev \
  --predictions_path predictions.jsonl \
  --max_workers 4 \
  --run_id mm_dev_run
```

If your installed harness does not recognize `--split`, check:

```bash
python -m swebench.harness.run_evaluation --help
```


#### Practical gotchas

Start with **one instance**, not the full split. SWE-bench is resource-intensive; the repo recommends an x86_64 machine with roughly **120 GB free storage, 16 GB RAM, and 8 CPU cores**, and lowering `--max_workers` if Docker or disk becomes unstable.

Make sure that the agent you are validating is properly configured to get the benchmark task information with whatever feature or changes you are evaluating.
It is CRITICAL that the answers and evaluation logic are not leaked in your setup.


### Humanity’s Last Exam (HLE)

Humanity’s Last Exam is a multimodal, closed-ended academic benchmark with 2500 questions across many subjects, including math, humanities, and natural sciences. It contains multiple-choice and short-answer questions designed for automated grading.

#### Worked example in this bundle

`@evaluation:examples/02-hle-foundation/` is a complete, runnable HLE-on-Amplifier example. Copy it as a starting point for any HLE evaluation. It uses the approach documented below.

#### Access (required for any HLE work)

`cais/hle` is gated on HuggingFace. Before downloading:

1. Visit https://huggingface.co/datasets/cais/hle and accept the access terms (mandatory click-through).
2. Create a read token at https://huggingface.co/settings/tokens with `Read access to contents of all public gated repos you can access` enabled.
3. Export `HF_TOKEN=hf_...` or add it to `~/.amplifier/keys.env`.

The HLE data must not be **publicly shared, re-uploaded, or redistributed**.

#### Approach for evaluating Amplifier on HLE

Use the pattern in `@evaluation:examples/02-hle-foundation/` as the recommended approach. The principles, in order:

- **Sample on the host, not in the environment under test.** Ground truth must never enter the DTU. The host downloads the parquet via `huggingface_hub`, picks a row, writes `question.md` (and `question_image.<ext>` for image samples) into a working directory, and pushes only those files into the DTU.
- **Pin the sample id.** A checked-in `PINNED_SAMPLE_ID` file makes the canonical question for an example deterministic across re-runs. The first run writes it; every subsequent run reads it.
- **Solver runs inside a DTU.** Plain `amplifier run` with whatever bundle is under test. The DTU profile is the source of truth for what the agent has access to.
- **Judge runs as a separate Amplifier session on the host.** The HLE judge prompt is LLM-as-judge and answer-type-agnostic. It handles exact strings, multiple choice, numerical with margin, and free-form text. Running it as its own `amplifier run` subprocess keeps it isolated from the solver's session and gives you a captured judge events.jsonl / transcript.jsonl alongside the solver's.
- **Capture metrics from both sessions.** Wall time, tool calls, tokens, delegations, cost. Extract from `events.jsonl` and `transcript.jsonl` for each session. See `metrics/extract_metrics.py` in the worked example.
- **Render a glanceable verdict.** A `verdict-{correct|incorrect}.md` at the run root makes the outcome visible to `ls`.

#### Practical guidance

- Pass each question through faithfully. Do not add scaffolding, hints, or context the benchmark does not assume.
- Never log or surface the ground-truth answer in any artifact pushed into the DTU.
- Start small. n=1 with a pinned sample id, end-to-end, before scaling.
- Capture wall clock, tokens, and cost per question. They show up in the verdict file and the metrics extractor.


## Next

Once the benchmark integration is mapped out, wrap it in a runnable harness:

```
read_file file_path="@evaluation:context/workflow/harness-automation.md"
```
