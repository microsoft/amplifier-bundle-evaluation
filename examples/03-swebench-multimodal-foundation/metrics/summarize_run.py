#!/usr/bin/env python3
"""Render a human-readable summary of a captured run.

Writes the summary as `verdict-resolved.md` or `verdict-unresolved.md` at the
run-dir root so a casual `ls` immediately shows the outcome. The two
polarities are mutually exclusive; the stale one is removed when present.

Usage:
    python3 metrics/summarize_run.py <run-dir>
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_metrics import extract  # noqa: E402


def _read_analysis(run_dir: Path) -> tuple[str | None, dict]:
    """Return (analysis_markdown_text, analysis_metadata_dict)."""
    md_path = run_dir / "analysis" / "ANALYSIS.md"
    meta_path = run_dir / "analysis" / "analysis_metadata.json"
    text = md_path.read_text() if md_path.exists() else None
    meta: dict = {}
    if meta_path.exists():
        try:
            import json

            meta = json.loads(meta_path.read_text())
        except Exception:
            meta = {}
    return text, meta


def render(data: dict, run_dir: Path) -> str:
    resolved = data["verdict"]["resolved"]
    verdict_word = "RESOLVED" if resolved else "UNRESOLVED"
    instance = data["instance"]
    verdict = data["verdict"]
    solver = data["solver"]
    grader = data["grader"]
    meta = data["meta"]
    analysis_md, analysis_meta = _read_analysis(run_dir)

    solver_sess = solver.get("session", {}) or {}
    solver_tokens = (
        solver_sess.get("root_tokens", {}) if isinstance(solver_sess, dict) else {}
    )
    tool_mix = solver_sess.get("tool_mix", {}) if isinstance(solver_sess, dict) else {}
    tool_mix_str = (
        ", ".join(f"{name}: {count}" for name, count in tool_mix.items()) or "(none)"
    )

    f2p = verdict.get("fail_to_pass", {}) or {}
    p2p = verdict.get("pass_to_pass", {}) or {}
    f2p_pass = f2p.get("success_count", 0)
    f2p_total = f2p_pass + f2p.get("failure_count", 0)
    p2p_pass = p2p.get("success_count", 0)
    p2p_total = p2p_pass + p2p.get("failure_count", 0)

    patch = solver.get("patch", {}) or {}

    parts: list[str] = []
    parts.append(f"# Verdict: {verdict_word}\n")
    classification = analysis_meta.get("classification") or "(no analysis)"
    summary = analysis_meta.get("summary") or ""
    parts.append("```")
    parts.append(f"Instance id:     {instance.get('id')}")
    parts.append(f"Repo:            {instance.get('repo')}")
    parts.append(f"Base commit:     {instance.get('base_commit')}")
    parts.append(f"Version:         {instance.get('version')}")
    parts.append(f"Images in issue: {instance.get('image_count')}")
    parts.append(f"Classification:  {classification}")
    parts.append("```\n")
    if summary:
        parts.append(f"> {summary}\n")

    # Plain-English explainer of what "resolved" means. Anyone unfamiliar
    # with SWE-bench will see this once and know how to read the rest.
    if resolved:
        parts.append(
            "**What this means:** the agent produced a code patch that fixed the bug. "
            "Specifically: every test the original PR added to prove the fix works now passes, "
            "and every test that was already passing before the fix still passes (no regressions).\n"
        )
    else:
        parts.append(
            "**What this means:** the agent did NOT fix the bug to the harness's satisfaction. "
            "Either one of the tests the original PR added to prove the fix works still fails, "
            "or the agent's changes broke a test that was previously passing.\n"
        )

    # Inline the analyzer's ANALYSIS.md as the primary narrative content.
    if analysis_md:
        parts.append("## Analysis\n")
        parts.append("_From the post-run analyzer (separate amplifier session). See `analysis/ANALYSIS.md` for the canonical file._\n")
        parts.append(analysis_md.strip())
        parts.append("")
    else:
        parts.append("## Analysis\n")
        parts.append("_The post-run analyzer did not produce ANALYSIS.md. See `analysis/stdout.txt`._\n")

    parts.append("## Test results\n")
    parts.append(
        "_The harness runs two test sets against the agent's patch. The fix-verification "
        "set comes from the original PR's `test_patch` (these tests fail on the base "
        "commit and must pass after the fix). The regression set is tests that were "
        "already passing (they must still pass)._\n"
    )
    parts.append("```")
    parts.append(
        f"Fix-verification tests (FAIL_TO_PASS):  {f2p_pass}/{f2p_total} passed"
    )
    if f2p.get("failure"):
        parts.append("  still failing after agent's patch:")
        for name in f2p["failure"][:10]:
            parts.append(f"    - {name.strip()}")
        if len(f2p["failure"]) > 10:
            parts.append(f"    ... and {len(f2p['failure']) - 10} more")
    parts.append(
        f"Regression tests       (PASS_TO_PASS):  {p2p_pass}/{p2p_total} passed"
    )
    if p2p.get("failure"):
        parts.append("  broken by agent's patch:")
        for name in p2p["failure"][:10]:
            parts.append(f"    - {name.strip()}")
        if len(p2p["failure"]) > 10:
            parts.append(f"    ... and {len(p2p['failure']) - 10} more")
    parts.append(f"Patch applied cleanly:                  {verdict.get('patch_successfully_applied')}")
    parts.append(f"Patch was empty (agent produced none):  {verdict.get('patch_was_empty')}")
    parts.append("```\n")

    parts.append("## What the agent changed\n")
    parts.append("```")
    if patch.get("missing"):
        parts.append("(no patch.diff produced)")
    elif patch.get("empty"):
        parts.append("(empty patch — agent did not edit any files)")
    else:
        parts.append(f"files changed:  {patch.get('files_changed', 0)}")
        for f in (patch.get("files") or [])[:10]:
            parts.append(f"  - {f}")
        if len(patch.get("files") or []) > 10:
            parts.append(f"  ... and {len(patch['files']) - 10} more")
        parts.append(f"lines added:    {patch.get('lines_added', 0)}")
        parts.append(f"lines removed:  {patch.get('lines_removed', 0)}")
        parts.append(f"patch chars:    {patch.get('patch_chars', 0)}")
    parts.append("```\n")

    parts.append("## How the agent worked (solver session stats)\n")
    parts.append("```")
    parts.append(f"session id:    {solver.get('session_id')}")
    parts.append(f"wall (meta):   {solver.get('wall_seconds_meta')}s")
    parts.append(f"exit code:     {solver.get('exit_code')}")
    parts.append(
        f"tool calls:    {solver_sess.get('tool_call_count', 0)} ({tool_mix_str})"
    )
    parts.append(f"delegations:   {len(solver_sess.get('delegations', []) or [])}")
    parts.append(
        "root tokens:   "
        f"{solver_tokens.get('input', 0):,} in / "
        f"{solver_tokens.get('output', 0):,} out / "
        f"{solver_tokens.get('cache_read', 0):,} cache_read"
    )
    parts.append("```\n")

    parts.append("## How the patch was graded (swebench harness)\n")
    parts.append("```")
    parts.append(f"run id:        {grader.get('harness_run_id')}")
    parts.append(f"wall:          {grader.get('wall_seconds')}s")
    parts.append(f"exit code:     {grader.get('exit_code')}")
    parts.append("```\n")

    parts.append("## Reproducibility\n")
    parts.append("```")
    parts.append(
        f"foundation:    {meta.get('foundation_branch')} @ {meta.get('foundation_sha')}"
    )
    parts.append(
        f"pinned id:     swebench/PINNED_INSTANCE_ID (this run id: {instance.get('id')})"
    )
    parts.append(f"ran at:        {meta.get('ran_at')}")
    parts.append("```\n")

    parts.append("## Artifacts\n")
    parts.append("```")
    parts.append(
        "sample/instance.json                       full SWE-bench record incl. gold patch + test_patch"
    )
    parts.append(
        "sample/problem_statement.md                what got pushed into the DTU"
    )
    parts.append("solver/patch.diff                          agent's git diff (graded)")
    parts.append("solver/stdout.txt                          amplifier-run stdout")
    parts.append(
        "solver/sessions/sessions/<sid>/            solver events.jsonl, transcript.jsonl"
    )
    parts.append("grader/verdict.json                        parsed verdict")
    parts.append(
        "grader/predictions.jsonl                   what we fed to the harness"
    )
    parts.append(
        "grader/harness_stdout.txt                  full swebench harness stdout"
    )
    parts.append(
        "grader/harness_report.json                 raw harness per-instance report"
    )
    parts.append(
        "grader/summary.json                        raw harness top-level summary"
    )
    parts.append("```\n")

    return "\n".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: summarize_run.py <run-dir>", file=sys.stderr)
        sys.exit(2)

    run_dir = Path(sys.argv[1])
    data = extract(run_dir)
    resolved = data["verdict"].get("resolved")
    polarity = "resolved" if resolved else "unresolved"
    out_name = f"verdict-{polarity}.md"

    stale = run_dir / ("verdict-unresolved.md" if resolved else "verdict-resolved.md")
    if stale.exists():
        stale.unlink()

    text = render(data, run_dir)
    (run_dir / out_name).write_text(text)
    print(f"[summarize_run] wrote {run_dir / out_name}", file=sys.stderr)


if __name__ == "__main__":
    main()
