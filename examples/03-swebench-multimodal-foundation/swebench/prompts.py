"""Prompts for the SWE-bench Multimodal foundation evaluation."""

SOLVER_PROMPT = """\
You are resolving a real GitHub issue in a JavaScript codebase.

Read the issue at /work/swe-task/problem_statement.md.

The repository is at /work/swe-task/repo/, already checked out to the buggy \
commit. Edit files in that directory to resolve the issue. Do NOT commit \
your changes -- we extract them via `git diff`. Do NOT modify files outside \
/work/swe-task/repo/.

You may fetch image URLs referenced in problem_statement.md to understand \
the bug visually. Do NOT search the web for the fixing pull request or the \
project's issue tracker -- that would defeat the benchmark.

Treat me as if I am asleep -- I am not here to answer questions, only to \
read your output and grade your patch afterwards.

When you believe the issue is fixed, stop. We will run the project's test \
suite on your changes."""


def build_solver_prompt() -> str:
    return SOLVER_PROMPT
