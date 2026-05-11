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

### 1. SWE-bench Multimodal

SWE-bench Multimodal is a SWE-bench variant for software-engineering issues that include visual context: screenshots, UI bugs, mockups, diagrams, or visual error messages. It has hundreds of tasks available.

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

dev = load_dataset("SWE-bench/SWE-bench_Multimodal", split="dev")
print(dev[0].keys())
print(dev[0]["problem_statement"])
print(dev[0]["image_assets"])
```

The multimodal records include normal SWE-bench fields like `repo`, `instance_id`, `base_commit`, `problem_statement`, `patch`, `test_patch`, `FAIL_TO_PASS`, and `PASS_TO_PASS`, plus an `image_assets` field containing image URLs associated with the problem statement, patch, or test patch. ([SWE-bench][2])

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

For local dev-set evaluation, use the harness pattern:

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name SWE-bench/SWE-bench_Multimodal \
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

#### First thing to know

The dataset is on Hugging Face as `cais/hle`, but it is gated: you need to log in and accept the access conditions before downloading it. This data must not be **publicly shared, re-uploaded, or redistributed**.

#### Install and load

```bash
git clone https://github.com/centerforaisafety/hle.git
cd hle
pip install -r requirements.txt
```

```python
from datasets import load_dataset

dataset = load_dataset("cais/hle", split="test")
print(dataset[0].keys())
```

The official README gives that same `load_dataset("cais/hle", split="test")` pattern. ([GitHub][7])

#### Run a tiny smoke test

The repo provides a simple evaluation flow using the `openai-python` interface. Their example uses `run_model_predictions.py` followed by `run_judge_results.py`; they recommend not setting `max_completion_tokens` below **8192** for reasoning models, and their evaluation defaults temperature to `0`. ([GitHub][7])

```bash
cd hle_eval

MODEL="gpt-4o-2024-11-20"
DATASET="cais/hle"

python run_model_predictions.py \
  --dataset ${DATASET} \
  --model ${MODEL} \
  --max_completion_tokens 8192 \
  --num_workers 4 \
  --max_samples 10

python run_judge_results.py \
  --dataset ${DATASET} \
  --predictions hle_${MODEL}.json \
  --num_workers 4
```

For a real run, increase `--num_workers` only after confirming your API rate limits and cost envelope.

The flow above runs the reference setup against a stock model via `openai-python`. **For evaluating your own agent, bundle, or feature, customize the setup so the thing under evaluation is what answers each question, not a raw model call.** In practice this means replacing the model invocation inside `run_model_predictions.py` with a call into your agent (an Amplifier `run`, a CLI invocation, a service endpoint, etc.). Keep three things in mind when wiring it in:

- Pass each question through faithfully. Do not add scaffolding, hints, or context the benchmark does not assume.
- Match the output format `run_judge_results.py` expects so the judging step works unchanged.
- Capture wall clock, tokens, and cost per question alongside the answer so they show up in the report.


## Next

Once the benchmark integration is mapped out, wrap it in a runnable harness:

```
read_file file_path="@evaluation:context/workflow/harness-automation.md"
```
