#!/usr/bin/env python3
"""Render a per-run verdict.html for one job in example 04.

Inspired by example 03's verdict.html quality: a self-contained HTML page
with a status banner, summary cards, sectioned content, syntax-highlighted
patches (SWE-bench), the original task input collapsed, and a run-metadata
key/value list. Uses inline CSS only (no external assets).

Usage:
    python3 metrics/render_verdict.py <run-dir>

Writes <run-dir>/verdict.html. Called by run_one_job.sh after meta.json is
written. Re-runnable.
"""

from __future__ import annotations

import html as _html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_metrics import extract  # noqa: E402


def _esc(s: object) -> str:
    if s is None:
        return ""
    return _html.escape(str(s))


_DIFF_CLASSES = {
    "@": "diff-hunk",
    "+": "diff-add",
    "-": "diff-del",
}


def _color_diff(diff_text: str) -> str:
    """Return syntax-colored HTML for a unified diff (escapes content)."""
    if not diff_text:
        return ""
    out_lines: list[str] = []
    for raw in diff_text.splitlines():
        if not raw:
            out_lines.append("")
            continue
        if raw.startswith("diff --git") or raw.startswith("index ") \
                or raw.startswith("--- ") or raw.startswith("+++ "):
            cls = "diff-meta"
        elif raw.startswith("@@"):
            cls = "diff-hunk"
        elif raw.startswith("+") and not raw.startswith("+++"):
            cls = "diff-add"
        elif raw.startswith("-") and not raw.startswith("---"):
            cls = "diff-del"
        else:
            cls = ""
        if cls:
            out_lines.append(f'<span class="{cls}">{_esc(raw)}</span>')
        else:
            out_lines.append(_esc(raw))
    return "\n".join(out_lines)


