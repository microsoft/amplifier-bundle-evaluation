# Brainstorm Scenarios

When deciding how to create evaluations, the most important step is to figure out what to evaluate against and how to measure it.
It is important to first figure out *what* the user wants to measure.


## Workflow

### 1. Brainstorm and Decide between Custom or Industry Standard Benchmarks

The first question to ask is whether the user would be better off creating their own custom scenarios, or whether it would be more efficient to pull in some industry standard benchmarks.

Consider these use cases where building custom tasks is necessary.
- "I have a new bundle that is supposed to do X" -> Develop custom task(s) that measure the new behavior
- "I have a custom agent that does Y" -> Develop custom task(s) that should invoke the new agent and see how well it does
- "I have an infographic builder that uses AI" -> This is a specific, targeted use case where existing benchmarks are unlikely to exist, so custom scenarios should be created.
- "I have a feature in my app that uses AI to do Z" -> Develop custom tasks that evaluate the AI part of the feature.
- "I built a custom hook (or module, or orchestrator) and want to know if it changes agent behavior" -> Create scenarios that make sure the new module, hook, or orchestrator is actually being exercised.
- "I already have a checklist of things my agent must do (or must not do), score against that" -> The job here will be to turn what the user wants into evaluation tasks.

Consider these use cases where pulling off-the-shelf benchmark tasks would be sufficient, or would be the only way to reach the necessary scale. Typically lean toward industry benchmarks when the change is broad and not tied to a specific workflow.
- "I swapped my bundle's provider from Anthropic to OpenAI, does quality hold?", "I built a memory system and want to know if it improves my agent", "I optimized my bundle for cost or wall-time, did I break behavior?" -> These types of evaluation needs cover a broad range of possible scenarios, so it would be better to use a set of off-the-shelf benchmarks rather than trying to boil the ocean coming up with your own.
- "I want to compare my bundle/agent against Claude Code or Codex on the same task" -> Often this means that the user wants to get a *broad* picture of how their agents or product work against these. However, they *may* also want to compare against custom scenarios.

Some scenarios are better suited toward more traditional validation, where you are testing whether something works rather than the quality of it. The key here is to not overindex on the measurement, but instead focus on setting up the scenario and automating it.
Some examples:
- "I refactored my bundle to load tools and agents lazily, does delegation still work on my actual workflows?"
- "I just added a new mode, can you make sure that it is able to be triggered with `/<mode shortcut>`?"


### 2a. Custom Scenarios

Creating custom scenarios is how to measure specific aspects of a new feature or specific change. If the user's evaluation need necessitates custom scenarios, please read this file to learn how to create custom scenarios for the user.

```
read_file file_path="@evaluation:context/workflow/custom-scenarios.md"
```


### 2b. Industry Standard Benchmarks

Industry standard benchmarks are useful when the user's needs involve measuring changes that impact a wide range of capabilities, they want a general sample of how things are working (i.e., it is not important to create their own scenarios), or they want to compare in a standard way. Please read this file to learn how to set up industry standard benchmarks.

```
read_file file_path="@evaluation:context/workflow/industry_benchmarks.md"
```


## Next

After deciding the path, continue with `context/workflow/custom-scenarios.md` for custom scenarios or `context/workflow/industry_benchmarks.md` for industry benchmarks. Either way, the next workflow step after that is harness automation.
