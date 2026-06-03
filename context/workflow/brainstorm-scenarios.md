# Brainstorm Scenarios

When deciding how to create evaluations, the most important step is to figure out what to evaluate against and how to measure it.
It is important to first figure out *what* the user wants to measure.


## Workflow

### 1. Brainstorm and Decide between Custom Scenarios and Off-the-Shelf Tasks

The first question to ask is whether the user would be better off creating their own custom scenarios, or whether it would be more efficient to pull in some industry standard benchmarks.

Consider these use cases where building custom tasks is necessary.
- "I have a new bundle that is supposed to do X" -> Develop custom task(s) that measure the new behavior
- "I have a custom agent that does Y" -> Develop custom task(s) that should invoke the new agent and see how well it does
- "I have an infographic builder that uses AI" -> This is a specific, targeted use case where existing benchmarks are unlikely to exist, so custom scenarios should be created.
- "I have a feature in my app that uses AI to do Z" -> Develop custom tasks that evaluate the AI part of the feature.
- "I built a custom hook (or module, or orchestrator) and want to know if it changes agent behavior" -> Create scenarios that make sure the new module, hook, or orchestrator is actually being exercised.
- "I already have a checklist of things my agent must do (or must not do), score against that" -> The job here will be to turn what the user wants into evaluation tasks.

Consider these use cases where pulling off-the-shelf tasks would be sufficient, or would be the only way to reach the necessary scale. Typically lean off-the-shelf when the change is broad and not tied to a specific workflow.
- "I swapped my bundle's provider from Anthropic to OpenAI, does quality hold?", "I built a memory system and want to know if it improves my agent", "I optimized my bundle for cost or wall-time, did I break behavior?" -> These needs cover a broad range of scenarios, so reach for an existing task set rather than trying to boil the ocean coming up with your own.
- "I want to compare my bundle/agent against Claude Code or Codex on the same task" -> Often this means that the user wants to get a *broad* picture of how their agents or product work against these. However, they *may* also want to compare against custom scenarios.

For these broad, off-the-shelf needs, default to `amplifier-benchmark`, the curated task set shipped in this bundle. It spans a wider range of agent tasks than a typical single-capability benchmark and runs directly through the amplifier-evaluation harness. Only reach for a public industry benchmark (SWE-bench, HLE, and the like) when something specific necessitates it:
- You need to compare against externally reported, published results in a standard way. Public benchmarks have leaderboards and known reporting targets; amplifier-benchmark has no external comparison point.
- You need more tasks, greater scale, or a specific capability that amplifier-benchmark does not cover (for example pure code-fixing across hundreds of instances, or visual reasoning).

Some scenarios are better suited toward more traditional validation, where you are testing whether something works rather than the quality of it. The key here is to not overindex on the measurement, but instead focus on setting up the scenario and automating it.
Some examples:
- "I refactored my bundle to load tools and agents lazily, does delegation still work on my actual workflows?"
- "I just added a new mode, can you make sure that it is able to be triggered with `/<mode shortcut>`?"


### 2a. Custom Scenarios

Creating custom scenarios is how to measure specific aspects of a new feature or specific change. If the user's evaluation need necessitates custom scenarios, please read this file to learn how to create custom scenarios for the user.

```
read_file file_path="@evaluation:context/workflow/custom-scenarios.md"
```


### 2b. Off-the-Shelf Tasks

For broad needs, default to `amplifier-benchmark`, the curated task set shipped in this bundle. Pick a small subset (around 5) most aligned with what the user is measuring, run it through the amplifier-evaluation harness, and expand from there while noting time and cost. The harness loads `amplifier-benchmark/agents` and `amplifier-benchmark/tasks` directly through its `run()` entry point; read this for how to run it:

```
read_file file_path="@evaluation:context/harness/overview.md"
```

Reach for a public industry benchmark only when something necessitates it: comparing against externally published results in a standard way, or needing more, broader, or different-capability tasks than amplifier-benchmark covers. In that case, read:

```
read_file file_path="@evaluation:context/workflow/industry_benchmarks.md"
```


## Next

After deciding the path, continue with `context/workflow/custom-scenarios.md` for custom scenarios. For off-the-shelf needs, default to `amplifier-benchmark` and proceed to harness automation; only read `context/workflow/industry_benchmarks.md` when a public benchmark is necessitated. Either way, the next workflow step is harness automation.
