#!/usr/bin/env python3
"""Build the top-level index report for an example-04 results directory.

This file is the entry point a user opens after running ./run.sh. It links to
the per-run verdict.html files (generated separately by render_verdict.py).

Sections:
  1. Title + model-pin banner (which models actually fired during solver runs)
  2. Summary table: foundation vs amplifier-dev per benchmark
  3. Per-task side-by-side comparison (with delta and links to verdict.html)
  4. Grid of mini-cards: one per run, each linking to its verdict.html

Self-contained, inlined CSS, no external assets.

Usage:
    python3 metrics/build_html_report.py <results-date-dir> [--output report.html]
"""

from __future__ import annotations

import argparse
import html as _html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_metrics import extract  # noqa: E402


VARIANTS = ["foundation", "amplifier-dev"]
BENCHMARKS = ["hle", "swebench"]


def _esc(s: object) -> str:
    if s is None:
        return ""
    return _html.escape(str(s))


def _gather(top_results: Path) -> list[dict]:
    rows: list[dict] = []
    for variant_dir in sorted(top_results.iterdir()):
        if not variant_dir.is_dir() or variant_dir.name.startswith("_"):
            continue
        if variant_dir.name not in VARIANTS:
            continue
        for bench_dir in sorted(variant_dir.iterdir()):
            if not bench_dir.is_dir():
                continue
            for task_dir in sorted(bench_dir.iterdir()):
                if not task_dir.is_dir() or not task_dir.name.startswith("task-"):
                    continue
                run_dir = task_dir / "run-1"
                if not (run_dir / "meta.json").exists():
                    rows.append({
                        "variant": variant_dir.name,
                        "benchmark": bench_dir.name,
                        "task_idx": task_dir.name.replace("task-", ""),
                        "missing": True,
                        "run_dir": str(run_dir),
                    })
                    continue
                data = extract(run_dir)
                data["_run_dir"] = str(run_dir)
                data["_verdict_href"] = str(
                    run_dir.relative_to(top_results) / "verdict.html"
                )
                rows.append(data)
    return rows


def _model_pin_banner(rows: list[dict]) -> str:
    """Collect every unique model name seen in solver events.jsonl across all runs."""
    seen: set[str] = set()
    for row in rows:
        run_dir = Path(row.get("_run_dir") or "")
        sid = (row.get("solver") or {}).get("session_id")
        if not (run_dir and sid):
            continue
        events_path = run_dir / "solver" / "sessions" / "sessions" / sid / "events.jsonl"
        if not events_path.exists():
            continue
        for line in events_path.read_text().splitlines():
            if '"event": "llm:response"' not in line and '"event":"llm:response"' not in line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            model = (ev.get("data") or {}).get("model") or (
                (ev.get("data") or {}).get("response") or {}
            ).get("model")
            if model:
                seen.add(model)
    if not seen:
        return ""
    pills = " ".join(f'<span class="model-pill"><code>{_esc(m)}</code></span>' for m in sorted(seen))
    return f'<div class="model-banner"><strong>Models seen in solver sessions:</strong> {pills}</div>'


def _dataset_banner(rows: list[dict]) -> str:
    """Show which SWE-bench dataset was used (looked up from instance.json)."""
    seen: set[str] = set()
    for row in rows:
        if (row.get("meta") or {}).get("benchmark") != "swebench":
            continue
        run_dir = Path(row.get("_run_dir") or "")
        inst_path = run_dir / "sample" / "instance.json"
        if not inst_path.exists():
            continue
        try:
            inst = json.loads(inst_path.read_text())
            if inst.get("dataset"):
                seen.add(inst["dataset"])
        except Exception:
            pass
    if not seen:
        return ""
    val = " / ".join(sorted(seen))
    return f'<div class="model-banner"><strong>SWE-bench dataset:</strong> <code>{_esc(val)}</code></div>'


