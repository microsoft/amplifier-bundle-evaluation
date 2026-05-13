# Rubric Design

A rubric is a checklist of specific, observable properties of the output, each weighted by how much it matters. Its job is to separate genuinely high-quality work from competent-looking slop. It is not a report card on whether the agent produced something.

## The Floor Has Moved

Modern agents rarely produce broken output. They produce *plausible* output that ticks the obvious boxes. A rubric that spends most of its scoring range on broken-vs-not-broken gradations has nothing left to say about the difference between "passable" and "actually good."

The working assumption for every criterion you write:

- The agent will produce output that looks reasonable on a quick read.
- It will hit the surface-level requirements stated in the instructions.
- It will create the files, run the commands, and emit the formats.

A criterion that only checks for that surface layer is dead weight. The rubric needs to push past it.

## The Pattern

A rubric is a flat mapping of named criteria. Each criterion has:

- A unique snake_case key
- A point allocation (positive integer)
- A specific, observable question about the output

Points sum to 100. The score is the sum of points earned across criteria. There are no 1-to-5 levels. Discrimination comes from criteria phrasing and weight allocation.

Reference shape from eval-recipes:

```python
RUBRIC_EDITABILITY = {
    "uses_placeholders": (
        "str - (35 points) CRITICAL: Does the PowerPoint use proper placeholders/text frames "
        "instead of absolutely positioned text boxes? This is THE key requirement from the instructions."
    ),
    "slide_count_correct": "str - (10 points) Does the slide count match the markdown structure (--- separators)?",
    "titles_correct": "str - (10 points) Are slide titles properly extracted from # headers?",
    "actually_editable": (
        "str - (10 points) Can text be easily moved and edited like a normal PowerPoint slide "
        "by non-technical users?"
    ),
    "content_preserved": "str - (10 points) Are markdown bullets, formatting, and tables preserved in the output?",
    "proper_layouts": "str - (15 points) Does the tool use slide layouts (title, content) appropriately?",
    "file_opens": "str - (10 points) Does the generated .pptx open without errors?",
    "score": "float - Score between 0 and 100. Sum the points earned from each criterion.",
}
```

One CRITICAL criterion holds 35% of the score because it encodes the make-or-break requirement from the instructions. The trivial-but-required checks (file opens, slide count) hold 10 each. The rubric is opinionated about what matters.

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

### Step 3: Allocate points by discriminating power

Distribute 100 points. The 2 or 3 criteria identified in Step 1 should hold at least 50 points combined. Trivial-but-required checks (file exists, script runs without crashing) get 5 to 10 points each. They earn their place by gating, not by separating quality.

Mark heavy-weighted criteria with `CRITICAL:` in the question text. That signals to the judge agent that this criterion encodes a make-or-break requirement and the rubric author wants partial credit treated strictly.

### Step 4: Split into multiple rubrics when phases differ

For tasks that require both static-artifact checks (the code is structured right, the prompts contain what they should) and dynamic-behavior checks (the script actually works end-to-end with real inputs), split into two rubrics with weighted aggregation.

Typical shape:

- **Implementation rubric**: structural checks. Easier for agents to pass.
- **Functional run rubric**: end-to-end execution against real inputs. Where the real discrimination happens.

Weight the harder phase more:

```python
final_score = result_implementation.score * 0.40 + result_functional.score * 0.60
```

Do not split for the sake of splitting. A single rubric is correct for tasks without a functional run phase.

### Step 5: Calibrate against two example outputs

Before locking the rubric:

1. Hold one genuinely high-quality output in mind, and one "competent slop" output (work that ticks the obvious boxes but misses the substance).
2. Walk both through the draft rubric and tally the scores.
3. If the gap is less than 30 points, the rubric is not discriminating. Find which criterion the slop is getting credit for that it should not, and tighten it.
4. Re-walk until the gap reflects the actual quality difference.

If you do not have two example outputs, generate them: have an agent produce one quick first-pass attempt (the slop) and one careful attempt with all hints made explicit (the high-quality reference). Score both. Iterate.

## Important Principles