_CSS = r"""
:root {
  --ok: #15803d;
  --ok-bg: #dcfce7;
  --bad: #b91c1c;
  --bad-bg: #fee2e2;
  --warn: #b45309;
  --warn-bg: #fef3c7;
  --muted: #64748b;
  --bg: #f8fafc;
  --card: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --code-bg: #0f172a;
  --code-text: #e2e8f0;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Oxygen, Ubuntu, sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  padding: 2rem 1rem;
  line-height: 1.55;
}
.wrap { max-width: 1100px; margin: 0 auto; }
.crumb { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.75rem; }
.crumb a { color: var(--muted); }
.banner {
  border-radius: 12px;
  padding: 1.5rem 2rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  border: 1px solid var(--border);
}
.banner.ok  { background: var(--ok-bg);  border-color: #86efac; }
.banner.bad { background: var(--bad-bg); border-color: #fca5a5; }
.banner-icon { font-size: 3rem; line-height: 1; }
.banner h1 { margin: 0; font-size: 1.8rem; }
.banner h1 .word-ok  { color: var(--ok); }
.banner h1 .word-bad { color: var(--bad); }
.banner p { margin: 0.3rem 0 0; color: var(--text); }
.tagline { font-style: italic; color: var(--muted); margin-top: 0.4rem; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}
.card .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
.card .value { font-size: 1.1rem; font-weight: 600; margin-top: 0.2rem; word-break: break-word; }
.card.ok   .value { color: var(--ok);   }
.card.bad  .value { color: var(--bad);  }
.card.warn .value { color: var(--warn); }
section {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
}
section > h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.4rem;
}
section .explainer { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.75rem; }
.test-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: center;
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  background: var(--bg);
  margin-bottom: 0.5rem;
}
.test-row .test-label { font-weight: 500; }
.test-row .test-sub   { font-size: 0.85rem; color: var(--muted); }
.pill {
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
}
.pill.ok    { background: var(--ok-bg);   color: var(--ok);   }
.pill.bad   { background: var(--bad-bg);  color: var(--bad);  }
.pill.warn  { background: var(--warn-bg); color: var(--warn); }
.pill.muted { background: #f1f5f9; color: var(--muted); }
details {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  margin-bottom: 0.75rem;
  background: var(--card);
}
details > summary { cursor: pointer; font-weight: 600; }
details[open] > summary { margin-bottom: 0.5rem; }
pre.problem {
  background: var(--bg);
  padding: 0.9rem;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre-wrap;
  font-size: 0.9rem;
  max-height: 600px;
}
.failure-reason {
  background: #fef2f2;
  border-left: 4px solid var(--bad);
  padding: 0.85rem 1rem;
  border-radius: 4px;
  margin: 0;
}
.failure-reason .reason-label {
  font-weight: 700;
  color: var(--bad);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 0.3rem;
}
.failure-reason .reason-mode {
  font-family: ui-monospace, SFMono-Regular, monospace;
  background: var(--bad-bg);
  color: var(--bad);
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  font-size: 0.85rem;
  margin-right: 0.4rem;
}
.patches {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
@media (max-width: 800px) { .patches { grid-template-columns: 1fr; } }
.patches .panel h3 { margin: 0 0 0.5rem; font-size: 1rem; }
.patches .panel pre {
  background: var(--code-bg);
  color: var(--code-text);
  padding: 0.75rem;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.78rem;
  max-height: 500px;
  line-height: 1.4;
  white-space: pre;
}
.diff-add  { color: #4ade80; }
.diff-del  { color: #f87171; }
.diff-hunk { color: #93c5fd; }
.diff-meta { color: #94a3b8; }
.test-list {
  list-style: none;
  padding: 0;
  margin: 0.4rem 0 0 0;
}
.test-list li {
  background: var(--bg);
  border-left: 3px solid var(--border);
  padding: 0.4rem 0.7rem;
  margin-bottom: 0.3rem;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.82rem;
  border-radius: 3px;
  word-break: break-word;
}
.test-list li.fail { border-left-color: var(--bad); }
.test-list li.pass { border-left-color: var(--ok);  }
.footer {
  margin-top: 2rem;
  color: var(--muted);
  font-size: 0.85rem;
  text-align: center;
}
.kv {
  display: grid;
  grid-template-columns: max-content 1fr;
  column-gap: 1.5rem;
  row-gap: 0.3rem;
  font-size: 0.92rem;
  margin: 0;
}
.kv dt { color: var(--muted); font-weight: 500; }
.kv dd { margin: 0; word-break: break-all; }
.compare-table { width: 100%; border-collapse: collapse; }
.compare-table th, .compare-table td {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
  font-size: 0.92rem;
}
.compare-table th { color: var(--muted); font-weight: 500; width: 25%; }
.compare-table td pre {
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  word-break: break-word;
  background: transparent;
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.92rem;
}
"""


def _banner(outcome: bool, benchmark: str, sample_id: str, failure_mode: str | None,
            short_reason: str | None) -> str:
    if benchmark == "hle":
        word_ok, word_bad = "CORRECT", "INCORRECT"
        tagline_ok = (
            "Judge confirmed the agent's extracted answer matches the ground "
            "truth."
        )
    else:
        word_ok, word_bad = "RESOLVED", "UNRESOLVED"
        tagline_ok = (
            "Every fix-verification test passed and no regression test broke. "
            "The agent produced a patch that actually fixes the bug."
        )
    if outcome:
        word = word_ok
        cls = "ok"
        icon = "&#x2705;"
        word_class = "word-ok"
        tagline = tagline_ok
    else:
        word = word_bad
        cls = "bad"
        icon = "&#x274C;"
        word_class = "word-bad"
        tagline = short_reason or "See below for details."
    sub = _esc(sample_id) if sample_id else ""
    return f"""
  <div class="banner {cls}">
    <div class="banner-icon">{icon}</div>
    <div>
      <h1>Verdict: <span class="{word_class}">{word}</span></h1>
      <p><strong>{_esc(failure_mode or word)}</strong>{' &mdash; ' + sub if sub else ''}</p>
      <p class="tagline">{_esc(tagline)}</p>
    </div>
  </div>
"""


