# Rubric Design

A rubric is a checklist of specific, observable properties of the output, each weighted by how much it matters. Its job is to separate genuinely high-quality work from competent-looking slop. It is not a report card on whether the agent produced something.

## The Floor Has Moved

Modern agents rarely produce broken output. They produce *plausible* output that ticks the obvious boxes. A rubric that spends most of its scoring range on broken-vs-not-broken gradations has nothing left to say about the difference between "passable" and "actually good."

The working assumption for every criterion you write:

- The agent will produce output that looks reasonable on a quick read.
- It will hit the surface-level requirements stated in the instructions.
- It will create the files, run the commands, and emit the formats.

A criterion that only checks for that surface layer is dead weight. The rubric needs to push past it.

## The shape of a rubric

A rubric is a flat set of named criteria. Each criterion has:

- a unique short name
- a point value, which is its relative weight
- an observable question about the output

A judge scores each criterion by awarding points up to its maximum, and the rubric's score is the points awarded divided by the points possible. Discrimination comes entirely from which criteria you choose and how you weight them. The points need not sum to any particular total: a round total like 100 lets each criterion read as a percentage, but a single binary check can be one 1-point criterion.

How a specific harness stores, runs, and aggregates rubrics is a separate concern. The methodology below is harness-agnostic; the amplifier-evaluation grader schema is worked through at the end of this document as one concrete home for a rubric.

## Your Process

### Step 1: Identify what separates high quality from average

Before writing any criteria, name the 2 or 3 things that distinguish a genuinely good run on this task from a competent-looking mediocre one. These are usually:

- A subtle requirement embedded in the instructions that surface-readers miss (e.g. "use placeholders, not absolute positioning")
- A behavior that requires the agent to go beyond literal interpretation (e.g. "the prompt must include 3+ examples covering different image types, not a single generic example")
- A failure mode observed in real runs (e.g. "the README explains how to run the script but never how to install the model")

These become the heavy-weighted criteria. Everything else is either a gate or filler.

### Step 2: Write each criterion as an observable question

Each criterion is something the judge can answer by looking at the artifact. The phrasing matters.

Fuzzy:
- "Is the README good?"
- "Are the examples clear?"
- "Is the code well-structured?"

Observable:
- "Does the README include all of: (a) installation steps, (b) model pull command, (c) example invocation, (d) expected output format?"
- "Does the prompt include at least 3 distinct examples showing the exact tag format (e.g. 'outdoor, sunset, mountain, landscape')? A single generic example does not count."
- "Are public functions documented with docstrings stating purpose and return type?"

If you cannot rephrase a criterion into something concrete and pointable, the criterion is asking for inference, not observation. Find the observable property behind the inference, or cut it.

Push the phrasing all the way to mechanical wherever you can:

- **For industry-benchmark-style tasks with an explicit known answer, score by a tolerance band, not by eyeball.** When the task has a single correct value to check against, give the judge the band that earns credit: "within 1% of 1,531,989.62", "0 to 5 character differences by edit distance", "tempo within 60 to 100 BPM". The judge compares against a rule instead of forming an opinion. This does not apply to open-ended tasks with no canonical answer.
- **For capability criteria, demand evidence the behavior actually fired**, not that it was claimed: "verify real API calls were made, not just a prompt constructed"; "the dependency is both declared and imported." The strongest form is a differential check: two contrasting outputs must differ in the expected direction (a "boss battle" track outpaces a "melancholy" one), which proves the input actually controls the result.
- **Name what NOT to penalize**, so acceptable variation does not quietly cost points: "wording need not match exactly", "a direct API call or an Agent SDK are both fine", "for a small model, generic-but-plausible output is acceptable; do not penalize inaccuracy."

### Step 3: Allocate points by discriminating power

Points are relative weights; the score is the points awarded divided by the total available. A round total like 100 keeps each criterion readable as a percentage. The 2 or 3 criteria identified in Step 1 should hold at least half the total combined. Trivial-but-required checks (file exists, script runs without crashing) get a small slice each. They earn their place by gating, not by separating quality.

Mark heavy-weighted criteria with `CRITICAL:` in the criterion text. That signals to the judge that this criterion encodes a make-or-break requirement and partial credit should be treated strictly.

Where a criterion allows partial credit, spell out how that partial credit is earned in its text so the judge does not invent its own scale: "full credit for 75%+ coverage, proportional below"; "25 points for gradient boosting, 5 for linear regression, 0 for no model." A negative-points criterion can cap a failure mode the task invites, such as penalizing output that over-extracts beyond a threshold.