1. **Cut criteria that everyone passes.** If everything can ace a criterion, it does not belong in the rubric. The point allocation is better spent on something that actually matters to the user experience.

2. **One criterion, one observable property.** "Does the README explain installation and usage and include examples?" should be three criteria. Compound criteria hide partial credit and obscure which failure mode triggered the score loss.

3. **Critical criteria stay concentrated.** If the instructions said "X is required," that becomes one criterion worth 25 to 40 points. Do not dilute by scattering it across three small criteria.

4. **Phrase for the judge, not the author.** The judge agent reads the criterion and produces a string explanation followed by a point award. Write criteria that make the judge's job mechanical: the evidence for full points, partial points, or zero should be obvious from looking at the artifact.

## Output Format

A rubric is a flat mapping (Python dict or YAML) where each entry is a criterion. The final entry is always a `score` field instructing the judge to sum earned points.

### Python dict form (used by `semantic_test`)

```python
RUBRIC = {
    "<criterion_key>": "str - (<points> points) <Specific observable question with concrete details>",
    # ... more criteria, all points summing to 100
    "score": "float - Score between 0 and 100. Sum the points earned from each criterion.",
}
```

### YAML form (for stored rubric files)

```yaml
rubric:
  version: "1.0"
  project: image-tagging
  description: Implementation and functional-run rubric for the image tagging task

  tests:
    - name: implementation
      weight: 40                # percent of final score (weights across tests sum to 100)
      criteria:
        - key: prompt_has_examples
          points: 25
          critical: true
          question: >
            Does the prompt include at least 3 distinct examples showing the exact tag format
            (e.g. 'outdoor, sunset, mountain, landscape')? A single generic example does not count.
        - key: uses_ollama
          points: 20
          question: Does the code use Ollama for image tagging?
        # ... criteria points sum to 100

    - name: functional_run
      weight: 60
      criteria:
        - key: script_runs_successfully
          points: 25
          question: Does the script run without errors when given the test images directory?
        # ... criteria points sum to 100
```

### Constraints

- All criterion keys are unique snake_case
- All criterion `points` values are positive integers
- Within each test (or within a single-test rubric), `points` sum to exactly 100
- The `score` field is always present in the Python form; in YAML it is implied by the schema
- 5 to 10 criteria per rubric is typical; more than 15 usually means several can be merged
- Prefix critical criteria with `CRITICAL:` in the question text
- When splitting into multiple tests, the test `weight` values sum to 100

## Example: Image Tagging Implementation Rubric

```python
RUBRIC_IMPLEMENTATION = {
    "prompt_has_examples": (
        "str - (25 points) CRITICAL: Does the prompt include at least 3 distinct examples "
        "showing the exact tag format (e.g. 'outdoor, sunset, mountain, landscape')? "
        "A single generic example does not count."
    ),
    "uses_ollama": "str - (20 points) Does the code use Ollama for image tagging?",
    "correct_model": "str - (20 points) Is the model `gemma3:4b-it-q4_K_M` specified in the code?",
    "csv_output_structure": "str - (15 points) Does the CSV output have columns: file_path, file_name, tags?",
    "folder_input": "str - (10 points) Can the script accept a folder path as a CLI argument?",
    "readme_installation": "str - (5 points) Does the README explain how to install Ollama and pull the model?",
    "readme_exists": "str - (5 points) Does a README exist?",
    "score": "float - Score between 0 and 100. Sum the points earned from each criterion.",
}
```

Why these weights:

- `prompt_has_examples` (25): the requirement most often missed by agents that skim the instructions. The "at least 3 distinct examples" specificity blocks single-example slop from getting full credit.
- `uses_ollama` and `correct_model` (20 each): gate criteria. Get these wrong and the rest is moot, but they are also the kind of thing a competent agent gets right. The points are there to keep the score honest, not to discriminate.
- `csv_output_structure` (15): specific column requirement. Moderate discrimination value.
- `folder_input` (10): easy to satisfy, easy to verify.
- README criteria (5 each): trivial to confirm, not where quality lives.

The rubric concentrates 25 points on the one criterion that actually distinguishes careful work from a quick first pass. A surface-reader agent scores around 50 to 60. A careful agent scores 90+.