def _failure_section(verdict: dict, benchmark: str) -> str:
    if verdict.get("outcome"):
        return ""
    mode = verdict.get("failure_mode") or "failed"
    if benchmark == "hle":
        text = verdict.get("reasoning") or verdict.get("explanation") or ""
        if not text:
            gt = verdict.get("ground_truth") or "?"
            ag = verdict.get("extracted_final_answer") or "(none)"
            text = f"Agent answered {ag}; correct answer was {gt}."
    else:
        text = verdict.get("explanation") or "Patch did not resolve the issue."
    return f"""
  <section>
    <h2>Why this run failed</h2>
    <div class="failure-reason">
      <span class="reason-label">Failure mode</span>
      <span class="reason-mode">{_esc(mode)}</span>
      <span>{_esc(text)}</span>
    </div>
  </section>
"""


def _status_cards_hle(row: dict) -> str:
    sample = row.get("sample") or {}
    verdict = row.get("verdict") or {}
    solver = row.get("solver") or {}
    sess = solver.get("session") or {}
    tokens = sess.get("root_tokens") or {}

    outcome = verdict.get("outcome")
    return f"""
  <div class="cards">
    <div class="card {'ok' if outcome else 'bad'}">
      <div class="label">Outcome</div>
      <div class="value">{'CORRECT' if outcome else 'INCORRECT'}</div>
    </div>
    <div class="card">
      <div class="label">Answer type</div>
      <div class="value">{_esc(sample.get('answer_type'))}</div>
    </div>
    <div class="card">
      <div class="label">Image in question</div>
      <div class="value">{'Yes' if sample.get('has_image') else 'No'}</div>
    </div>
    <div class="card">
      <div class="label">Solver wall</div>
      <div class="value">{_esc(solver.get('wall_seconds'))}s</div>
    </div>
    <div class="card">
      <div class="label">Solver tokens (in / out)</div>
      <div class="value">{tokens.get('input', 0):,} / {tokens.get('output', 0):,}</div>
    </div>
    <div class="card">
      <div class="label">Tool calls</div>
      <div class="value">{sess.get('tool_call_count', 0)}</div>
    </div>
  </div>
"""


def _status_cards_swe(row: dict) -> str:
    sample = row.get("sample") or {}
    verdict = row.get("verdict") or {}
    solver = row.get("solver") or {}
    sess = solver.get("session") or {}
    f2p = verdict.get("fail_to_pass") or {}
    p2p = verdict.get("pass_to_pass") or {}
    patch = solver.get("patch") or {}

    f2p_pass = f2p.get("success_count", 0)
    f2p_total = f2p_pass + f2p.get("failure_count", 0)
    p2p_pass = p2p.get("success_count", 0)
    p2p_total = p2p_pass + p2p.get("failure_count", 0)
    patch_applied = verdict.get("patch_successfully_applied")
    f2p_ok = f2p_total > 0 and f2p_pass == f2p_total
    p2p_ok = p2p_total == 0 or p2p_pass == p2p_total

    return f"""
  <div class="cards">
    <div class="card {'ok' if f2p_ok else 'bad'}">
      <div class="label">Fix-verification tests</div>
      <div class="value">{f2p_pass}/{f2p_total} passed</div>
    </div>
    <div class="card {'ok' if p2p_ok else 'bad'}">
      <div class="label">Regression tests</div>
      <div class="value">{p2p_pass}/{p2p_total} passed</div>
    </div>
    <div class="card {'ok' if patch_applied else 'bad'}">
      <div class="label">Patch applied</div>
      <div class="value">{'Yes' if patch_applied else 'No'}</div>
    </div>
    <div class="card">
      <div class="label">Patch size</div>
      <div class="value">+{patch.get('lines_added', 0)} / -{patch.get('lines_removed', 0)}</div>
    </div>
    <div class="card">
      <div class="label">Solver wall</div>
      <div class="value">{_esc(solver.get('wall_seconds'))}s</div>
    </div>
    <div class="card">
      <div class="label">Tool calls</div>
      <div class="value">{sess.get('tool_call_count', 0)}</div>
    </div>
  </div>
"""


