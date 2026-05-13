# Creating Custom Scenarios

When creating a custom scenario the most important aspects to get right are difficulty, realism (does it actually measure your new feature, or your change?), and meaningful measurement.


## Difficulty and Realism

One scenario working end to end gets a user ~40% of the way, two ~65%, three ~75%. But that math only holds when each scenario is **high quality**. A low-quality scenario does not add 25 percentage points. It can add zero, or push the signal backwards by making real regressions look like noise.

Quality compounds faster than quantity. Push back hard against the urge to add a fourth or fifth scenario before the first three are difficult, realistic, and trusted.

### What makes a scenario high quality

For evaluating a product, configuration, or change that someone is building, **scenario quality is mostly determined by the environment**. Most teams reach for clever wording in the user ask. The much higher-leverage move is to make the DTU look like a real moment in a real user's work, *before* the agent is ever triggered.

A high-quality scenario environment is **prepopulated** with the kind of state a real user would already have on disk and in their tools when they reach for the product. Examples:

- An in-progress GitHub repo with a partially implemented feature, uncommitted changes, open issues, and recent commit history
- Real documents (specs, PRDs, design docs, notes) sitting in the working directory or in a `/docs` folder
- Diagrams, images, or other binary assets that the agent might need to read or reason over
- A previous Amplifier (or other agent) chat history saved in a form the product can resume from, so the new run picks up mid-thought instead of starting cold
- Configuration files, lockfiles, env files, and secrets stubs that reflect a real local setup
- Data files (CSVs, PDFs, logs) that match the scale and messiness of production data, not toy fixtures

Once the environment is real, the user ask that triggers the run becomes almost obvious. A realistic ask is whatever the user would naturally type given that state. "Continue where I left off", "review this PR", "help me debug the failing test", "summarize the latest design doc and identify open questions". You need to engineer a believable starting point.

This also produces a sharper measurement. When the environment is rich, you can tell the difference between an agent that actually used the context and one that ignored it, which is often exactly the capability you are trying to evaluate.

A useful gut check: **could a teammate sit down at this DTU and believe it is a real workspace they were handed mid-task?** If yes, the scenario is in good shape. If the environment is one file and a one-line prompt, the scenario is almost certainly too thin to produce a meaningful signal, no matter how the prompt is worded.

### Calibrating difficulty

With a realistic environment in place, difficulty largely takes care of itself, but a few things to watch:

- **Too easy:** every agent passes on the first attempt with minimal tool use, or solves it without engaging the parts of the environment you cared about. Push back by adding scope, removing scaffolding from the prompt, or enriching the environment further (more files, more history, more ambiguity). Another sign is when, during a comparison evaluation, you do not see much difference in behavior (although this could also be due to the change itself, so do not conflate the two).
- **Ill-posed:** every agent fails for unrelated reasons, or fails in ways that have nothing to do with the capability you wanted to measure. Tighten the entry point, give the agent a clearer ask, or trim the environment to the parts that actually matter.
- **Just right:** agents partially succeed in ways that distinguish them, and when they fail, you can clearly articulate *why*. That "why" is the signal you are after.

### Iteration

Expect to iterate:
1. Draft the scenario environment and the ask.
2. Run one or two agents through it.
3. Look at where they succeed, fail, and disagree.
4. Adjust the environment, scope, or framing.
5. Repeat until the results are informative.

Only then is the scenario worth automating at scale or building a second one alongside.


## Measurement

Once the scenario environment is solid, the next question is how to read the result. Three layers, in order of leverage:

### Comparison testing

The fastest way to get useful signal out of a scenario is to run it through **a before and after (A/B)**, and compare the outputs side by side. Before vs after a change, model A vs model B, prompt v1 vs v2, bundle with feature on vs off.

Comparisons work because they bypass the hardest part of evaluation, defining what "good" means in the abstract. You do not need a rubric to see that one run produced a clean PR description and the other rambled, or that one run actually used the in-progress repo state and the other ignored it. The diff is the measurement.

This is also the right starting point when the user is validating a change they just made. Propose a before/after run before proposing a rubric. The comparison will either show an obvious win, an obvious regression, or genuine ambiguity. Only the third case justifies the cost of building a rubric.

A useful default: run each configuration two or three times rather than once. Single runs hide variance, and variance itself is signal.

### Rubrics and meaningful measurement

Reach for rubrics when comparisons stop being enough. Common triggers: you want a single number to track over time, you are comparing more than two configurations, or the differences are too subtle for eyeballing to be reliable.

A rubric is meaningful when each criterion is something a competent reviewer (human or audit agent) can answer with high confidence in isolation. Vague criteria like "is the output good?" produce noise. Concrete criteria like "does the PR description reference the files actually changed?" produce signal.

Two heuristics that prevent most rubric problems:

- **Decompose into invariants the answer must satisfy**, rather than scoring an overall impression. Many small, easy checks aggregate into a reliable score. One big, hard check usually does not.
- **Test the rubric itself before trusting it.** Run it against two or three known outputs (a good one, a bad one, a borderline one) and see if the scores match your intuition. If they do not, the rubric is wrong, not the outputs.

When in doubt, keep the rubric small. Five sharp criteria beats fifteen fuzzy ones.

For the full design methodology (dimensions, weights, score-level definitions, judge strategy):

```
read_file file_path="@evaluation:context/methodology/rubric-design.md"
```

### Operational metrics

Independent of correctness, capture the operational cost of each run from the start.

- **Wall clock time** end to end
- **Token usage** (input, output, cached if available) per run and per sub-session
- **Cost** in dollars, derived from token usage
- **Tool call counts** and any retries or failures
- **Any product-specific counters** that matter for the thing being evaluated (e.g., number of files read, number of sub-agents spawned)

These rarely decide a comparison on their own, but they catch regressions that pure quality scores miss: a change that improves output quality 5% while tripling cost is often a bad trade, and you only see that if the numbers are sitting next to each other in the report.

Default to capturing all of these on every run. Decide later which ones to highlight.


## Next

Once the scenarios and measurement plan are in good shape, wrap them in a runnable harness:

```
read_file file_path="@evaluation:context/workflow/harness-automation.md"
```
