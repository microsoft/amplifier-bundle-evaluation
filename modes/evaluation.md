---
mode:
  name: evaluation
  description: Guidance for creating evaluations for the Amplifier ecosystem and beyond.
  shortcut: eval
  default_action: allow
---

## Getting Started

For anyone new to evals, this is how they should start. 

### 1. Scenarios

First, determine and create one to five key scenarios. A scenario contains all the necessary inputs and problem setup that a user might have. For example, if the user is building an Amplifier bundle that is a skill, the scenario might include the prompt that should trigger the skill.


### 2. Automation

Setup an an automation to run the scenario automatically. This should setup a digital-twin-profile that creates the environment for the scenario, including loading any necessary data. Then, the scenario should be able to be "run". For example, if its an Amplifier skill, a command might be sent to the DTU to run amplifier with that prompt. The output should then be captured. This output might include capturing wall clock time, tokens, cost, etc.
In cases where the goal is to compare *changes*, there could be parallel DTUs made that have the before and after installed.


### 3. Analyze the results

After running through one or more scenarios. Look at the results. Do they make sense? Are they what you would expect?
In a before and after case, how did the outputs change? If its not clear, consider running more samples.


### 4. Analyze the Patterns

Once you get here, you will have the automations to run many scenarios, trying different approaches, and getting their outputs. Only then should you think about automating the "evaluation" part of it to get scores or some aggregate results.


### 5. Larger Scale Metrics

Once you have some "hero" scenarios and automations, move to the deep dives to determine how to come up with rubrics and getting metrics.


## Deep Dives

Deep dives are expert written articles, documents, and papers that are meant to be point-in-time (they may go out of date over time) expertise. You should leverage these to get some expert perspectives and take techniques from them. However, these are often more rigorous than what is necessary. Read a deep dive in full when you think you need deeper expertise on a particular use case for a user.

To load any of the files below, use:

```
read_file file_path="@evaluation:context/deep_dives/<filename>"
```

### demystifying-evals-for-ai-agents.md

Anthropic engineering's framework for designing automated evals for AI agents — defines tasks, environments, grading approaches (programmatic, LLM-as-judge, rubric, end-state), and trade-offs across single-turn, multi-turn, and full-agent evals.

- **Read when:** the user is choosing a grading strategy, designing the structure of an eval (task vs trajectory vs end-state), or asking what a "good eval" generally looks like.

### lessons-on-creating-high-quality-evals.md

Three case studies (code documentation discrepancies, long PDF extraction, image-tagging tool creation) showing how to use agents to build difficult, high-signal eval tasks with clean ground truth or invariant-based scoring. Most useful when building benchmarks for broad capabilities, rather than focused tasks for a specific feature.

- **Read when:** the user is creating a new eval task from scratch, needs ideas for sourcing ground truth, or is deciding between ground-truth and invariant-based scoring for an open-ended task.

### is_a_mixture_of_models_a_competitive_advantage.md

Empirical study (Humanity's Last Exam, others) on whether mixing frontier models in a multi-agent setup outperforms a single-model team holding compute roughly constant.

- **Read when:** Read when the user wants a sense of industry standard benchmarks like Humanity's Last Exam and they are trying to answer research questions with data.

### local_llm_measurement_example.md

Worked example of rigorously measuring local LLM latency and throughput (TTFT, ITL, output tok/s, total latency) across multiple models, quantizations, and node counts using vLLM + GuideLLM, plus light task-based probes of how each model actually behaves under different serving configurations.

- **Read when:** the user is designing latency or perf benchmarks, picking metrics for an inference setup, comparing serving configurations (single-node vs distributed, full vs quantized), or wants a concrete template for sanity-checking how a model behaves before scoring quality.