def _hle_sections(row: dict, run_dir: Path) -> list[str]:
    sample = row.get("sample") or {}
    verdict = row.get("verdict") or {}
    solver = row.get("solver") or {}

    sections: list[str] = []

    # Side-by-side: ground truth vs agent ANSWER vs judge extracted.
    sections.append(f"""
  <section>
    <h2>Answer comparison</h2>
    <p class="explainer">The solver writes its final answer to <code>answer.txt</code>
    (extracted as the <code>ANSWER:</code> line). A separate amplifier session
    plays the role of the judge and decides if the answer matches the ground
    truth.</p>
    <table class="compare-table">
      <tr><th>Ground truth</th><td><pre>{_esc(sample.get('ground_truth') or '(none)')}</pre></td></tr>
      <tr><th>Agent ANSWER</th><td><pre>{_esc(solver.get('final_answer_line') or '(no ANSWER: line)')}</pre></td></tr>
      <tr><th>Judge extracted</th><td><pre>{_esc(verdict.get('extracted_final_answer') or '(none)')}</pre></td></tr>
    </table>
  </section>
""")

    if verdict.get("reasoning"):
        sections.append(f"""
  <section>
    <h2>Judge reasoning</h2>
    <p class="explainer">The judge's own explanation, captured verbatim from the
    grading amplifier session.</p>
    <pre class="problem">{_esc(verdict.get('reasoning'))}</pre>
  </section>
""")

    # Solver's full answer.txt content (collapsed).
    answer_path = run_dir / "solver" / "answer.txt"
    if answer_path.exists():
        answer_text = answer_path.read_text()
        sections.append(f"""
  <section>
    <h2>Agent's full answer.txt</h2>
    <details>
      <summary>Show full answer ({len(answer_text)} chars)</summary>
      <pre class="problem">{_esc(answer_text)}</pre>
    </details>
  </section>
""")

    # Question (collapsed).
    question_path = run_dir / "sample" / "question.md"
    if question_path.exists():
        question_text = question_path.read_text()
        sections.append(f"""
  <section>
    <h2>Question</h2>
    <details>
      <summary>Show the HLE question the agent saw</summary>
      <pre class="problem">{_esc(question_text)}</pre>
    </details>
  </section>
""")
    return sections


