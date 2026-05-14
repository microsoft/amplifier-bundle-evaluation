#!/usr/bin/env python3
"""Render a single self-contained HTML report for a captured run.

Reads:
    <run-dir>/meta.json
    <run-dir>/sample/instance.json
    <run-dir>/sample/problem_statement.md
    <run-dir>/solver/patch.diff
    <run-dir>/analysis/ANALYSIS.md
    <run-dir>/analysis/analysis_metadata.json
    <run-dir>/grader/verdict.json

Writes:
    <run-dir>/verdict.html

The HTML embeds all data inline. Two CDN deps (marked, diff2html) render
the markdown and the side-by-side patch diff. Open the file in a browser
or share it directly.

Usage:
    python3 metrics/render_html.py <run-dir>
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_metrics import extract  # noqa: E402


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
:root {{
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
}}
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
               Oxygen, Ubuntu, sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  padding: 2rem 1rem;
  line-height: 1.55;
}}
.wrap {{ max-width: 1100px; margin: 0 auto; }}
.banner {{
  border-radius: 12px;
  padding: 1.5rem 2rem;
  margin-bottom: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1.5rem;
  border: 1px solid var(--border);
}}
.banner.ok  {{ background: var(--ok-bg);  border-color: #86efac; }}
.banner.bad {{ background: var(--bad-bg); border-color: #fca5a5; }}
.banner-icon {{
  font-size: 3rem;
  line-height: 1;
}}
.banner h1 {{ margin: 0; font-size: 1.8rem; }}
.banner h1 .word-ok  {{ color: var(--ok); }}
.banner h1 .word-bad {{ color: var(--bad); }}
.banner p {{ margin: 0.3rem 0 0; color: var(--text); }}
.tagline {{
  font-style: italic;
  color: var(--muted);
  margin-top: 0.4rem;
}}
.cards {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}}
.card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.75rem 1rem;
}}
.card .label {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }}
.card .value {{ font-size: 1.1rem; font-weight: 600; margin-top: 0.2rem; word-break: break-all; }}
.card.ok  .value {{ color: var(--ok);  }}
.card.bad .value {{ color: var(--bad); }}
.card.warn .value {{ color: var(--warn); }}
section {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.25rem 1.5rem;
  margin-bottom: 1.25rem;
}}
section > h2 {{
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.4rem;
}}
section .explainer {{
  color: var(--muted);
  font-size: 0.9rem;
  margin-bottom: 0.75rem;
}}
.test-row {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 1rem;
  align-items: center;
  padding: 0.6rem 0.8rem;
  border-radius: 6px;
  background: var(--bg);
  margin-bottom: 0.5rem;
}}
.test-row .test-label {{ font-weight: 500; }}
.test-row .test-sub   {{ font-size: 0.85rem; color: var(--muted); }}
.pill {{
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.9rem;
}}
.pill.ok   {{ background: var(--ok-bg);   color: var(--ok);   }}
.pill.bad  {{ background: var(--bad-bg);  color: var(--bad);  }}
.pill.warn {{ background: var(--warn-bg); color: var(--warn); }}
.pill.muted {{ background: #f1f5f9; color: var(--muted); }}
details {{
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.5rem 0.85rem;
  margin-bottom: 0.75rem;
  background: var(--card);
}}
details > summary {{ cursor: pointer; font-weight: 600; }}
details[open] > summary {{ margin-bottom: 0.5rem; }}
pre.problem {{
  background: var(--bg);
  padding: 0.9rem;
  border-radius: 6px;
  overflow-x: auto;
  white-space: pre-wrap;
  font-size: 0.9rem;
}}
.analysis-content :first-child {{ margin-top: 0; }}
.analysis-content h1, .analysis-content h2, .analysis-content h3 {{
  border-bottom: 1px solid var(--border);
  padding-bottom: 0.25rem;
}}
.analysis-content code {{
  background: #f1f5f9;
  padding: 0.1em 0.3em;
  border-radius: 3px;
  font-size: 0.9em;
}}
.analysis-content pre {{
  background: var(--code-bg);
  color: var(--code-text);
  padding: 0.9rem;
  border-radius: 6px;
  overflow-x: auto;
}}
.analysis-content pre code {{
  background: transparent;
  color: inherit;
  padding: 0;
}}
.patches {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}}
@media (max-width: 800px) {{
  .patches {{ grid-template-columns: 1fr; }}
}}
.patches .panel h3 {{ margin: 0 0 0.5rem; font-size: 1rem; }}
.patches .panel pre {{
  background: var(--code-bg);
  color: var(--code-text);
  padding: 0.75rem;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 0.78rem;
  max-height: 480px;
  line-height: 1.4;
}}
.diff-add {{ color: #4ade80; }}
.diff-del {{ color: #f87171; }}
.diff-hunk {{ color: #93c5fd; }}
.diff-meta {{ color: #94a3b8; }}
.footer {{
  margin-top: 2rem;
  color: var(--muted);
  font-size: 0.85rem;
  text-align: center;
}}
.kv {{ display: grid; grid-template-columns: max-content 1fr; column-gap: 1.5rem; row-gap: 0.3rem; font-size: 0.92rem; }}
.kv dt {{ color: var(--muted); font-weight: 500; }}
.kv dd {{ margin: 0; word-break: break-all; }}
.obs-list {{ margin: 0.5rem 0 0 1rem; padding: 0; }}
.obs-list li {{ margin-bottom: 0.4rem; }}
</style>
</head>
<body>
<div class="wrap">

  <div class="banner {banner_class}">
    <div class="banner-icon">{banner_icon}</div>
    <div>
      <h1>Verdict: <span class="word-{banner_class}">{verdict_word}</span></h1>
      <p><strong>{classification}</strong> &mdash; {instance_id} ({repo})</p>
      <p class="tagline">{what_it_means}</p>
    </div>
  </div>

  {summary_block}

  <div class="cards">
    <div class="card {f2p_class}">
      <div class="label">Fix-verification tests</div>
      <div class="value">{f2p_pass}/{f2p_total} passed</div>
    </div>
    <div class="card {p2p_class}">
      <div class="label">Regression tests</div>
      <div class="value">{p2p_pass}/{p2p_total} passed</div>
    </div>
    <div class="card {applied_class}">
      <div class="label">Patch applied</div>
      <div class="value">{applied_text}</div>
    </div>
    <div class="card">
      <div class="label">Patch size</div>
      <div class="value">{patch_lines_added}+ / {patch_lines_removed}-</div>
    </div>
    <div class="card">
      <div class="label">Solver wall time</div>
      <div class="value">{solver_wall}s</div>
    </div>
    <div class="card">
      <div class="label">Solver tool calls</div>
      <div class="value">{tool_calls}</div>
    </div>
  </div>

  <section>
    <h2>Test results</h2>
    <p class="explainer">The harness runs two test sets against the agent's patch. The <strong>fix-verification</strong> set comes from the original PR's <code>test_patch</code> (these tests fail on the base commit and must pass after the fix). The <strong>regression</strong> set is tests that were already passing (they must still pass).</p>
    <div class="test-row">
      <div>
        <div class="test-label">Fix-verification tests (FAIL_TO_PASS)</div>
        <div class="test-sub">Tests added by the PR to prove the fix works</div>
      </div>
      <span class="pill {f2p_class}">{f2p_pass}/{f2p_total}</span>
    </div>
    {f2p_failures}
    <div class="test-row">
      <div>
        <div class="test-label">Regression tests (PASS_TO_PASS)</div>
        <div class="test-sub">Tests that must still pass after the agent's patch</div>
      </div>
      <span class="pill {p2p_class}">{p2p_pass}/{p2p_total}</span>
    </div>
    {p2p_failures}
  </section>

  {observations_block}

  <section>
    <h2>Analysis</h2>
    <p class="explainer">From the post-run analyzer (a separate amplifier session). Source: <code>analysis/ANALYSIS.md</code>.</p>
    <div class="analysis-content" id="analysis-md">{analysis_md_escaped}</div>
  </section>

  <section>
    <h2>Patches: agent vs. gold</h2>
    <p class="explainer">Side-by-side comparison of the agent's patch (what was graded) and the gold patch (the real-world fix from the merged PR).</p>
    <div class="patches">
      <div class="panel">
        <h3>Agent's patch</h3>
        <pre>{agent_patch_html}</pre>
      </div>
      <div class="panel">
        <h3>Gold patch</h3>
        <pre>{gold_patch_html}</pre>
      </div>
    </div>
  </section>

  <section>
    <h2>Problem statement</h2>
    <details>
      <summary>Show the GitHub issue the agent saw</summary>
      <pre class="problem">{problem_statement_escaped}</pre>
    </details>
  </section>

  <section>
    <h2>Run metadata</h2>
    <dl class="kv">
      <dt>Instance id</dt><dd>{instance_id}</dd>
      <dt>Repo</dt><dd>{repo}</dd>
      <dt>Base commit</dt><dd><code>{base_commit}</code></dd>
      <dt>Foundation</dt><dd>{foundation_branch} @ <code>{foundation_sha}</code></dd>
      <dt>Ran at</dt><dd>{ran_at}</dd>
      <dt>Solver session id</dt><dd><code>{solver_sid}</code></dd>
      <dt>Solver exit code</dt><dd>{solver_exit}</dd>
      <dt>Solver tokens</dt><dd>{solver_input_tokens:,} in / {solver_output_tokens:,} out / {solver_cache_read_tokens:,} cache_read</dd>
      <dt>Grader run id</dt><dd><code>{harness_run_id}</code></dd>
      <dt>Grader wall</dt><dd>{grader_wall}s</dd>
      <dt>Analyzer session id</dt><dd><code>{analyzer_sid}</code></dd>
      <dt>Analyzer classification</dt><dd>{classification}</dd>
    </dl>
  </section>

  <p class="footer">Generated by <code>metrics/render_html.py</code> from artifacts in <code>{run_dir}</code>.</p>
</div>

<!-- marked.js converts the inlined ANALYSIS.md text into rendered HTML in-browser -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
(function() {{
  var el = document.getElementById('analysis-md');
  if (el && window.marked) {{
    var raw = el.textContent;
    el.innerHTML = window.marked.parse(raw);
  }}
}})();
</script>
</body>
</html>
"""