def _summary_section(rows: list[dict]) -> str:
    counts: dict[tuple[str, str], dict] = {}
    for variant in VARIANTS:
        for bench in BENCHMARKS:
            counts[(variant, bench)] = {
                "passed": 0, "total": 0,
                "wall_sum": 0, "tokens_in_sum": 0, "tokens_out_sum": 0,
                "tool_calls_sum": 0,
            }
    for row in rows:
        if row.get("missing") or row.get("error"):
            continue
        meta = row.get("meta") or {}
        key = (meta.get("variant"), meta.get("benchmark"))
        if key not in counts:
            continue
        c = counts[key]
        c["total"] += 1
        verdict = row.get("verdict") or {}
        if verdict.get("outcome"):
            c["passed"] += 1
        solver = row.get("solver") or {}
        wall = solver.get("wall_seconds")
        if isinstance(wall, (int, float)):
            c["wall_sum"] += wall
        sess = solver.get("session") or {}
        tokens = sess.get("root_tokens") or {}
        c["tokens_in_sum"] += int(tokens.get("input", 0) or 0)
        c["tokens_out_sum"] += int(tokens.get("output", 0) or 0)
        c["tool_calls_sum"] += int(sess.get("tool_call_count", 0) or 0)

    lines: list[str] = []
    lines.append('<section>')
    lines.append('<h2>Summary</h2>')
    lines.append('<p class="explainer">Aggregate pass rates and resource usage '
                 'per (variant, benchmark). Click any row in the comparison table '
                 'below for full per-run detail.</p>')
    lines.append('<table class="summary">')
    lines.append('<thead><tr>')
    lines.append('<th>Variant</th><th>Benchmark</th><th>Pass rate</th>'
                 '<th>Total solver wall</th><th>Tokens (in / out)</th><th>Tool calls</th>'
                 '</tr></thead>')
    lines.append('<tbody>')
    for variant in VARIANTS:
        for bench in BENCHMARKS:
            c = counts[(variant, bench)]
            rate_text = f"{c['passed']}/{c['total']}" if c["total"] else "0/0"
            rate_cls = "ok" if c["passed"] == c["total"] and c["total"] > 0 \
                       else ("warn" if c["passed"] > 0 else "bad")
            wall_min = c["wall_sum"] / 60 if c["wall_sum"] else 0
            outcome_key = "correct" if bench == "hle" else "resolved"
            lines.append('<tr>')
            lines.append(f'<td><strong>{_esc(variant)}</strong></td>')
            lines.append(f'<td>{_esc(bench)} <span class="muted">({outcome_key})</span></td>')
            lines.append(f'<td><span class="pill {rate_cls}">{rate_text}</span></td>')
            lines.append(f'<td>{wall_min:.1f} min</td>')
            lines.append(f'<td>{c["tokens_in_sum"]:,} / {c["tokens_out_sum"]:,}</td>')
            lines.append(f'<td>{c["tool_calls_sum"]}</td>')
            lines.append('</tr>')
    lines.append('</tbody></table>')
    lines.append('</section>')
    return "\n".join(lines)


def _comparison_section(rows: list[dict]) -> str:
    by_task: dict[tuple[str, str], dict[str, dict]] = {}
    for row in rows:
        meta = row.get("meta") or {}
        bench = meta.get("benchmark")
        idx = meta.get("task_idx")
        variant = meta.get("variant")
        if not (bench and idx and variant):
            continue
        by_task.setdefault((bench, str(idx)), {})[variant] = row

    lines: list[str] = []
    lines.append('<section>')
    lines.append('<h2>Per-task comparison</h2>')
    lines.append('<p class="explainer">Same task run on both bundle variants. '
                 'Click a verdict for the full per-run report.</p>')
    lines.append('<table class="compare">')
    lines.append('<thead><tr>')
    lines.append('<th>Benchmark</th><th>Task</th><th>Foundation</th>'
                 '<th>Amplifier Dev</th><th>Delta</th></tr></thead>')
    lines.append('<tbody>')
    for bench in BENCHMARKS:
        for idx_str in sorted({k[1] for k in by_task.keys() if k[0] == bench}, key=int):
            key = (bench, idx_str)
            if key not in by_task:
                continue
            cells = by_task[key]
            f_row = cells.get("foundation")
            d_row = cells.get("amplifier-dev")
            task_id = ""
            for r in (f_row, d_row):
                if r and not r.get("missing"):
                    task_id = (r.get("sample") or {}).get("id", "")
                    if task_id:
                        break

            def _verdict_cell(row: dict | None) -> str:
                if row is None or row.get("missing"):
                    return '<span class="pill muted">missing</span>'
                if row.get("error"):
                    return f'<span class="pill bad">error: {_esc(row["error"])}</span>'
                v = row.get("verdict") or {}
                outcome = v.get("outcome")
                solver = row.get("solver") or {}
                wall = solver.get("wall_seconds") or 0
                badge = ('<span class="pill ok">PASS</span>' if outcome
                         else '<span class="pill bad">FAIL</span>')
                href = row.get("_verdict_href")
                link = f'<a href="{_esc(href)}">verdict</a>' if href else ""
                return (f'{badge} <span class="muted">'
                        f'{int(wall)}s</span> {link}')

            def _outcome(row: dict | None) -> bool | None:
                if row is None or row.get("missing") or row.get("error"):
                    return None
                return bool((row.get("verdict") or {}).get("outcome"))

            f_out = _outcome(f_row)
            d_out = _outcome(d_row)
            if f_out is None or d_out is None:
                delta = "&mdash;"
            elif f_out == d_out:
                delta = "<span class='muted'>same</span>"
            elif d_out and not f_out:
                delta = '<span class="delta-better">dev better</span>'
            else:
                delta = '<span class="delta-worse">foundation better</span>'

            lines.append('<tr>')
            lines.append(f'<td>{_esc(bench)}</td>')
            lines.append(f'<td><code>{_esc(task_id)}</code></td>')
            lines.append(f'<td>{_verdict_cell(f_row)}</td>')
            lines.append(f'<td>{_verdict_cell(d_row)}</td>')
            lines.append(f'<td>{delta}</td>')
            lines.append('</tr>')
    lines.append('</tbody></table>')
    lines.append('</section>')
    return "\n".join(lines)


