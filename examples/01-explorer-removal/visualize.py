#!/usr/bin/env python3
"""Render a self-contained HTML report for an explorer-removal run.

Reads a run's comparison.json plus each arm's grader result and produces a
single report.html with no external dependencies (inline CSS, CSS bars). Open
it in a browser to see the concrete A/B outcome.

Usage:
    python visualize.py [--run <results-dir>] [--output <report.html>]

With no args it uses the most recent results/<timestamp>/ dir and writes
report.html inside it.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _latest_run() -> Path | None:
    runs = sorted(
        (HERE / "results").glob("*/"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    return runs[0] if runs else None


def _fmt(n) -> str:
    if isinstance(n, (int, float)) and not isinstance(n, bool):
        if isinstance(n, float) and n != int(n):
            return f"{n:,.1f}"
        return f"{int(n):,}"
    return str(n)


def _bar(value: float, vmax: float, cls: str) -> str:
    pct = 0 if not vmax else max(1.5, round(100 * value / vmax, 2))
    return f'<div class="bar {cls}" style="width:{pct}%"></div>'


def _metric_row(
    label: str, with_v, without_v, *, ratio=None, lower_is_better=True, note=""
) -> str:
    vmax = max(abs(with_v or 0), abs(without_v or 0)) or 1
    # Which arm is "good" on this metric? For context tokens/tool calls lower is
    # better, so the lean WITH arm is good (green) and the bloated WITHOUT is bad.
    badge = ""
    if ratio is not None:
        badge = f'<span class="ratio">{ratio}x</span>'
    return f"""
    <div class="metric">
      <div class="mhead"><span class="mlabel">{label}</span>{badge}</div>
      <div class="track"><div class="tlab">with</div>{_bar(with_v or 0, vmax, "good")}<div class="val">{_fmt(with_v)}</div></div>
      <div class="track"><div class="tlab">without</div>{_bar(without_v or 0, vmax, "bad")}<div class="val">{_fmt(without_v)}</div></div>
      {f'<div class="note">{note}</div>' if note else ""}
    </div>"""


def _humanize(key: str) -> str:
    """J1_provider_abstraction_identified -> 'J1 &middot; provider abstraction identified'."""
    parts = key.split("_")
    if parts and parts[0][:1].isalpha() and parts[0][1:].isdigit():
        return f"{parts[0]} &middot; " + html.escape(" ".join(parts[1:]))
    return html.escape(key.replace("_", " "))


def _grader_detail_html(arm_dir: Path) -> str:
    """Full grader detail: overall score, each evaluation's points + weight, every
    rubric criterion with PASS/FAIL and the grader's reasoning, plus a collapsible
    full audit report."""
    gr = _load(arm_dir / "grader" / "grader_result.json")
    if not gr:
        return '<div class="qscore">n/a</div><div class="creason">No grader result found.</div>'

    overall = gr.get("overall_score")
    out = [
        f'<div class="qscore">{overall if overall is not None else "n/a"}<span class="qmax"> overall</span></div>'
    ]

    for ev in gr.get("evaluations", []):
        pa, pp = ev.get("points_awarded"), ev.get("points_possible")
        meta = []
        if pa is not None and pp is not None:
            meta.append(f"{pa}/{pp} pts")
        if ev.get("weight") is not None:
            meta.append(f"weight {ev['weight']}")
        if ev.get("elapsed_s") is not None:
            meta.append(f"{ev['elapsed_s']:.0f}s")
        out.append(
            f'<div class="evname">{html.escape(ev.get("name", ""))}'
            f'<span class="evpts">{" &middot; ".join(meta)}</span></div>'
        )
        for key, info in (ev.get("rubric_scores") or {}).items():
            ok = (info.get("points_awarded", 0) or 0) > 0
            cls = "pass" if ok else "fail"
            reason = html.escape(info.get("reasoning", "") or "")
            out.append(
                f'<div class="crit"><div class="crithead">'
                f'<span class="cbadge {cls}">{"PASS" if ok else "FAIL"}</span>'
                f'<span class="ckey">{_humanize(key)}</span></div>'
                f'<div class="creason">{reason}</div></div>'
            )
        report = ev.get("initial_report")
        if report:
            out.append(
                '<details class="report"><summary>Full audit report</summary>'
                f"<pre>{html.escape(report)}</pre></details>"
            )
    return "".join(out)


def build_html(run_dir: Path) -> str:
    comp = _load(run_dir / "comparison.json")
    d = comp.get("diff", {})
    w = comp.get("with_explorer", {})
    wo = comp.get("without_explorer", {})

    def g(key, field="ratio_without_over_with"):
        return (d.get(key) or {}).get(field)

    wsub = next((s for s in w.get("sessions", []) if s.get("role") == "sub"), None)
    sub_note = ""
    if wsub:
        sub_note = (
            f"With the explorer, {_fmt(wsub['input'] + wsub['output'])} of the total "
            f"in+out tokens are spent in the explorer SUB-session -- real cost the "
            f"root-only number hides."
        )

    root_rows = "".join(
        [
            _metric_row(
                "Root-context input tokens",
                w.get("root_tokens", {}).get("input"),
                wo.get("root_tokens", {}).get("input"),
                ratio=g("root_input_tokens"),
            ),
            _metric_row(
                "Root-context total tokens (in+out)",
                w.get("root_tokens", {}).get("total"),
                wo.get("root_tokens", {}).get("total"),
                ratio=g("root_total_tokens"),
            ),
            _metric_row(
                "Root tool calls",
                w.get("tool_call_count"),
                wo.get("tool_call_count"),
                ratio=g("root_tool_calls"),
            ),
        ]
    )

    total_rows = "".join(
        [
            _metric_row(
                "Total input tokens (all sessions)",
                w.get("all_tokens", {}).get("input"),
                wo.get("all_tokens", {}).get("input"),
                ratio=g("total_input_tokens"),
                note=sub_note,
            ),
            _metric_row(
                "Total tokens in+out (all sessions)",
                w.get("all_tokens", {}).get("total"),
                wo.get("all_tokens", {}).get("total"),
                ratio=g("total_tokens"),
            ),
            _metric_row(
                "Total processed incl cache (all sessions)",
                w.get("all_tokens", {}).get("processed"),
                wo.get("all_tokens", {}).get("processed"),
                ratio=g("total_processed_tokens"),
            ),
        ]
    )

    other_rows = "".join(
        [
            _metric_row(
                "Root delegations",
                w.get("delegation_count"),
                wo.get("delegation_count"),
            ),
            _metric_row(
                "file:line citations", w.get("citation_count"), wo.get("citation_count")
            ),
            _metric_row(
                "Wall seconds (events)",
                w.get("wall_seconds_events"),
                wo.get("wall_seconds_events"),
                note="Removing the explorer is FASTER wall-clock -- the explorer trades wall time for a lean root, it is not a latency optimization.",
            ),
        ]
    )

    root_ratio = g("root_input_tokens")
    total_ratio = g("total_tokens")

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Explorer Removal -- Context Sink Report</title>
<style>
  :root {{ --good:#1aa179; --good2:#2ecc9b; --bad:#e0533d; --bad2:#ff6f52; --ink:#10171f; --mut:#5b6b7a; --line:#e6ebf0; --bg:#f6f8fa; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; color:var(--ink); background:var(--bg); }}
  .wrap {{ max-width:880px; margin:0 auto; padding:32px 20px 64px; }}
  h1 {{ font-size:26px; margin:0 0 4px; letter-spacing:-.3px; }}
  .sub {{ color:var(--mut); margin:0 0 24px; }}
  .verdict {{ background:linear-gradient(100deg,#0f2f27,#123); color:#eafff7; border-radius:14px; padding:22px 24px; margin:0 0 28px; }}
  .verdict .big {{ font-size:20px; font-weight:650; }}
  .verdict .big b {{ color:var(--good2); }}
  .verdict .sm {{ color:#b9d8cd; margin-top:6px; font-size:14px; }}
  .legend {{ display:flex; gap:18px; margin:0 0 18px; font-size:13px; color:var(--mut); }}
  .dot {{ display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:6px; vertical-align:middle; }}
  .dot.g {{ background:var(--good); }} .dot.b {{ background:var(--bad); }}
  .metric {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:14px 16px; margin-bottom:12px; }}
  .mhead {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
  .mlabel {{ font-weight:600; }}
  .ratio {{ background:#fde8e3; color:#b8341d; font-weight:700; font-size:13px; padding:2px 9px; border-radius:20px; }}
  .track {{ display:flex; align-items:center; gap:10px; margin:5px 0; }}
  .tlab {{ width:52px; color:var(--mut); font-size:12.5px; text-align:right; }}
  .bar {{ height:18px; border-radius:5px; min-width:3px; }}
  .bar.good {{ background:linear-gradient(90deg,var(--good),var(--good2)); }}
  .bar.bad {{ background:linear-gradient(90deg,var(--bad),var(--bad2)); }}
  .val {{ font-variant-numeric:tabular-nums; font-size:13px; color:#2a3742; }}
  .note {{ color:var(--mut); font-size:12.5px; margin-top:8px; border-top:1px dashed var(--line); padding-top:8px; }}
  .sub2 {{ color:var(--mut); font-size:13px; margin:0 0 14px; }}
  .sub2 code {{ background:#eef2f5; padding:1px 5px; border-radius:5px; }}
  .quality {{ display:flex; flex-direction:column; gap:16px; margin:8px 0; }}
  .qcard {{ background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px 18px; }}
  .qcard h3 {{ margin:0 0 6px; font-size:15px; }}
  .qscore {{ font-size:28px; font-weight:700; color:var(--good); }}
  .qmax {{ font-size:13px; font-weight:500; color:var(--mut); }}
  .evname {{ font-weight:650; font-size:13.5px; margin:12px 0 8px; padding-top:10px; border-top:1px solid var(--line); }}
  .evpts {{ font-weight:500; color:var(--mut); margin-left:8px; }}
  .crit {{ margin:0 0 10px; padding-left:12px; border-left:3px solid var(--line); }}
  .crithead {{ display:flex; align-items:center; gap:8px; margin-bottom:3px; }}
  .cbadge {{ font-size:11px; font-weight:700; letter-spacing:.04em; padding:1px 7px; border-radius:5px; color:#fff; }}
  .cbadge.pass {{ background:var(--good); }} .cbadge.fail {{ background:var(--bad); }}
  .ckey {{ font-size:13px; font-weight:600; }}
  .creason {{ font-size:12.5px; color:#3a4855; line-height:1.55; }}
  .crit.pass {{ border-left-color:var(--good); }}
  details.report {{ margin-top:10px; font-size:12.5px; }}
  details.report summary {{ cursor:pointer; color:var(--mut); font-weight:600; }}
  details.report pre {{ white-space:pre-wrap; background:#f3f6f8; border:1px solid var(--line); border-radius:8px; padding:12px; margin:8px 0 0; font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace; color:#2a3742; max-height:360px; overflow:auto; }}
  h2 {{ font-size:15px; text-transform:uppercase; letter-spacing:.06em; color:var(--mut); margin:28px 0 12px; }}
  .meta {{ color:var(--mut); font-size:12.5px; margin-top:30px; border-top:1px solid var(--line); padding-top:14px; }}
  .meta code {{ background:#eef2f5; padding:1px 6px; border-radius:5px; }}
</style></head>
<body><div class="wrap">
  <h1>foundation:explorer &mdash; context-sink report</h1>
  <p class="sub">Same exploration prompt, same target repo, foundation WITH vs WITHOUT the explorer agent.</p>

  <div class="verdict">
    <div class="big">Root context <b>{root_ratio}x</b> leaner with the explorer &mdash; but total compute only <b>{total_ratio}x</b> cheaper.</div>
    <div class="sm">The explorer moves exploration into a sub-session, so the ROOT stays lean (this is what enables longer sessions). But that sub-session still spends tokens, so the TOTAL compute gap is far smaller than the root-only number suggests. Answer quality held at parity, and the no-explorer arm is actually faster wall-clock.</div>
  </div>

  <div class="legend">
    <span><span class="dot g"></span>with explorer</span>
    <span><span class="dot b"></span>without explorer</span>
  </div>

  <h2>Root context &mdash; the context-sink benefit</h2>
  {root_rows}

  <h2>Total compute &mdash; root + sub-sessions (the real cost)</h2>
  {total_rows}

  <h2>Behavior</h2>
  {other_rows}

  <h2>Answer quality (grader)</h2>
  <p class="sub2">Rubric-graded by an LLM auditor running inside the DTU: it located the root session's final answer, scored each criterion, and verified every cited file:line against <code>/workspace/agent-framework</code>. Expand "Full audit report" for the auditor's complete reasoning.</p>
  <div class="quality">
    <div class="qcard"><h3>with explorer</h3>{_grader_detail_html(run_dir / "with-explorer")}</div>
    <div class="qcard"><h3>without explorer</h3>{_grader_detail_html(run_dir / "without-explorer")}</div>
  </div>

  <div class="meta">
    Run: <code>{run_dir.name}</code> &middot; root sessions:
    with <code>{w.get("root_session_id", "?")}</code>,
    without <code>{wo.get("root_session_id", "?")}</code>.
    Metrics from each root session's <code>events.jsonl</code>; quality from the rubric grader.
  </div>
</div></body></html>"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--run",
        type=Path,
        default=None,
        help="results/<timestamp> dir (default: latest)",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=None,
        help="output html (default: <run>/report.html)",
    )
    args = ap.parse_args()

    run_dir = args.run or _latest_run()
    if not run_dir or not run_dir.is_dir():
        print("no run dir found; pass --run <results-dir>")
        return 2
    out = args.output or (run_dir / "report.html")
    out.write_text(build_html(run_dir))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