def _failure_rows(failures: list[str], regression: bool) -> str:
    if not failures:
        return ""
    title = (
        "Broken by agent's patch:"
        if regression
        else "Still failing after agent's patch:"
    )
    rows = []
    rows.append(
        f'<div class="test-sub" style="margin-left:1rem;margin-bottom:0.3rem;">{title}</div>'
    )
    for f in failures[:25]:
        rows.append(
            f'<div class="test-row" style="background:var(--bad-bg);margin-left:1rem;">'
            f"<div><code>{html.escape(f.strip())}</code></div>"
            f'<span class="pill bad">FAIL</span></div>'
        )
    if len(failures) > 25:
        rows.append(
            f'<div class="test-sub" style="margin-left:1rem;">... and {len(failures) - 25} more</div>'
        )
    return "\n".join(rows)


def _colorize_diff(diff_text: str) -> str:
    """HTML-escape a unified diff and color the +/- lines."""
    out = []
    for line in diff_text.splitlines():
        escaped = html.escape(line)
        if line.startswith("+++") or line.startswith("---"):
            out.append(f'<span class="diff-meta">{escaped}</span>')
        elif line.startswith("@@"):
            out.append(f'<span class="diff-hunk">{escaped}</span>')
        elif line.startswith("+"):
            out.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith("-"):
            out.append(f'<span class="diff-del">{escaped}</span>')
        elif line.startswith("diff --git") or line.startswith("index "):
            out.append(f'<span class="diff-meta">{escaped}</span>')
        else:
            out.append(escaped)
    return "\n".join(out)