def _mini_card(row: dict) -> str:
    if row.get("missing"):
        return (
            '<a class="mini-card mini-missing" href="#">'
            f'<div class="mini-header">{_esc(row.get("variant"))} / '
            f'{_esc(row.get("benchmark"))} / task-{_esc(row.get("task_idx"))}</div>'
            '<div class="mini-failure">No meta.json (job did not produce results)</div>'
            '</a>'
        )
    meta = row.get("meta") or {}
    sample = row.get("sample") or {}
    verdict = row.get("verdict") or {}
    solver = row.get("solver") or {}
    sess = solver.get("session") or {}
    tokens = sess.get("root_tokens") or {}
    outcome = verdict.get("outcome")
    benchmark = meta.get("benchmark")
    word_ok = "CORRECT" if benchmark == "hle" else "RESOLVED"
    word_bad = "INCORRECT" if benchmark == "hle" else "UNRESOLVED"
    word = word_ok if outcome else word_bad
    cls = "ok" if outcome else "bad"
    href = row.get("_verdict_href") or "#"
    failure_mode = verdict.get("failure_mode") or ""
    failure_block = ""
    if not outcome:
        if benchmark == "hle":
            text = (verdict.get("reasoning") or "")[:180] \
                or (f"Agent: {verdict.get('extracted_final_answer') or '(none)'} "
                    f"vs truth: {sample.get('ground_truth') or '?'}")
        else:
            text = verdict.get("explanation") or "Patch did not resolve the issue."
        failure_block = (
            f'<div class="mini-failure">'
            f'<span class="mini-failmode">{_esc(failure_mode)}</span> '
            f'<span>{_esc(text[:200])}</span>'
            f'</div>'
        )
    wall = solver.get("wall_seconds") or 0
    return f"""
<a class="mini-card mini-{cls}" href="{_esc(href)}">
  <div class="mini-header">
    <span class="pill {cls}">{word}</span>
    {_esc(meta.get('variant'))} / {_esc(meta.get('benchmark'))} / task-{_esc(meta.get('task_idx'))}
  </div>
  <div class="mini-sample"><code>{_esc(sample.get('id', ''))}</code></div>
  {failure_block}
  <div class="mini-stats">
    <span>{int(wall)}s wall</span>
    <span>{tokens.get('input', 0):,} in / {tokens.get('output', 0):,} out tok</span>
    <span>{sess.get('tool_call_count', 0)} tool calls</span>
  </div>
</a>
"""


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
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  margin: 0;
  padding: 2rem 1rem;
  line-height: 1.55;
}
.wrap { max-width: 1200px; margin: 0 auto; }
h1 { margin: 0 0 0.25rem; font-size: 1.8rem; }
.subtitle { color: var(--muted); margin-top: 0; }
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
.model-banner {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.6rem 1rem;
  margin-bottom: 1rem;
  font-size: 0.92rem;
}
.model-banner code { background: var(--bg); padding: 0.05rem 0.4rem; border-radius: 3px; }
.model-pill { margin-right: 0.4rem; }
table.summary, table.compare { width: 100%; border-collapse: collapse; }
table.summary th, table.summary td,
table.compare th, table.compare td {
  text-align: left;
  padding: 0.55rem 0.75rem;
  border-bottom: 1px solid var(--border);
  font-size: 0.93rem;
  vertical-align: middle;
}
table.summary th, table.compare th {
  background: var(--bg);
  font-weight: 600;
  font-size: 0.85rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
tbody tr:hover { background: #f9fafb; }
.pill {
  display: inline-block;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  font-weight: 600;
  font-size: 0.8rem;
  vertical-align: middle;
}
.pill.ok    { background: var(--ok-bg);   color: var(--ok);   }
.pill.bad   { background: var(--bad-bg);  color: var(--bad);  }
.pill.warn  { background: var(--warn-bg); color: var(--warn); }
.pill.muted { background: #f1f5f9; color: var(--muted); }
.muted { color: var(--muted); font-size: 0.85rem; }
.delta-better { color: var(--ok); font-weight: 600; }
.delta-worse  { color: var(--bad); font-weight: 600; }
code { background: #f1f5f9; padding: 0.05rem 0.3rem; border-radius: 3px;
       font-size: 0.85em; font-family: ui-monospace, SFMono-Regular, monospace; }
a { color: #1d4ed8; text-decoration: none; }
a:hover { text-decoration: underline; }
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 0.85rem;
  margin-top: 0.75rem;
}
.mini-card {
  display: block;
  background: var(--card);
  border: 1px solid var(--border);
  border-left: 4px solid var(--border);
  border-radius: 8px;
  padding: 0.85rem 1rem;
  text-decoration: none;
  color: var(--text);
  transition: box-shadow 0.15s, transform 0.05s;
}
.mini-card:hover { box-shadow: 0 4px 14px rgba(0,0,0,0.07); text-decoration: none; }
.mini-card:active { transform: translateY(1px); }
.mini-card.mini-ok  { border-left-color: var(--ok); }
.mini-card.mini-bad { border-left-color: var(--bad); }
.mini-card.mini-missing { border-left-color: var(--warn); background: #fff8e1; }
.mini-header { font-weight: 600; font-size: 0.95rem; margin-bottom: 0.2rem; }
.mini-header .pill { margin-right: 0.4rem; }
.mini-sample { font-size: 0.82rem; color: var(--muted); margin-bottom: 0.4rem; }
.mini-failure {
  background: #fef2f2;
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
  margin: 0.4rem 0;
  font-size: 0.82rem;
  line-height: 1.4;
}
.mini-failmode {
  font-family: ui-monospace, SFMono-Regular, monospace;
  font-size: 0.72rem;
  background: var(--bad-bg);
  color: var(--bad);
  padding: 0.05rem 0.35rem;
  border-radius: 3px;
  margin-right: 0.3rem;
}
.mini-stats {
  display: flex;
  gap: 0.85rem;
  margin-top: 0.35rem;
  font-size: 0.8rem;
  color: var(--muted);
}
.footer { margin-top: 2rem; color: var(--muted); font-size: 0.85rem; text-align: center; }
"""


def build(top_results: Path) -> str:
    rows = _gather(top_results)
    model_banner = _model_pin_banner(rows)
    dataset_banner = _dataset_banner(rows)
    summary = _summary_section(rows)
    comparison = _comparison_section(rows)
    cards = "\n".join(_mini_card(row) for row in rows)

    title = f"Amplifier Foundation vs Dev demo &mdash; {top_results.name}"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
<h1>{title}</h1>
<p class="subtitle">HLE and SWE-bench tasks run on the foundation bundle and
the amplifier-dev bundle in parallel Digital Twin Universe instances.
Generated from <code>{_esc(top_results)}</code>.</p>
{dataset_banner}
{model_banner}

{summary}
{comparison}

<section>
  <h2>Per-run detail</h2>
  <p class="explainer">Click any card to open the full
  <code>verdict.html</code> for that run (banner, status cards, failing tests,
  patches side-by-side for SWE-bench, problem statement, full run metadata).</p>
  <div class="cards">
{cards}
  </div>
</section>

<p class="footer">
Generated by <code>metrics/build_html_report.py</code>.
Per-run verdict pages are generated by <code>metrics/render_verdict.py</code>.
Source data lives under each run's <code>solver/</code> and
<code>{{judge|grader}}/</code> directories.
</p>
</div>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("top_results", type=Path,
                        help="Top-level results dir, e.g. results/2026-05-14/")
    parser.add_argument("--output", type=Path, default=None,
                        help="Output HTML path (default: <top-results>/report.html)")
    args = parser.parse_args()

    if not args.top_results.exists():
        print(f"ERROR: {args.top_results} does not exist", file=sys.stderr)
        sys.exit(2)

    output_path = args.output or (args.top_results / "report.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    html_text = build(args.top_results)
    output_path.write_text(html_text)
    print(f"[build_html_report] wrote {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