### Step 4: Pair the rubric with an evidence-gathering plan

A criterion is only observable if the judge actually gathers the evidence for it. Every rubric needs a companion plan for what the judge does before scoring: which files to read, which commands to run, what to inspect. If a criterion asks "does the script run without errors on the test images," the plan must actually run it. Write the plan and the rubric together so every criterion maps to something the plan produces. A few tactics keep that plan mechanical:

- **Gate execution-dependent criteria on failure.** State the conditions that force a zero: a missing or empty deliverable, a tool that errored, a run that blew its time budget ("if the script fails or times out after 15 minutes, score 0 for this pass"). Otherwise the judge awards sympathy points to work that never ran.
- **Turn perception into a script the judge runs.** When a property is hard to judge by reading (audio, images, structural validity), stage a helper that emits machine-readable output and have the plan run it; the rubric keys off its fields. Say so plainly: "since you cannot listen to audio, use the analysis script as a proxy."
- **Look up values that drift.** For answers that go stale (model names, prices), have the plan check a live source rather than hardcoding a list.

When a criterion needs a reference the solver must not see (an answer key, expected output, a scoring helper), keep it out of the solver's environment and supply it only to the judge, scoped to it ("only evaluate whether these specific items were found; do not penalize for extras"). For tasks that emit facts, verify claims against a live source or an HTTP 200 and score fabrication down explicitly. How a harness wires the hidden reference up is harness-specific; the grader does it with `steps` and `mounts`, shown in the worked example.

### Step 5: Split into multiple scored passes when phases differ

For tasks that require both static-artifact checks (the code is structured right, the prompts contain what they should) and dynamic-behavior checks (the script actually works end-to-end with real inputs), use two separately-scored rubrics with weighted aggregation rather than one overloaded rubric.

Typical shape:

- An **implementation** pass: structural checks. Easier for agents to pass.
- A **functional run** pass: end-to-end execution against real inputs. Where the real discrimination happens.

Weight the harder phase more (for example 0.4 and 0.6). Each pass is scored independently, then combined by relative weight.

Do not split for the sake of splitting. A single rubric is correct for tasks without a functional run phase.

### Step 6: Calibrate against two example outputs

Before locking the rubric:

1. Hold one genuinely high-quality output in mind, and one "competent slop" output (work that ticks the obvious boxes but misses the substance).
2. Walk both through the draft rubric and tally the scores.
3. If the gap is less than 30 points, the rubric is not discriminating. Find which criterion the slop is getting credit for that it should not, and tighten it.
4. Re-walk until the gap reflects the actual quality difference.

If you do not have two example outputs, generate them: have an agent produce one quick first-pass attempt (the slop) and one careful attempt with all hints made explicit (the high-quality reference). Score both. Iterate.

## Reading the result: watch for ceiling effects

A comparison can only detect a difference when both runs have room to move on the scale. Before reporting a verdict, check where the scores fall on the scale, not just whether they differ.

- **Equal scores near the top of the scale are inconclusive, not evidence that there is no difference.** If the control and treatment both score 0.95, that does not show the rubric failed to measure a difference. It shows the scores landed close to the maximum, with no room left to register one. Ask whether a clearly better run could have scored higher here. If it could not, the task or the rubric is too easy, and the result supports no conclusion either way. Treat equal high scores as a sign the task needs to be harder, not as a finding to report.
- **Equal scores in the middle of the scale are a real result.** Two runs that both land near 0.6 on a hard task have been measured and found comparable, which is informative. A tie is only inconclusive when the scores sit at the top or bottom of the scale, where neither run had room to separate.

This is the Step 6 calibration check applied to the live run rather than to two sample outputs. Step 6 checks that the rubric can separate strong work from weak work; this checks that the task left enough room on the scale for that separation to appear.

## Important Principles

1. **Cut criteria that everyone passes.** If everything can ace a criterion, it does not belong in the rubric. The point allocation is better spent on something that actually matters to the user experience.

2. **One criterion, one observable property.** "Does the README explain installation and usage and include examples?" should be three criteria. Compound criteria hide partial credit and obscure which failure mode triggered the score loss.

3. **Critical criteria stay concentrated.** If the instructions said "X is required," that becomes one criterion worth 25 to 40 points. Do not dilute by scattering it across three small criteria.

4. **Phrase for the judge, not the author.** The judge agent reads the criterion and produces a string explanation followed by a point award. Write criteria that make the judge's job mechanical: the evidence for full points, partial points, or zero should be obvious from looking at the artifact.

