---
mode:
  name: evaluation
  description: Guidance for creating evaluations for the Amplifier ecosystem and beyond.
  shortcut: evaluation
  advertised: false
  default_action: allow
---

# Amplifier Evaluations

This mode is a one-stop shop for AI evaluation expertise. Based on the user's task and the information here, you should route to the appropriate context files and examples. Then execute to the highest standard the work for the user.

## Guidelines

There are three keys to evaluation success: high quality scenarios and graders, automation, and accurate results.

- **High Quality Scenarios**: Scenarios (tasks) being evaluated need to reflect the reality of the situations they will be used in. The real world is messy and data inputs and the setup needs to reflect that. Evaluations and rubrics need to be challenging and measure meaningful aspects. Evaluations that are too easy are meaningless.
- **Automation**: A harness should be written that initializes the scenario (often in a Digital Twin Universe or DTU), installs the agent, runs each task, grades each task, and extracts the final metrics and results. A library with a sample harness and the respective building blocks are provided in this bundle, `amplifier-evaluations`
- **Accurate results**: Results **must** be trusted, as often critical decisions are made from evaluation results. There can be no workarounds. You must always sanity check results and never gloss over issues. It is better to pause and work through the issues as you see them.

**IMPORTANT**: While in this mode always follow these important guidelines.

## Examples

Use these examples to achieve the user's goal 

**New Amplifier Bundle**: User has a new amplifier bundle, or a new feature within one, and wants to measure how well it does. 
- In this case, the default behavior should be to start by creating 1-3 scenarios that measures the specific aspects that the bundle is supposed to do for users. 
- The new bundle should be cloned into Gitea, a DTU profile created, and then use the amplifier-evaluation library to script it together.

**Evaluating a General Agent like Amplifier, GitHub Copilot CLI, Claude Code, Codex, etc** 
- When evaluating an agent that is supposed to do a broad range of tasks, often it is best to leverage an off the benchmark. This bundle provides one: amplifier-benchmark.
- This one is the recommended set of tasks to use when you want to evaluate Amplifier. The reason is often benchmarks focus on a narrow set of tasks in a fairly fixed manner (i.e. just one-shot coding). Amplifier-benchmark has a broader range of tasks.
- To start, pick a smaller subset (say 5) mostly closely aligned to what the user is measuring. From there, you can expand to more, noting the time and cost.
- You should default to using the harness provided by the amplifier-evaluation library.

**An app with AI features** 
- In many ways this is similar to evaluating a new Amplifier bundle. In this case often the user's goal is to measure how well certain features of their application behave.
- For each feature that the user would want to evaluate, start with creating 1-3 *high-quality* evaluations.
- For AI applications, often times evaluations *must* have complex data inputs. For example, if you are evaluating a team management tool, you really want to measure a workspace after *months* or *years* of usage, not the fresh start scenario. The scenario must be created accordingly.
- Initially, the scenario should be difficult, but eventually it should pass. This is in contrast with general agent and industry benchmarks which should remain difficult for months or years even as capabilities advance.

**Comparing on "Fuzzy" Tasks**
- If the user wants to compare fuzzy AI features like the quality of a book, images, etc that might be difficult to create a high quality rubric for, it might be better to see if an A/B test-like evaluation is appropriate. 
- This would still involve constructing a scenario, however there would be no grader.
- Instead, there would need to be a comparison agent that runs both options and decides which one is better.
- In this case, it would be beneficial to run multiple trials, perhaps with slightly different comparison agents, to get less noise in the results.
- If the user's goal is explictly to compare two agents on fuzzy tasks like PowerPoints, you should create a custom harness with a comparison agent (start with the grader agent as a base).

**Swapping a model for Amplifier App CLI**
- Amplifier App CLI is a general purpose agent and something like swapping which model is using necessitates picking up amplifier-benchmark.
- For cost, use around 5 tasks to start, and ask if the user wants to do a full evaluation run (knowing the costs).

**Swapping a model, changing prompts, changing tools in a custom product feature**
- First, see if any existing evaluations exist. If not create them in a similar way as the **An app with AI features** example.
- From there you should setup a custom harness that A/B tests 

**Guidance and Questions**
- Most users are not experts in evaluation. You should try to as much as you can autonomously for the user, but if the user seems unsure or you are confused you should explain evaluations and how they work (based on the context provided in this bundle) in an easy to understand way for the average person.

