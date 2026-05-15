"""Prompts for the SWE-bench portion of the demo (language-agnostic).

Supports both SWE-bench Multimodal (JS, with image assets in problem_statement)
and SWE-bench Verified (Python, no image assets). The wording adapts based on
the `dataset` argument.
"""

SOLVER_PROMPT_TEMPLATE = """\
You are resolving a real GitHub issue in a {language} codebase.

Read the issue at /work/task/problem_statement.md.

The repository is at /work/task/repo/, already checked out to the buggy \
commit. Edit files in that directory to resolve the issue. Do NOT commit \
your changes, we extract them via `git diff`. Do NOT modify files outside \
/work/task/repo/.{image_note}

Do NOT search the web for the fixing pull request or the project's issue \
tracker, that would defeat the benchmark.

Treat me as if I am asleep. I am not here to answer questions, only to \
read your output and grade your patch afterwards.

When you believe the issue is fixed, stop. We will run the project's test \
suite on your changes."""

_IMAGE_NOTE_MULTIMODAL = (
    "\n\nYou may fetch image URLs referenced in problem_statement.md to "
    "understand the bug visually."
)

_LANGUAGE = {
    "multimodal": "JavaScript",
    "verified": "Python",
}


def build_solver_prompt(dataset: str = "multimodal") -> str:
    language = _LANGUAGE.get(dataset, "real")
    image_note = _IMAGE_NOTE_MULTIMODAL if dataset == "multimodal" else ""
    return SOLVER_PROMPT_TEMPLATE.format(language=language, image_note=image_note)