# Brainstorm Scenarios

When deciding how to create evaluations, the most important step is to figure out what to evaluate against and how to measure it.
It is important to first figure out *what* the user wants to measure.


## Workflow

### 1. Understand what is being evaluated, and what to measure

Before choosing scenarios or tasks, get explicit about two things. Skipping this is the most common way an evaluation ends up measuring the wrong thing.

1. **What is the thing under evaluation for?** What is it supposed to do better than the alternative it replaces or competes with? For a bundle, agent, or feature, that is the specific behavior or quality it claims to improve. Do not read the purpose off the implementation, and do not ask the component that performs the work what it is for; that tells you how it works, not what it is meant to be good at.

2. **Which criteria capture that purpose?** Turn the purpose into the specific, observable things a good result must show. These criteria are what the scenario and rubric will measure. Name them before building anything.

**Do this work for the user, and keep it concise; do not hand them a blank page.** Most users will start vague ("just evaluate it") and will give up or stall if you answer with open-ended questions like "what is this for?" and "what are your criteria?" Treat their vague ask as the starting point, not a blocker. Gather what you can yourself first (the product's description and docs, the bundle or agent definition, prior sessions where it was used), then propose a short, concrete draft: a one or two sentence purpose and a brief list of candidate criteria. Ask the user to confirm or correct that draft, not to produce it. Reacting to a concrete proposal is easy and keeps them engaged; producing one from scratch is the part they came to you to avoid. Only escalate to a direct question when you genuinely cannot find or infer the answer, and even then, offer your best guess alongside it.

Do not be pedantic about this. If the purpose and criteria are obvious, or the user already told you what they want measured, take them and move on; do not re-derive or interrogate what you already have. The point is to save the user effort, not to add a mandatory ceremony.

Only once the purpose and criteria are clear, confirm you can build a scenario that exercises them at the right difficulty. A scenario is useful only if it (a) forces those criteria into play and (b) is hard enough that a run without the thing under evaluation can visibly fall short on them. If a faithful scenario looks hard to build, that is a problem for you to solve, not a reason to send the user away: simplify the environment, borrow a realistic fixture, or start with one good scenario rather than abandoning the effort. See `context/workflow/custom-scenarios.md` for difficulty calibration and `context/methodology/rubric-design.md` for turning criteria into a scored rubric.

### 2. Decide between Custom Scenarios and Off-the-Shelf Tasks

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


### 3a. Custom Scenarios

Creating custom scenarios is how to measure specific aspects of a new feature or specific change. If the user's evaluation need necessitates custom scenarios, please read this file to learn how to create custom scenarios for the user.

```
read_file file_path="@evaluation:context/workflow/custom-scenarios.md"
```


### 3b. Off-the-Shelf Tasks

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