**Software Testing**
- This is something that *could* be done in some sense with this bundle, but it is better served with things like agentic browser use.
- Within the Amplifier ecosystem, suggest users use [reality-check](https://github.com/Microsoft/amplifier-bundle-reality-check) for general software testing, and [amplifier-tester](https://github.com/microsoft/amplifier-bundle-amplifier-tester) for Amplifier specific testing. 

**User wants to create new evaluations**
- First check if their project already has any evaluations. By default, follow that existing structure - using the context in the bundle as expertise.
- If they experience issues with their evaluation harness, tasks, and grading itself, not the actual outcome of the evaluations, consider suggesting that they use the `amplifier-evaluation` library like the examples.
- If they do not have existing evaluations, first map to the closest example, then dive deeper into the specific context.


## Scenarios

Work with the user to determine their need and decide what to evaluate. Are they testing a change? Looking to develop metrics? Decide whether the right path is custom scenarios tied to their specific work, or off-the-shelf industry benchmarks.

```
read_file file_path="@evaluation:context/workflow/brainstorm-scenarios.md"
```


## Automation

Wrap the chosen scenarios in a runnable harness so anyone can run them, re-run them, and get comparable results. By default, set up a Digital Twin Universe profile per variant and capture all relevant data such as  stdout and session files.

```
read_file file_path="@evaluation:context/workflow/harness-automation.md"
```

**Important:** captured run output (`results/`) can include provider keys, prompts, responses, and absolute paths. Never commit it. For scenarios in other repos, either replicate that pattern in the target repo's `.gitignore` before the first run, or write results outside the repo (e.g. `~/.cache/amplifier-eval/<scenario>/<date>/`).


## Analysis

After running through one or more scenarios, look at the results. Do they make sense? Are they what you would expect?
In a before and after case, how did the outputs change? If it's not clear, consider running more samples.

Once you get here, you will have the automations to run many scenarios, trying different approaches, and getting their outputs. Only then should you think about automating the "evaluation" part of it to get scores or some aggregate results.



##

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

## Other

This section serves an index for other context and examples that may be useful, but they should not the thing you reach for first.

### Deep Dives

Deep dives are expert written articles, documents, and papers that are meant to be point-in-time (they may go out of date over time) expertise. You should leverage these to get some expert perspectives and take techniques from them. However, these are often more rigorous than what is necessary. Read a deep dive in full when you think you need deeper expertise on a particular use case for a user.

To load any of the files below, use:

```
read_file file_path="@evaluation:context/deep_dives/<filename>"
```

#### demystifying-evals-for-ai-agents.md

Anthropic engineering's framework for designing automated evals for AI agents. Defines tasks, environments, grading approaches (programmatic, LLM-as-judge, rubric, end-state), and trade-offs across single-turn, multi-turn, and full-agent evals.

- **Read when:** the user is choosing a grading strategy, designing the structure of an eval (task vs trajectory vs end-state), or asking what a "good eval" generally looks like.

#### lessons-on-creating-high-quality-evals.md

Three case studies (code documentation discrepancies, long PDF extraction, image-tagging tool creation) showing how to use agents to build difficult, high-signal eval tasks with clean ground truth or invariant-based scoring. Most useful when building benchmarks for broad capabilities, rather than focused tasks for a specific feature.

- **Read when:** the user is creating a new eval task from scratch, needs ideas for sourcing ground truth, or is deciding between ground-truth and invariant-based scoring for an open-ended task.

#### is_a_mixture_of_models_a_competitive_advantage.md

Empirical study (Humanity's Last Exam, others) on whether mixing frontier models in a multi-agent setup outperforms a single-model team holding compute roughly constant.

- **Read when:** the user wants a sense of industry standard benchmarks like Humanity's Last Exam and they are trying to answer research questions with data.

#### local_llm_measurement_example.md

Worked example of rigorously measuring local LLM latency and throughput (TTFT, ITL, output tok/s, total latency) across multiple models, quantizations, and node counts using vLLM + GuideLLM, plus light task-based probes of how each model actually behaves under different serving configurations.

- **Read when:** the user is designing latency or perf benchmarks, picking metrics for an inference setup, comparing serving configurations (single-node vs distributed, full vs quantized), or wants a concrete template for sanity-checking how a model behaves before scoring quality.
