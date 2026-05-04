# Lessons on Creating High Quality Agent Evals

David Koleczek
Published: *December 19, 2025*

*Evaluating AI, specifically long-running AI agents*[^1]*, is an ever-moving and evolving goalpost.** Off the shelf **industry,** benchmarks fall into a few buckets: misaligned with our goals saturated, not representative of **real-world** usage, or **too easy to be meaningful**.** **If the tasks** comprising the benchmark** are too easy, they don't have value. If the** task is** hard**,** but the evaluations are **low quality**, **it **create**s** noise in the results.** **We aim to produce difficult evals for current agents, each being high signal, and building them to be representative of our product goals. **In this **document,** we discuss the strategies we are leveraging to keep **pace** by highlighting three case studies.*

## Introduction

Agents and the tools and products that integrate them are becoming increasingly general, which leads to a need for a more general set of high-quality evaluation tasks. In this document, we discuss three specific examples of tasks we have created to illustrate the process of creating these tasks and make it easier for humans and agents to collaborate to create better evaluation, more efficiently. Next, we discuss the key lessons for creating high quality tasks and evaluations.

**Easy to Measure**: Good tasks are rooted in being able to measure them. The first two tasks were created explicitly in such a way that ground truth emerged naturally. However, creating tasks in this way cannot cover the scope of possible use cases we want to measure so in the third example we show how we can have relatively open ended tasks and measure if they are successful through invariants, or criteria that individually in isolation are easy for agents to check.