def _swe_sections(row: dict, run_dir: Path) -> list[str]:
    sample = row.get("sample") or {}
    verdict = row.get("verdict") or {}
    solver = row.get("solver") or {}
    f2p = verdict.get("fail_to_pass") or {}
    p2p = verdict.get("pass_to_pass") or {}

    sections: list[str] = []

    # Test results section.
    rows_html: list[str] = []
    f2p_pass = f2p.get("success_count", 0)
    f2p_total = f2p_pass + f2p.get("failure_count", 0)
    p2p_pass = p2p.get("success_count", 0)
    p2p_total = p2p_pass + p2p.get("failure_count", 0)
    f2p_pill_cls = "ok" if f2p_total > 0 and f2p_pass == f2p_total else "bad"
    p2p_pill_cls = "ok" if p2p_total == 0 or p2p_pass == p2p_total else "bad"
    rows_html.append(f"""
    <div class="test-row">
      <div>
        <div class="test-label">Fix-verification tests (FAIL_TO_PASS)</div>
        <div class="test-sub">Tests added by the original PR to prove the fix works</div>
      </div>
      <span class="pill {f2p_pill_cls}">{f2p_pass}/{f2p_total}</span>
    </div>
""")
    rows_html.append(f"""
    <div class="test-row">
      <div>
        <div class="test-label">Regression tests (PASS_TO_PASS)</div>
        <div class="test-sub">Tests that were passing on the base commit and must still pass</div>
      </div>
      <span class="pill {p2p_pill_cls}">{p2p_pass}/{p2p_total}</span>
    </div>
""")
    sections.append(f"""
  <section>
    <h2>Test results</h2>
    <p class="explainer">The harness runs two test sets against the agent's
    patch. The <strong>fix-verification</strong> set comes from the original
    PR's <code>test_patch</code> (these tests fail on the base commit and must
    pass after the fix). The <strong>regression</strong> set is tests that
    were already passing (they must still pass).</p>
    {"".join(rows_html)}
  </section>
""")

    # Failing test names (open if any failures).
    f2p_fails = f2p.get("failure") or []
    p2p_fails = p2p.get("failure") or []
    if f2p_fails or p2p_fails:
        body: list[str] = []
        if f2p_fails:
            items = "".join(
                f'<li class="fail">{_esc(t.strip())}</li>' for t in f2p_fails[:15]
            )
            extra = (
                f'<p class="explainer">... and {len(f2p_fails) - 15} more.</p>'
                if len(f2p_fails) > 15 else ""
            )
            body.append(f"""
    <details open>
      <summary>Fix-verification tests that did NOT pass ({len(f2p_fails)})</summary>
      <ul class="test-list">{items}</ul>
      {extra}
    </details>
""")
        if p2p_fails:
            items = "".join(
                f'<li class="fail">{_esc(t.strip())}</li>' for t in p2p_fails[:15]
            )
            extra = (
                f'<p class="explainer">... and {len(p2p_fails) - 15} more.</p>'
                if len(p2p_fails) > 15 else ""
            )
            body.append(f"""
    <details>
      <summary>Regressions: previously-passing tests now failing ({len(p2p_fails)})</summary>
      <ul class="test-list">{items}</ul>
      {extra}
    </details>
""")
        sections.append(f"""
  <section>
    <h2>Failing tests</h2>
    {"".join(body)}
  </section>
""")

    # Patches side-by-side.
    patch_path = run_dir / "solver" / "patch.diff"
    agent_patch = patch_path.read_text() if patch_path.exists() else ""
    instance_path = run_dir / "sample" / "instance.json"
    gold_patch = ""
    if instance_path.exists():
        try:
            inst = json.loads(instance_path.read_text())
            gold_patch = inst.get("patch") or ""
        except Exception:
            pass
    if agent_patch or gold_patch:
        sections.append(f"""
  <section>
    <h2>Patches: agent vs. gold</h2>
    <p class="explainer">Side-by-side comparison of the agent's patch (what was
    graded) and the gold patch (the real-world fix from the merged PR). The
    agent never sees the gold patch.</p>
    <div class="patches">
      <div class="panel">
        <h3>Agent's patch ({len(agent_patch)} chars)</h3>
        <pre>{_color_diff(agent_patch) if agent_patch.strip() else '(empty patch &mdash; agent did not edit any files)'}</pre>
      </div>
      <div class="panel">
        <h3>Gold patch ({len(gold_patch)} chars)</h3>
        <pre>{_color_diff(gold_patch)}</pre>
      </div>
    </div>
  </section>
""")

    # Problem statement (collapsed).
    problem_path = run_dir / "sample" / "problem_statement.md"
    if problem_path.exists():
        problem_text = problem_path.read_text()
        sections.append(f"""
  <section>
    <h2>Problem statement</h2>
    <details>
      <summary>Show the GitHub issue the agent saw</summary>
      <pre class="problem">{_esc(problem_text)}</pre>
    </details>
  </section>
""")
    return sections


