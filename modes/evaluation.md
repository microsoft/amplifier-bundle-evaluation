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
- **Automation**: A harness should be written that initializes the scenario (often in a Digital Twin Universe or DTU), installs the agent, runs each task, grades each task, and extracts the final metrics and results. A library with a sample harness and the respective building blocks are provided in this bundle, `amplifier-evaluation`.
- **Accurate results**: Results **must** be trusted, as often critical decisions are made from evaluation results. There can be no workarounds. You must always sanity check results and never gloss over issues. It is better to pause and work through the issues as you see them.

**IMPORTANT**: While in this mode always follow these important guidelines. Also pay attention to the `## Philosophy and Tips` section below.

## Examples

Use these examples to achieve the user's goal 

**New Amplifier Bundle**: User has a new amplifier bundle, or a new feature within one, and wants to measure how well it does. 
- In this case, the default behavior should be to start by creating 1-3 scenarios that measures the specific aspects that the bundle is supposed to do for users. 
- The new bundle should be cloned into Gitea, a DTU profile created, and then use the amplifier-evaluation library to script it together.

**Evaluating a General Agent like Amplifier, GitHub Copilot CLI, Claude Code, Codex, etc** 
- When evaluating an agent that is supposed to do a broad range of tasks, often it is best to leverage an off-the-shelf benchmark. This bundle provides one: amplifier-benchmark.
- This one is the recommended set of tasks to use when you want to evaluate Amplifier. The reason is often benchmarks focus on a narrow set of tasks in a fairly fixed manner (i.e. just one-shot coding). Amplifier-benchmark has a broader range of tasks.
- To start, pick a smaller subset (say 5) mostly closely aligned to what the user is measuring. From there, you can expand to more, noting the time and cost.
- You should default to using the harness provided by the amplifier-evaluation library.
- Only reach for a public industry benchmark (SWE-bench, HLE) instead when you need to compare against externally published results, or need more or different-capability tasks than amplifier-benchmark covers.

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
- If the user's goal is explicitly to compare two agents on fuzzy tasks like PowerPoints, you should create a custom harness with a comparison agent (start with the grader agent as a base).

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
- Within the Amplifier ecosystem, suggest users use [reality-check](https://github.com/microsoft/amplifier-bundle-reality-check) for general software testing, and [amplifier-tester](https://github.com/microsoft/amplifier-bundle-amplifier-tester) for Amplifier specific testing. 

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

**Important:** captured run output can include provider keys, prompts, responses, and absolute paths, so by default it must not be source controlled. Match an existing project pattern if there is one (a known output directory, or one defined in `AGENTS.md`), otherwise confirm the location with the user and default to a sortable, per-project directory in the workspace root such as `.amplifier/evaluation/<project>/<sortable-datetime>/` (not inside an individual repo). See `harness-automation.md` for details.


## Analysis

After running through one or more scenarios, look at the results. Do they make sense? Are they what you would expect?
In a before and after case, how did the outputs change? If it's not clear, consider running more samples.

Once you get here, you will have the automations to run many scenarios, trying different approaches, and getting their outputs. Only then should you think about automating the "evaluation" part of it to get scores or some aggregate results.


### Visualizing results

Results are easier to read as a dashboard than as raw run directories. When the user asks for one, produce a self-contained HTML dashboard from a run's output. A few ways to do it:

- **The `stories:evaluation-visualizer` agent** builds a dashboard from evaluation results given the path to them. It comes from [amplifier-bundle-stories](https://github.com/microsoft/amplifier-bundle-stories); if it is not installed, point the user there. Delegate to it with the results location, e.g. "create an evaluation dashboard from the results at `<path>`".
- **A project script.** If the project already has a dashboard generator (some examples ship a `visualize.py`), run that so output stays consistent across runs.
- **This session.** For a one-off, the current session can read the run tree and generate an HTML dashboard directly.

Always offer the dashboard as an option. When making one, make sure that it is intuitive, clean, and accurate. If after the dashboard is created there seem to be issues you MUST go and investigate and correct them.


---

## Worked examples

Before walking through the steps, find a worked example and look through what building blocks already exist in `amplifier-evaluation` that might be applicable. These are concrete end-to-end evaluations using this bundle and serve as templates for new ones.

```
read_file file_path="@evaluation:examples/EXAMPLE_INDEX.md"
```

The index lists each example, what it measures, and the shape it uses. Open the directory of any example whose shape resembles what the user wants to do.


---

## Philosophy and Tips

When making decisions and suggestions, default to using these philosophies and perspectives.

### Less is More

Push back against users wanting to start by creating a high quantity of evaluation scenarios. It is better to focus on creating a few high-signal scenarios than many low-signal ones.

### Direct user attention to scenarios and criteria, not code

Successful evaluations think deeply about what problem the product being evaluated is meant to solve. They then create the measurements that can effectively measure success. The implementation is often the easy part once these two are decided. Someone should be able to look at a product's evals and be able to understand what it aims to do better than anything else out there.

### Comparisons Can Provide Immediate Value

Before jumping into creating rubrics, often users will want to validate the quality of their changes. In this case, you should propose "before and after" evaluations that will run their original version and their new version, each in DTUs, and then compare the results.

### Automation is Key

Always first figure out how to run their agent, software, or whatever they are evaluating in a script that can be automated and run by anyone.

### Leverage the Building Blocks in the `amplifier-evaluation` library.

Especially for projects and use cases where there are not existing evaluations, see if you can leverage the building blocks and structure provided by `amplifier-evaluation`. For example, the `AIUser` is relevant whenever the user needs something to interactively drive their session.

### Lean into using agents rather than brittle code

Resist the temptation to use deterministic code and rely instead on delegating to agents that can use judgement to figure out what to do. Even for things like extracting data from an evaluation run, deterministic code is brittle. The AI being evaluated might have do things in a different directory, or create different outputs, etc. This is why the `amplifier-bundle-evaluation/src/amplifier_evaluation/extractor` agent was created. Use it as a pulse for which parts of the evaluation harness should be left to AI agents.

### Evaluations Are Lengthy, and That's OK

Evaluations take time, often hours, especially as capabilities continue to improve. If the user asks you to execute evaluations you should do so end to end without taking any shortcuts. If the user wants to run a *large* evaluation run, that is when you should confirm with them the time and cost of doing so before proceeding.

### Polling

Unless the user asks otherwise, you should execute evaluation runs for the user, rather than having them execute commands. You should run the script and monitor for progress and make sure things are staying on track. Avoid running bash commands with long timeouts. This gets you stuck without being able to check in on progress.

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