**Leverage Agents****, Recipes,**** and the Semantic Test**: To make it feasible to create enough high-quality tasks within a realistic time frame, it is necessary to inject agents everywhere throughout the process. One core building block to facilitate this is the semantic test, which simply takes a series of steps and a rubric, and currently uses the Claude Agent SDK to execute the steps to then complete a rubric. We refer to this agent as the “audit agent”. This allows for non-deterministic tests that can still with a high degree of reliability to measure how well an agent did. The implementation is in [eval-recipes](https://github.com/microsoft/eval-recipes/blob/main/eval_recipes/benchmarking/semantic_test.py).

**Quality over Quantity and Trial and Error**: It is better to have a smaller set of tasks that are each of higher quality. Tasks where the evaluations are poor often lead to inconsistent results, such as the agent judging the work always grading the work as "well done" because the evaluation was too open ended. Or on the other hand, if the task is too easy, tasks where the score is always near 100 for each agent do not provide value. Thus, it is critical to test and iterate on the tasks and their evaluations before committing to them. Additionally, we will show how high-quality tasks lead to high quality automated analysis of *why* agents failed at the task.

## Related Work

A first class of widely reported benchmarks measures specific competencies in ways that are only loosely coupled to real-world agent use cases. [AIME 2025](https://huggingface.co/datasets/opencompass/AIME2025) tests contest-style mathematical problem solving via short final-answer exact match, which is useful for isolating mathematical reasoning but abstracts away interaction, tool use, and iterative workflows. [ARC-AGI-2](https://arcprize.org/arc-agi/2/) tasks are visual puzzles that test abstract reasoning and generalization rather than memorized knowledge. Even when such benchmarks have rigorous, execution-based scoring, they can still be “synthetic” relative to real usage. For example, [FormulaOne-Warmup](https://github.com/double-ai/formulaone-dataset-release) centers on algorithmic dynamic-programming subroutines for logic-defined graph problems with correctness enforced by a released test suite, which provides crisp supervision but evaluates a narrow slice of programming behavior unlikely to match typical end-user workflows.

A second class comprises benchmarks that better approximate real work products but lack a fast, fully public, automatic validation loop, alongside benchmark families that are increasingly saturated due to long-standing community optimization and possible contamination. [GDPval](https://openai.com/index/gdpval/) targets economically meaningful deliverables across occupations and is primarily scored via blinded expert pairwise comparisons (with only partial/experimental automation), which makes iterative development and independent reproducibility harder than in fully executable harnesses. In parallel, software-issue benchmarks such as [SWE-bench Verified](https://openai.com/index/introducing-swe-bench-verified/) benefit from objective test-based scoring, but their extensive adoption and prolonged leaderboard focus can incentivize benchmark-specific scaffolding and reduce their value as fresh indicators of general capability.

A third class includes benchmarks that may offer better candidates for our purposes by combining higher-fidelity task structure with either executable verification or explicitly defined rubrics on hard, domain-authentic problems. [FrontierScience](https://openai.com/index/frontierscience) targets expert-level science reasoning using an open gold set and a stated grading procedure (short-answer checks and rubric-based scoring), trading some automation purity for coverage of genuinely difficult scientific synthesis. [Terminal-Bench 2.0](https://github.com/laude-institute/terminal-bench-2) evaluates tool-using agents in containerized terminal environments with objective task verifiers, enabling tight feedback loops that more closely resemble real development and operations workflows; complementary candidates include GUI-centered computer-use evaluation in [OSWorld](https://os-world.github.io/), end-to-end ML workflow execution in [MLE-bench](https://github.com/openai/mle-bench), research-replication pipelines in [PaperBench](https://openai.com/index/paperbench), and market-grounded software deliverables in [SWE-Lancer](https://openai.com/index/swe-lancer/). Collectively, these benchmarks move closer to measuring end-to-end capability under realistic constraints, while still leaving open methodological questions around grader robustness for rubric-based evaluation and the cost/standardization burden of execution-heavy environments. In the future, we may incorporate tasks from this category into our results.

## Example 1 – Code Documentation Discrepancies

In this first example, we look at how we can create an evaluation task aimed at measuring how well an agent can discover discrepancies in documentation with respect to the actual implementation and functionality. The core challenge is in how we construct that task and environment such that we can be confident in our measurement, whilst leveraging agents to make it feasible and scalable. We begin creating tasks by starting with existing, high-quality, code repositories, and the goal of using coding agents to inject code discrepancies. The main considerations for choosing an adequate repo as of today are that it does not have a significant number of external dependencies (like cloud services or API keys) and it is high quality such that we don't encounter a large amount of false positive discrepancies that already existed in the repository. The final task definition(s) can be found in the eval-recipes package in the [data/tasks directory](https://github.com/microsoft/eval-recipes/tree/main/data/tasks/code-discrepancy-docstrings-grasp).

Let's walk through the final process that creates the evaluation tasks for code documentation discrepancies. Note that the process described here is intentionally kept loose, but one recommended way to implement it is through the [amplifier-recipes-collection](https://github.com/microsoft/amplifier-collection-recipes), but another way could be through directing a general agent such as one built into [amplifier-app-cli](https://github.com/microsoft/amplifier-app-cli), GitHub Copilot, Claude Code, or others. We find that the general agents are great for an initial exploration and figuring out a process, but once that process is discovered, it is better to encode your process more precisely which amplifier and the recipe-collection makes easy. Throughout, we will discuss the lessons and learnings that helped us get to this point.

*Figure 1**:** High level flow of** an agent** injecting a discrepancy in a repository. This process is repeated multiple times to create one task.*

First, as shown in Figure 1, we first instruct the agent to explore the chosen repository, whilst giving it a rough scope. In this case, the chosen repo was [graspologic](https://github.com/graspologic-org/graspologic). Depending on the repository and its documentation, we might scope the injected discrepancies to docstrings, tutorials, or markdown documents, or the scope is “all of the above” present in the repo. Creating this scope up front helps direct the agent from misunderstanding the problem. For example, there have been instances where the agent without a smaller scope became confused and started to find existing discrepancies. Often agents will do this exploration, without explicit instruction, as part of finding a discrepancy once we define the scope.

### Discrepancy #3: SeedlessProcrustes initial_P Soft Assignment Matrix Description

| Property | Value |
| --- | --- |
| Location | `./graspologic/align/seedless_procrustes.py` (lines 83-84) |
| Related Code | `./graspologic/align/seedless_procrustes.py` (lines 253-263) |
| Type | Matrix normalization claim - row/column sums swapped |

...

#### Interesting Twist

The error message at lines 259-261 is ALREADY WRONG in the same way:

```python

msg = (

    "Initial_P must be a soft assignment matrix "

    "(rows add up to (1/number of cols) "   # WRONG! Should be 1/number of rows

    "and columns add up to (1/number of rows))"  # WRONG! Should be 1/number of cols

)

```

*Figure 2: Example of one of the discrepancies injected into the grapsologic library.*

As part of the process of finding a discrepancy, the key is to validate that the discrepancy is one that an agent could reasonably find. Thus, we spend time encoding validation into the process in two ways. The first is to check if the proposed discrepancy is a discrepancy in the first place. This helps discover a class of problems around:

a) The agent misunderstands how the code works. Forcing the model to run the code helps catch issues.

b) The agent stumbling upon an existing discrepancy (which might be OK, but could lead to confusion when the model is also being encouraged to inject a new issue). 

The second validation occurs after the dependency is injected; the model is then encouraged to follow the new (but now wrong) documentation to validate that there is now actually an issue in the docs. This is also a good time to check in on progress and steer the agent if necessary. For example, we want to make sure the discrepancies are not trivial. Often the agent would make simple additions to files that are obviously incorrect. This is problematic because the task will simply become checking if the agent reads the file and checks the corresponding source code. However, if we push the agent to make plausible changes, we can get some very tricky gems such as the one in Figure 2 where the agent discovered an existing error to pile onto. In a similar vein, encouraging diversity of discrepancies can increase difficulty. For example, agents might be very good at spotting one issue, but if there are many, they may not be able to find all of them, especially if they are scattered across the library. 

The final step is to have the agent summarize the injected discrepancy into a Markdown file for use as ground truth and then repeat the process to find more discrepancies. Then the easy part is converting to an [eval-recipes task definition](https://github.com/microsoft/eval-recipes/blob/main/docs/BENCHMARKING.md):

- Come up with task instructions that would lead the agent towards achieving the goal without giving away too much, while also giving us a principled way to be able to evaluate. For example, for a general agent this was: “*I'm working on cleaning up the **<**library**>** **docs, could you find me all discrepancies in the documentation versus what is actually implemented/how it works? Please place your findings in DISCREPANCIES.md so I can review them.*”

- Create the semantic test steps and rubric. In this case, because we have clean ground truth the semantic test is quite simple. It needs to find the DISCREPANCIES.md and then check if each of the discrepancies the agent found match the ones in our ground truth file. Importantly, we do not penalize false positive discrepancies the agent may have found as we have no way of knowing which discrepancies originally existed.

Figure 3 shows the rubric that was filled in by the audit agent executed on the [code-discrepancy-docstrings-grasp task](https://github.com/microsoft/eval-recipes/tree/main/data/tasks/code-discrepancy-docstrings-grasp) while reviewing work completed by Claude Code. We see that in this instance, Claude Code found 2 out of the 4 discrepancies that were injected.

"semantic_test_metadata": {

      "file_created": "Yes - DISCREPANCIES.md exists at /project/DISCREPANCIES.md with 13,445 bytes of content created on Dec 17 17:04",

      "discrepancy_1_bic_column_order": "NOT IDENTIFIED - The agent did not mention the GaussianCluster bic_ DataFrame column reordering issue. The code at lines 169-172 of gclust.py reorders columns to ['spherical', 'diag', 'tied', 'full'] regardless of user input, contradicting the docstring at lines 101-102 which states columns are ordered according to input parameter order. 0 points awarded.",

      "discrepancy_2_svd_seed_none": "CORRECTLY IDENTIFIED - Found at lines 86-89 of DISCREPANCIES.md under 'High Severity Issues > Embed Module > svd_seed Behavior Mismatch'. States: 'Documentation claims svd_seed=None uses system entropy, but implementation converts None to 0 (deterministic).' This accurately captures the core issue. 24 points awarded.",

      "discrepancy_3_initial_p_sums": "NOT IDENTIFIED - The agent did not mention the SeedlessProcrustes initial_P parameter having swapped row/column sum constraints in the docstring versus implementation. While the agent found another issue in SeedlessProcrustes (wrong variable in error message), the specific initial_P documentation discrepancy was not identified. 0 points awarded.",

      "discrepancy_4_n_init_ghost": "CORRECTLY IDENTIFIED - Found at lines 103-106 of DISCREPANCIES.md under 'High Severity Issues > Cluster Module'. States: 'n_init Parameter Documented but Not Implemented - KMeansCluster. Docstring documents n_init parameter but it does not exist in __init__.' This accurately identifies the ghost parameter issue. 24 points awarded."},

*Figure 3: **A sample rubric for the *[*code-discrepancy-docstrings-grasp task*](https://github.com/microsoft/eval-recipes/tree/main/data/tasks/code-discrepancy-docstrings-grasp)* generated after our audit agent examined Claude Code’s work.*

We additionally run a workflow to help us analyze *why* the agent did not catch some of the issues. Figure 4 shows how the agent did in fact *look* at the docstring which had a discrepancy, but since it did not execute or further validate if the docstring was correct, it did not catch the issue.

The agent's exploration approach focused on comparing **parameter signatures and return types** but did not deeply analyze the **behavioral semantics** of what attributes like `bic_` actually contain at runtime versus what the docstring promises.

The agent DID examine `gclust.py` (confirmed by grep searches showing the file was processed). However, the issue is subtle:

- The agent would have seen line 242 which mentions error message issues

- Line 253 about range documentation mismatches

- But the `bic_` column ordering is an **attribute behavior discrepancy**, not a parameter/signature mismatch

*Figure 4: A snippet from a generated report that analyzes why an agent, in this case Claude Code, incorrectly solved the *[*code-discrepancy-docstrings-grasp task.*](https://github.com/microsoft/eval-recipes/tree/main/data/tasks/code-discrepancy-docstrings-grasp)

To summarize, **each individual step of creating this task likely** **sounds simple – that is by design**. To maximize the chances the agent can successfully create the task to a high degree, we need each individual step to be very reliable while we direct at a high level. The details around diversity and encouraging complexity without going too far are key to creating tasks that balance difficulty and utility.

## Example 2 – Long and Complex PDF Extraction

Let's say another hypothesis we have about our product is that it should perform better on tasks that require operating over content that is much more than can fit within a context window, and requires specialized steps that an off-the-shelf agent might not realize it needs to effectively solve the problem. One such task that would help us measure this is extracting data from very lengthy and messy PDFs. These are both far too long to load in as is into a single LLM call, *and* PDFs often contain content that can only be accurately extracted with additional OCR. The core challenge is while there are many lengthy and messy PDFs in the wild, we don't have *answers* to the types of questions that people might ask of them. This is where we take an approach to come up with a problem space, then generate synthetic data to reflect that world, come up with questions, answer pairs that can be relatively easily answered from the raw data, and finally generating a messy PDF that contains the data necessary to answer our questions we generated.

*Figure 5: **High level flow of an agent creating a task for Q**&**A over a complex PDF.*

As shown in Figure 5 and like in example 1, it is important to start with an exploration that leads to scoping down the problem space. In this specific case, after an exploration phase with a general agent, we land on HR data because it checks many boxes: ability to enumerate lots of realistic data (names of employees and data about them) and have complex relationships present (such as organization structures). Another important aspect to consider is that as the underlying LLMs become more intelligent, they are also getting better at sensing when something is off about synthetic data. That is why we take care to make the data realistic by having it model data after a real multinational corporation and setup the scenario (by claiming the data has been anonymized) such that an LLM wouldn't flag it as fabricated.

The synthetic generation step was largely autonomous with steering at a high level to encourage diversity and complexity in the generated data that models struggle with by default. Some of this steering led to:

- Replacing hardcoded name lists with the Faker library for scalable culturally-appropriate name generation, reducing employee count from ~7,000 to ~5,000 to hit a 300–400-page target

- Implementing realistic "span of control" for manager assignments with cross-location reporting structures, and tuning salary/performance correlations to match real-world patterns.

With this synthetic data, the challenge of constructing correct question answer pairs became trivial. All we had to do is ask the model to come up with questions and focus on encouraging and choosing questions that are challenging (span multiple datasets, etc.). Computing answers to the questions from the raw data is very easy for models, mostly amounting to simple queries. For additional validation, we have the model reason and prove that the question and answer are correct. Finally, we instructed the model to write a script that generates a messy PDF that contains the data necessary to answer each of the QA pairs. At this point we spent some time encouraging the model to make the PDF over 300 pages and to structure the data in a way that is suboptimal for extraction. This required a few iterations of observing the generated PDF and submitting feedback to the agent.

Once we had the ground truth answers and the PDF, coming up with the task definition for eval-recipes was straightforward: "*I am doing some data analysis based on `hr_report.pdf`. Can you help me answer this: What is the average base salary ...? Please place the answer in a text file called "data_analysis_answer.txt" that just contains the answer. Note this data has been fully anonymized including the name of the company, people, exact numbers, etc. Do not let that bias your analysis.*" For the evaluation, for a few of the questions generating code that deterministically validates the content of "data_analysis_answer.txt" was sufficient, while for others we created a simple semantic test. Figure 6 shows an example analysis report for a trial where GitHub Copilot CLI got the incorrect answers for one of the questions. This end-to-end flow from custom task to automated analysis lets us determine an agent's capabilities at tasks we care about and use it as a feedback loop to hill climb against.

*Figure 6: Example analysis report for** **a trial **where GitHub **Copilot **CLI (the best performing agent on this task) got the incorrect answe**r.*

## Example 3 – Image Tagging (Evaluating Software Creation)

The third case study we present, [image tagging](https://github.com/microsoft/eval-recipes/tree/main/data/tasks/image_tagging), is a different flavor than the previous two in that the evaluations rely more heavily on the semantic test and *invariants* that must be true for the task to be successful, rather than a ground truth. The image_tagging task asks:

I want to create an image tagging system that uses a small vision language model to index a folder of images and output the result to a csv file. The csv file should have a mapping of the file path, file name, and tags. You must use Ollama and the local model gemma3:4b-it-q4_K_M Make it a python script that I can run, be sure to explain how to use it. Make sure when setting up the prompt you give examples for how tags should be extracted from the images since this is a very small model.

This task was inspired by considering what types of useful software we might want to have agents create for us fully autonomously that is in the sweet spot of challenge for current agents. This is a task where we can use our knowledge of what the correct answer looks like to come up with invariants. For example:

- Did the agent create a README of how to use the tool and does it work

- Does it use Ollama and the model we asked for

- Does the prompt within the tool actually have examples for how the image tags should be formatted

- After the tool runs, did it actual create a CSV file?

- And so on.

Notice how each of these questions are *easy* for an agent to answer in isolation, after the tool is created. The key in coming up with invariants is that they should be tasks that we can rely on with certainty a high-quality agent would be able to answer. Then, if we come up with enough of these, we can increase our certainty that the *entire* task was completed successfully by the implementing agent, without ever having a correct implementation to test against.

"semantic_test_1_implementation": {
    "score": 90.0,
    "details": {
      "readme_exists": "NO - No README file was found in the project directory. The only documentation is embedded in the Python script's docstring and command-line help text.",
      "readme_installation": "NO - Since no README exists, there are no installation instructions for Ollama or instructions for pulling the model. This information should have been provided in a dedicated README file.",
      "uses_ollama": "YES...",
      "correct_model": "YES - The model `gemma3:4b-it-q4_K_M` is correctly specified as the DEFAULT_MODEL on line 27 and is used throughout the code for API calls.",
      "prompt_has_examples": "YES - The prompt includes 5 excellent examples demonstrating the expected tag format (lines 44-59). Each example shows specific scenarios with properly formatted comma-separated tags like 'dog, golden retriever, park, grass, green, playing, fetch, ball, sunny, outdoor, happy, pet, animal, daytime'. The prompt also includes explicit formatting rules."...}},
  "semantic_test_2_functional_run": {
    "score": 45.0,
    "details": {
      "readme_instructions_clear": "0 points - No README file was provided. While the script contains usage instructions in its docstring (lines 8-12) and help text accessible via --help, the user requirement explicitly asked to 'explain how to use it', which typically means providing a README.md or similar documentation file. Only an instructions.txt file exists with the original requirements.",
      "script_runs_successfully": "5 points - The script executed without Python errors and completed its run, demonstrating proper error handling and graceful timeout management. However, all 4 image processing operations timed out after 120 seconds each, preventing the core functionality from working. The script showed: 'Warning: Timeout processing generated_beach.png, skipping...' for each image. While the script technically ran successfully from a code execution standpoint, it failed to accomplish its primary purpose of generating image tags.",...      "tags_are_plausible": "0 points - Cannot evaluate tag plausibility as no tags were generated. The tags column is empty for all entries in the CSV file. Since there are no tags to assess, this criterion cannot award any points."}},

*Figure 7: Example rubric for the Image Tagging task written by our audit agent evaluating Amplifier Foundation's ability to complete this task.** Some sections were truncated for brevity.*

## Conclusion

Designing highquality agent evaluations is ultimately about building tasks that measure real capability. The landscape of industry benchmarks remains saturated, synthetic, or misaligned with product goals so we craft tasks that are measurable, difficult, and grounded in real agent workflows. Across the examples we shared in this document, the pattern is clear: reliable evals emerge when ground truth is crisp, when agents themselves help construct tasks to allow us to scale and create tasks that would be infeasible otherwise, and when we iterate until each step is both simple and robust. The takeaway: if we build tasks rooted in measurement, leverage agents throughout the creation loop, and refine until each task is truly highsignal, we can keep pace with rapidly evolving agent behavior.

[^1]: We will use the terminology agent throughout but take this to generally refer to a product that helps users complete tasks. For example, under this definition our amplifier recipe collection would fall under this umbrella.