def _metadata_section(row: dict, meta: dict) -> str:
    sample = row.get("sample") or {}
    solver = row.get("solver") or {}
    sess = solver.get("session") or {}
    tokens = sess.get("root_tokens") or {}
    judge_or_grader = row.get("judge_or_grader") or {}
    meta_solver = meta.get("solver") or {}
    meta_inner = row.get("meta") or {}

    tool_mix = sess.get("tool_mix") or {}
    tool_mix_str = (
        ", ".join(f"{name}: {count}" for name, count in tool_mix.items())
        or "(none)"
    )

    rows: list[tuple[str, str]] = []
    rows.append(("Task", f"<code>{_esc(meta_inner.get('benchmark'))}/{_esc(meta_inner.get('task_idx'))}</code>"))
    rows.append(("Variant", f"<strong>{_esc(meta_inner.get('variant'))}</strong>"))
    if sample.get("id"):
        rows.append(("Sample id", f"<code>{_esc(sample.get('id'))}</code>"))
    if sample.get("repo"):
        rows.append(("Repo", f"<code>{_esc(sample.get('repo'))}</code>"))
    if sample.get("base_commit"):
        rows.append(("Base commit", f"<code>{_esc(sample.get('base_commit'))}</code>"))
    rows.append(("Foundation", f"main @ <code>{_esc(meta_solver.get('foundation_sha'))}</code>"))
    rows.append(("Ran at", _esc(meta_inner.get("ran_at"))))
    rows.append(("Profile", f"<code>{_esc(meta_solver.get('profile'))}</code>"))
    rows.append(("DTU id", f"<code>{_esc(meta_inner.get('dtu_id'))}</code>"))
    rows.append(("Solver session id", f"<code>{_esc(solver.get('session_id'))}</code>"))
    rows.append(("Solver exit code", _esc(solver.get("exit_code"))))
    rows.append((
        "Solver tokens",
        f"{tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out / "
        f"{tokens.get('cache_read', 0):,} cache_read",
    ))
    rows.append(("Tool mix", _esc(tool_mix_str)))
    rows.append((
        f"{judge_or_grader.get('kind', 'judge').capitalize()} wall",
        f"{_esc(judge_or_grader.get('wall_seconds'))}s",
    ))

    body = "\n".join(f"      <dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    return f"""
  <section>
    <h2>Run metadata</h2>
    <dl class="kv">
{body}
    </dl>
  </section>
"""


def render(run_dir: Path) -> str:
    data = extract(run_dir)
    if data.get("error"):
        return f"<html><body><p>Error: {_esc(data.get('error'))}</p></body></html>"

    meta = json.loads((run_dir / "meta.json").read_text())
    sample = data.get("sample") or {}
    verdict = data.get("verdict") or {}
    benchmark = (data.get("meta") or {}).get("benchmark")
    outcome = bool(verdict.get("outcome"))

    failure_mode = verdict.get("failure_mode") or (
        ("CORRECT" if benchmark == "hle" else "RESOLVED")
        if outcome
        else ("INCORRECT" if benchmark == "hle" else "UNRESOLVED")
    )

    short_reason = ""
    if not outcome:
        if benchmark == "hle":
            short_reason = (verdict.get("reasoning") or "")[:200]
            if not short_reason:
                gt = sample.get("ground_truth") or "?"
                ag = verdict.get("extracted_final_answer") or "(none)"
                short_reason = f"Agent answered {ag}; correct answer was {gt}."
        else:
            short_reason = verdict.get("explanation") or "Patch did not resolve the issue."

    banner_html = _banner(outcome, benchmark, sample.get("id", ""), failure_mode, short_reason)
    failure_html = _failure_section(verdict, benchmark)
    if benchmark == "hle":
        cards_html = _status_cards_hle(data)
        body_sections = _hle_sections(data, run_dir)
    else:
        cards_html = _status_cards_swe(data)
        body_sections = _swe_sections(data, run_dir)
    metadata_html = _metadata_section(data, meta)

    title = (
        f"{'CORRECT' if outcome and benchmark == 'hle' else ''}"
        f"{'INCORRECT' if not outcome and benchmark == 'hle' else ''}"
        f"{'RESOLVED' if outcome and benchmark == 'swebench' else ''}"
        f"{'UNRESOLVED' if not outcome and benchmark == 'swebench' else ''}"
        f" &mdash; {_esc(sample.get('id', 'unknown'))}"
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Verdict: {title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <p class="crumb"><a href="../../../../report.html">&larr; back to top-level report</a></p>
{banner_html}
{failure_html}
{cards_html}
{"".join(body_sections)}
{metadata_html}
  <p class="footer">Generated by <code>metrics/render_verdict.py</code> from
  <code>{_esc(run_dir)}</code>.</p>
</div>
</body>
</html>
"""


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: render_verdict.py <run-dir>", file=sys.stderr)
        sys.exit(2)
    run_dir = Path(sys.argv[1])
    if not (run_dir / "meta.json").exists():
        print(f"ERROR: {run_dir}/meta.json not found", file=sys.stderr)
        sys.exit(2)
    out_path = run_dir / "verdict.html"
    out_path.write_text(render(run_dir))
    print(f"[render_verdict] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