def _read_text(p: Path) -> str:
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def render_html(run_dir: Path) -> str:
    data = extract(run_dir)
    instance = data["instance"]
    verdict = data["verdict"]
    solver = data["solver"]
    grader = data["grader"]
    meta = data["meta"]

    # Auxiliary file reads.
    analysis_md = _read_text(run_dir / "analysis" / "ANALYSIS.md")
    analysis_meta_path = run_dir / "analysis" / "analysis_metadata.json"
    analysis_meta = (
        json.loads(analysis_meta_path.read_text())
        if analysis_meta_path.exists()
        else {}
    )
    full_meta_path = run_dir / "meta.json"
    full_meta = (
        json.loads(full_meta_path.read_text()) if full_meta_path.exists() else {}
    )

    agent_patch = _read_text(run_dir / "solver" / "patch.diff")
    instance_json_path = run_dir / "sample" / "instance.json"
    instance_full = (
        json.loads(instance_json_path.read_text())
        if instance_json_path.exists()
        else {}
    )
    gold_patch = instance_full.get("patch", "")
    problem_statement = _read_text(run_dir / "sample" / "problem_statement.md")

    # Verdict shaping.
    resolved = bool(verdict.get("resolved"))
    verdict_word = "RESOLVED" if resolved else "UNRESOLVED"
    banner_class = "ok" if resolved else "bad"
    banner_icon = "✅" if resolved else "❌"
    what_it_means = (
        "Every fix-verification test passed and no regression test broke. "
        "The agent produced a patch that actually fixes the bug."
        if resolved
        else "The agent did NOT fix the bug to the harness's satisfaction. "
        "Either a fix-verification test still fails, or a regression test broke."
    )

    f2p = verdict.get("fail_to_pass", {}) or {}
    p2p = verdict.get("pass_to_pass", {}) or {}
    f2p_pass = f2p.get("success_count", 0)
    f2p_total = f2p_pass + f2p.get("failure_count", 0)
    p2p_pass = p2p.get("success_count", 0)
    p2p_total = p2p_pass + p2p.get("failure_count", 0)

    f2p_class = (
        "ok"
        if (f2p_total and f2p_pass == f2p_total)
        else ("muted" if f2p_total == 0 else "bad")
    )
    p2p_class = "ok" if (p2p_pass == p2p_total) else "bad"
    applied = verdict.get("patch_successfully_applied")
    applied_class = "ok" if applied else ("muted" if applied is None else "bad")
    applied_text = "Yes" if applied else ("Unknown" if applied is None else "No")

    patch_shape = solver.get("patch", {}) or {}
    patch_lines_added = patch_shape.get("lines_added", 0)
    patch_lines_removed = patch_shape.get("lines_removed", 0)

    sess = solver.get("session", {}) or {}
    tool_calls = sess.get("tool_call_count", 0)
    tokens = sess.get("root_tokens", {}) or {}

    classification = analysis_meta.get("classification") or "(no analysis)"
    summary = analysis_meta.get("summary") or ""
    summary_block = (
        f'<section><p style="margin:0;font-size:1.05rem;">'
        f"<strong>Summary:</strong> {html.escape(summary)}</p></section>"
        if summary
        else ""
    )

    observations = analysis_meta.get("key_observations") or []
    if observations:
        obs_html = "\n".join(f"<li>{html.escape(o)}</li>" for o in observations[:8])
        observations_block = (
            "<section>\n"
            "<h2>Key observations</h2>\n"
            '<p class="explainer">From the analyzer\'s structured metadata.</p>\n'
            f'<ul class="obs-list">{obs_html}</ul>\n'
            "</section>"
        )
    else:
        observations_block = ""

    analysis_full_meta = full_meta.get("analysis", {}) or {}
    analyzer_sid = analysis_full_meta.get("session_id") or "(not captured)"

    return _HTML_TEMPLATE.format(
        title=f"Verdict: {verdict_word} — {instance.get('id', '')}",
        banner_class=banner_class,
        banner_icon=banner_icon,
        verdict_word=verdict_word,
        classification=html.escape(classification),
        instance_id=html.escape(instance.get("id", "") or ""),
        repo=html.escape(instance.get("repo", "") or ""),
        what_it_means=html.escape(what_it_means),
        summary_block=summary_block,
        f2p_class=f2p_class,
        f2p_pass=f2p_pass,
        f2p_total=f2p_total,
        f2p_failures=_failure_rows(f2p.get("failure", []), regression=False),
        p2p_class=p2p_class,
        p2p_pass=p2p_pass,
        p2p_total=p2p_total,
        p2p_failures=_failure_rows(p2p.get("failure", []), regression=True),
        applied_class=applied_class,
        applied_text=applied_text,
        patch_lines_added=patch_lines_added,
        patch_lines_removed=patch_lines_removed,
        solver_wall=solver.get("wall_seconds_meta") or "n/a",
        tool_calls=tool_calls,
        observations_block=observations_block,
        # marked.js parses the textContent. We escape so any HTML in the
        # markdown is literal, then marked converts it back to HTML.
        analysis_md_escaped=html.escape(
            analysis_md or "_No analysis report available._"
        ),
        agent_patch_html=_colorize_diff(agent_patch)
        if agent_patch.strip()
        else "(empty patch — agent produced no changes)",
        gold_patch_html=_colorize_diff(gold_patch)
        if gold_patch.strip()
        else "(no gold patch in dataset)",
        problem_statement_escaped=html.escape(problem_statement),
        base_commit=html.escape(instance.get("base_commit", "") or ""),
        foundation_branch=html.escape(meta.get("foundation_branch", "") or ""),
        foundation_sha=html.escape(meta.get("foundation_sha", "") or ""),
        ran_at=html.escape(meta.get("ran_at", "") or ""),
        solver_sid=html.escape(solver.get("session_id", "") or ""),
        solver_exit=solver.get("exit_code"),
        solver_input_tokens=tokens.get("input", 0),
        solver_output_tokens=tokens.get("output", 0),
        solver_cache_read_tokens=tokens.get("cache_read", 0),
        harness_run_id=html.escape(grader.get("harness_run_id", "") or ""),
        grader_wall=grader.get("wall_seconds") or "n/a",
        analyzer_sid=html.escape(analyzer_sid),
        run_dir=html.escape(str(run_dir)),
    )


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: render_html.py <run-dir>", file=sys.stderr)
        sys.exit(2)

    run_dir = Path(sys.argv[1])
    out_path = run_dir / "verdict.html"
    out_path.write_text(render_html(run_dir), encoding="utf-8")
    print(f"[render_html] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