## Worked example: the amplifier-evaluation grader

This is one concrete home for a rubric. The amplifier-evaluation library's grader reads a `grader.yaml` and parses it into one or more weighted evaluations (`grader/schema.py`). Each evaluation pairs a rubric with the `steps` the judge follows inside the Digital Twin Universe to gather evidence.

How the generic concepts above map onto this schema:

- **Criteria** become a `rubric` mapping keyed by snake_case name. Each criterion has a positive-integer `points` and a `description` (the observable question). There is no `score` field and no `critical:` field: the grader computes the score, and the parser ignores any key other than `points` and `description`. Put `CRITICAL:` in the `description`.
- **Points and weights** are scored by `grader/grader.py`: per evaluation, `score = points_awarded / total_points`; overall is the weighted average `sum(score * weight) / sum(weight)`, so weights are relative (`0.4`/`0.6` equals `2`/`3`).
- **The evidence-gathering plan** is the `steps` field. The criterion keys and per-criterion max points are compiled into the `submit_rubric` tool's input schema (`grader/tools.py`), so the judge returns a `points_awarded` (clamped to `[0, points]`) and a `reasoning` string for every criterion.
- **References hidden from the solver** are `mounts`: each copies `grader-data/<source>` to a `destination` inside the DTU before the judge runs.

### Single evaluation with a hidden answer key

```yaml
evaluations:
  - name: answer_correctness
    weight: 1.0
    mounts:
      - source: reference.json          # resolved under the task's grader-data/
        destination: /grader/reference.json
    steps: |
      1. Read the solver's answer from /workspace/answer.txt.
      2. Read the reference answer from /grader/reference.json (mounted above).
      3. Compare; award the point only on an exact or numerically-equivalent match.
    rubric:
      answer_correct:
        points: 1
        description: >
          Does the solver's final answer match the reference? Score 0 if the
          answer file is missing, ambiguous, or wrong.
```

### Two phases, weighted

```yaml
evaluations:
  - name: implementation
    weight: 0.4
    steps: |
      Explore the project directory. Read the main script and any README, then
      verify the model, prompt examples, CLI input, and CSV output shape.
    rubric:
      prompt_has_examples:
        points: 25
        description: >
          CRITICAL: Does the prompt include at least 3 distinct examples showing
          the exact tag format (e.g. 'outdoor, sunset, mountain, landscape')?
          A single generic example does not count.
      uses_ollama:
        points: 20
        description: Does the code use Ollama for image tagging?
      correct_model:
        points: 20
        description: Is the model `gemma3:4b-it-q4_K_M` specified in the code?
      csv_output_structure:
        points: 15
        description: 'Does the CSV have columns: file_path, file_name, tags?'
      folder_input:
        points: 10
        description: Can the script accept a folder path as input?
      readme_installation:
        points: 5
        description: Does the README explain how to install Ollama and pull the model?
      readme_exists:
        points: 5
        description: Does a README exist?

  - name: functional_run
    weight: 0.6
    steps: |
      Start Ollama if needed, run the script against the test images directory,
      then read the generated CSV and check its rows and tag quality.
    rubric:
      script_runs_successfully:
        points: 25
        description: Does the script run without errors on the test images directory?
      # ... remaining criteria
```

This is the real `image_tagging` grader (`amplifier-benchmark/tasks/image_tagging/grader.yaml`); read it in full for a complete two-phase rubric.

Why these weights: `prompt_has_examples` (25) is the requirement most often missed by agents that skim the instructions, and the "at least 3 distinct examples" specificity blocks single-example slop from full credit. `uses_ollama` and `correct_model` (20 each) are gate criteria a competent agent gets right; the points keep the score honest rather than discriminate. `csv_output_structure` (15) is a specific column requirement with moderate discrimination value, `folder_input` (10) is easy to verify, and the README criteria (5 each) are trivial to confirm. The implementation pass concentrates points on the one criterion that distinguishes careful work from a quick first pass; the functional run pass (weight 0.6) is where the real discrimination happens, since an agent that never runs its own script scores far lower there than on the structural checks.

### Schema constraints

- Criterion keys are unique snake_case within an evaluation
- `points` is a positive integer; the per-evaluation total is whatever you choose
- `weight` is a float; weights are relative and need not sum to anything
- There is no `score` field and no `critical:` field; put `CRITICAL:` in the `description`
- `mounts` is optional
