#!/usr/bin/env python3
"""Render a human-readable summary of a captured run.

Writes the summary as `verdict-correct.md` or `verdict-incorrect.md` at the
run-dir root so a casual `ls` immediately shows the outcome. The two
polarities are mutually exclusive; the stale one is removed when present.

Usage:
    python3 metrics/summarize_run.py <run-dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

# Reuse the canonical extractor so we don't duplicate logic.
sys.path.insert(0, str(Path(__file__).parent))
from extract_metrics import extract  # noqa: E402


def render(data: dict) -> str:
    correct = data["verdict"]["correct"]
    verdict_word = "CORRECT" if correct else "INCORRECT"
    sample = data["sample"]
    verdict = data["verdict"]
    solver = data["solver"]
    judge = data["judge"]
    meta = data["meta"]

    solver_sess = solver.get("session", {}) or {}
    judge_sess = judge.get("session", {}) or {}
    solver_tokens = (
        solver_sess.get("root_tokens", {}) if isinstance(solver_sess, dict) else {}
    )
    judge_tokens = (
        judge_sess.get("root_tokens", {}) if isinstance(judge_sess, dict) else {}
    )
    tool_mix = solver_sess.get("tool_mix", {}) if isinstance(solver_sess, dict) else {}
    tool_mix_str = (
        ", ".join(f"{name}: {count}" for name, count in tool_mix.items()) or "(none)"
    )

    parts = []
    parts.append(f"# Verdict: {verdict_word}\n")
    parts.append("```")
    parts.append(f"Sample id:   {sample.get('id')}")
    parts.append(f"Answer type: {sample.get('answer_type')}")
    parts.append(f"Has image:   {'yes' if sample.get('has_image') else 'no'}")
    parts.append("```\n")

    parts.append("## Ground truth\n")
    parts.append("```")
    parts.append(str(sample.get("ground_truth", "")).strip())
    parts.append("```\n")

    parts.append(
        "## Solver final answer (last `ANSWER:` line of `solver/answer.txt`)\n"
    )
    parts.append("```")
    parts.append(
        str(solver.get("final_answer_line") or "(no ANSWER: line found)").strip()
    )
    parts.append("```\n")

    parts.append("## Judge extracted answer\n")
    parts.append("```")
    parts.append(str(verdict.get("extracted_final_answer") or "(none)").strip())
    parts.append("```\n")

    parts.append("## Solver session\n")
    parts.append("```")
    parts.append(f"session id:    {solver.get('session_id')}")
    parts.append(f"wall (meta):   {solver.get('wall_seconds_meta')}s")
    parts.append(f"exit code:     {solver.get('exit_code')}")
    parts.append(
        f"tool calls:    {solver_sess.get('tool_call_count', 0)} ({tool_mix_str})"
    )
    parts.append(f"delegations:   {len(solver_sess.get('delegations', []))}")
    parts.append(
        "root tokens:   "
        f"{solver_tokens.get('input', 0):,} in / "
        f"{solver_tokens.get('output', 0):,} out / "
        f"{solver_tokens.get('cache_read', 0):,} cache_read"
    )
    parts.append("```\n")

    parts.append("## Judge session\n")
    parts.append("```")
    parts.append(f"session id:    {judge.get('session_id')}")
    parts.append(f"wall:          {judge.get('wall_seconds')}s")
    parts.append(
        "root tokens:   "
        f"{judge_tokens.get('input', 0):,} in / "
        f"{judge_tokens.get('output', 0):,} out"
    )
    parts.append("```\n")

    parts.append("## Reproducibility\n")
    parts.append("```")
    parts.append(
        f"foundation:    {meta.get('foundation_branch')} @ {meta.get('foundation_sha')}"
    )
    parts.append(
        f"pinned id:     hle/PINNED_SAMPLE_ID (this run id: {sample.get('id')})"
    )
    parts.append(f"ran at:        {meta.get('ran_at')}")
    parts.append("```\n")

    parts.append("## Artifacts\n")
    parts.append("```")
    parts.append(
        "sample/sample.json                          full HLE record incl. ground truth"
    )
    parts.append(
        "sample/question.md                          what got pushed into the DTU"
    )
    if sample.get("has_image"):
        parts.append(
            "sample/question_image.*                     image pushed into the DTU"
        )
    parts.append("solver/answer.txt                           agent's final answer.txt")
    parts.append("solver/stdout.txt                           amplifier-run stdout")
    parts.append(
        "solver/sessions/sessions/<sid>/             solver events.jsonl, transcript.jsonl"
    )
    parts.append("judge/verdict.json                          parsed verdict")
    parts.append("judge/judge_prompt.txt                      exact judge prompt")
    parts.append(
        "judge/sessions/sessions/<sid>/              judge events.jsonl, transcript.jsonl"
    )
    parts.append("```\n")

    return "\n".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: summarize_run.py <run-dir>", file=sys.stderr)
        sys.exit(2)

    run_dir = Path(sys.argv[1])
    data = extract(run_dir)
    correct = data["verdict"].get("correct")
    polarity = "correct" if correct else "incorrect"
    out_name = f"verdict-{polarity}.md"

    # Remove any stale opposite-polarity file so re-runs don't keep both.
    stale = run_dir / ("verdict-incorrect.md" if correct else "verdict-correct.md")
    if stale.exists():
        stale.unlink()

    text = render(data)
    (run_dir / out_name).write_text(text)
    print(f"[summarize_run] wrote {run_dir / out_name}", file=sys.stderr)


if __name__ == "__main__":
    main()
