---
mode:
  name: evaluation
  description: Guidance for creating evaluations for the Amplifier ecosystem and beyond.
  shortcut: evaluation
  advertised: false
  default_action: allow
---


## High Level Steps

For anyone new to evals, this is how they should start.

### 1. Scenarios

Work with the user to determine their need and decide what to evaluate. Are they testing a change? Looking to develop metrics? Decide whether the right path is custom scenarios tied to their specific work, or off-the-shelf industry benchmarks.

```
read_file file_path="@evaluation:context/workflow/brainstorm-scenarios.md"
```


### 2. Automation

Wrap the chosen scenarios in a runnable harness so anyone can run them, re-run them, and get comparable results. By default, set up a Digital Twin Universe profile per variant and capture all relevant data such as  stdout and session files.

```
read_file file_path="@evaluation:context/workflow/harness-automation.md"
```


### 3. Analyze the results

After running through one or more scenarios, look at the results. Do they make sense? Are they what you would expect?
In a before and after case, how did the outputs change? If it's not clear, consider running more samples.


### 4. Analyze the Patterns

Once you get here, you will have the automations to run many scenarios, trying different approaches, and getting their outputs. Only then should you think about automating the "evaluation" part of it to get scores or some aggregate results.


### 5. Rubrics and meaningful measurement

Once a small number of "hero" scenarios are running through the harness and the outputs feel right by inspection, define rubrics to turn that judgment into scores and aggregate metrics.


---

## Worked examples

Before walking through the steps, find a worked example. These are concrete end-to-end evaluations using this bundle and serve as templates for new ones.

```
read_file file_path="@evaluation:examples/EXAMPLE_INDEX.md"
```

The index lists each example, what it measures, and the shape it uses. Open the directory of any example whose shape resembles what the user wants to do.


---

## Philosophy

When making decisions and suggestions, default to using these philosophies and perspectives.

### Start Simple

Use the principle that one scenario working end to end will get a user 40% of the way, two will get them 65%, three 75% and so on. This coupled with comparison or A/B like evaluations can provide high signal and best trade off between time spent and usefulness.

### Less is More

Push back against users wanting to start by creating a high quantity of evaluation scenarios. It is better to focus on creating a few high-signal scenarios than many low-signal ones.

### Direct user attention to scenarios and criteria, not code

Successful evaluations think deeply about what problem the product being evaluated is meant to solve. They then create the measurements that can effectively measure success. The implementation is often the easy part once these two are decided.

### Comparisons Can Provide Immediate Value

Before jumping into creating rubrics, often users will want to validate the quality of their changes. In this case, you should propose "before and after" evaluations that will run their original version and their new version, each in DTUs, and then compare the results.

### Automation is Key

Always first figure out how to run their agent, software, or whatever they are evaluating in a script that can be automated and run by anyone.


---

## Deep Dives

Deep dives are expert written articles, documents, and papers that are meant to be point-in-time (they may go out of date over time) expertise. You should leverage these to get some expert perspectives and take techniques from them. However, these are often more rigorous than what is necessary. Read a deep dive in full when you think you need deeper expertise on a particular use case for a user.

To load any of the files below, use:

```
read_file file_path="@evaluation:context/deep_dives/<filename>"
```

### demystifying-evals-for-ai-agents.md

Anthropic engineering's framework for designing automated evals for AI agents. Defines tasks, environments, grading approaches (programmatic, LLM-as-judge, rubric, end-state), and trade-offs across single-turn, multi-turn, and full-agent evals.

- **Read when:** the user is choosing a grading strategy, designing the structure of an eval (task vs trajectory vs end-state), or asking what a "good eval" generally looks like.

### lessons-on-creating-high-quality-evals.md

Three case studies (code documentation discrepancies, long PDF extraction, image-tagging tool creation) showing how to use agents to build difficult, high-signal eval tasks with clean ground truth or invariant-based scoring. Most useful when building benchmarks for broad capabilities, rather than focused tasks for a specific feature.

- **Read when:** the user is creating a new eval task from scratch, needs ideas for sourcing ground truth, or is deciding between ground-truth and invariant-based scoring for an open-ended task.

### is_a_mixture_of_models_a_competitive_advantage.md

Empirical study (Humanity's Last Exam, others) on whether mixing frontier models in a multi-agent setup outperforms a single-model team holding compute roughly constant.

- **Read when:** the user wants a sense of industry standard benchmarks like Humanity's Last Exam and they are trying to answer research questions with data.

### local_llm_measurement_example.md

Worked example of rigorously measuring local LLM latency and throughput (TTFT, ITL, output tok/s, total latency) across multiple models, quantizations, and node counts using vLLM + GuideLLM, plus light task-based probes of how each model actually behaves under different serving configurations.

- **Read when:** the user is designing latency or perf benchmarks, picking metrics for an inference setup, comparing serving configurations (single-node vs distributed, full vs quantized), or wants a concrete template for sanity-checking how a model behaves before scoring quality.
