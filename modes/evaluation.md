---
mode:
  name: evaluation
  description: Guidance for creating evaluations for the Amplifier ecosystem and beyond.
  shortcut: evaluation
  default_action: allow
---


## High Level Steps

For anyone new to evals, this is how they should start. 

### 1. Scenarios

Work with the user to determine their need. Are they testing a change? Are they looking to develop metrics? What scenarios and use cases are important for them to measure?
Determine and create one to five key scenarios. A scenario contains all the necessary inputs and problem setup that a user might have. For example, if the user is building an Amplifier bundle that is a skill, the scenario might include the prompt that should trigger the skill.


### 2. Automation

Setup an an automation to run the scenario automatically. This should setup a digital-twin-profile that creates the environment for the scenario, including loading any necessary data. Then, the scenario should be able to be "run". For example, if its an Amplifier skill, a command might be sent to the DTU to run amplifier with that prompt. The output should then be captured. This output might include capturing wall clock time, tokens, cost, etc. 
- In cases where the goal is to compare *changes*, there could be parallel DTUs made that have the before and after installed.
- By default, create an evaluations/ dir where each scenario will live. Use the examples as a reference structure. However, this could change depending on the user's use case.
- From the DTUs be sure to extract the relevant files for analysis that will happen at an aggregate level outside each individual DTU or scenario run within the DTU.


### 3. Analyze the results

After running through one or more scenarios. Look at the results. Do they make sense? Are they what you would expect?
In a before and after case, how did the outputs change? If its not clear, consider running more samples.


### 4. Analyze the Patterns

Once you get here, you will have the automations to run many scenarios, trying different approaches, and getting their outputs. Only then should you think about automating the "evaluation" part of it to get scores or some aggregate results.


### 5. Larger Scale Metrics

Once you have some "hero" scenarios and automations, move to the deep dives to determine how to come up with rubrics and getting metrics.


## Worked examples

Before walking through the steps below, find a worked examples — they are concrete end-to-end evaluations using this bundle and serve as templates for new ones.

```
read_file file_path="@evaluation:examples/EXAMPLE_INDEX.md"
```

The index lists each example, what it measures, and the shape it uses. Open the directory of any example whose shape resembles what the user wants to do.


## Philosophy

When making decisions and suggestions, default to using these philosophies and perspectives.

### Start Simple

Use the principle that one scenario working end to end will get a user 40% of the way, two will get them 65%, three 75% and so on. This coupled with comparison or A/B like evaluations can provide high signal and best trade off between time spent and usefulness.

### Less is More

Push back against users wanting to start by creating a high quantity of evaluation scenarios. It is better to focus on creating a few that are high signal than scale.

### Direct user attention to scenarios and criteria, not code

Successful evaluations think deeply about what the problem the product being evaluated is meant to solve. They then create the measurements that can effectively measure success. The implementation is the often the easy part once these two are decided.

### Comparisons Can Provide Immediate Value

Before jumping into creating rubrics, often users will want to validate the quality of their changes. In this case, you should propose "before and after" evaluations that will run their original version, and their new version each in DTUs and then compare the results.

### Automation is Key

Always first figure out how to run their agent, software, whatever they are evaluating in script that can be automated and run by anyone.


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

