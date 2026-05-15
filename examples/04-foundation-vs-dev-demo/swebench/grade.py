#!/usr/bin/env python3
"""Host-side SWE-bench Multimodal grader (single instance).

Same shape as example 03. Runs `python -m swebench.harness.run_evaluation`
against one instance, parses the report, writes verdict.json.

Usage:
    python3 swebench/grade.py \
        --instance <path to instance.json> \
        --patch    <path to solver patch.diff> \
        --output   <path to grader output dir> \
        [--model-name amplifier-foundation-main]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

_DATASETS = {
    "multimodal": ("princeton-nlp/SWE-bench_Multimodal", "dev"),
    "verified": ("princeton-nlp/SWE-bench_Verified", "test"),
}


def _find_per_instance_report(
    run_dir: Path, model_name: str, instance_id: str
) -> Path | None:
    candidates = list(
        run_dir.glob(f"logs/run_evaluation/*/{model_name}/{instance_id}/report.json")
    )
    return candidates[0] if candidates else None


def _find_top_level_summary(work_dir: Path, run_id: str) -> Path | None:
    candidates = list(work_dir.glob(f"*.{run_id}.json"))
    return candidates[0] if candidates else None


def _is_resolved(instance_id: str, report: dict) -> tuple[bool, dict]:
    instance_report = report.get(instance_id, {}) or {}
    tests = instance_report.get("tests_status", {}) or {}
    f2p = tests.get("FAIL_TO_PASS", {}) or {}
    p2p = tests.get("PASS_TO_PASS", {}) or {}

    f2p_success = list(f2p.get("success", []) or [])
    f2p_failure = list(f2p.get("failure", []) or [])
    p2p_success = list(p2p.get("success", []) or [])
    p2p_failure = list(p2p.get("failure", []) or [])

    resolved_flag = instance_report.get("resolved")
    if resolved_flag is None:
        resolved_flag = (
            (not f2p_failure)
            and (not p2p_failure)
            and bool(f2p_success or not f2p.get("expected"))
        )

    return bool(resolved_flag), {
        "fail_to_pass": {
            "success": f2p_success,
            "failure": f2p_failure,
            "success_count": len(f2p_success),
            "failure_count": len(f2p_failure),
        },
        "pass_to_pass": {
            "success": p2p_success,
            "failure": p2p_failure,
            "success_count": len(p2p_success),
            "failure_count": len(p2p_failure),
        },
        "patch_is_None": instance_report.get("patch_is_None"),
        "patch_exists": instance_report.get("patch_exists"),
        "patch_successfully_applied": instance_report.get("patch_successfully_applied"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Grade a SWE-bench Multimodal solver patch via the official harness"
    )
    parser.add_argument("--instance", type=Path, required=True)
    parser.add_argument("--patch", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run-id", type=str, default=None)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument(
        "--model-name",
        type=str,
        default="amplifier-foundation-main",
        help="model_name_or_path written into predictions.jsonl",
    )
    parser.add_argument(
        "--dataset",
        choices=list(_DATASETS.keys()),
        default="multimodal",
        help="Which SWE-bench dataset to grade against (default: multimodal)",
    )
    args = parser.parse_args()
    dataset_name, split = _DATASETS[args.dataset]

    args.output.mkdir(parents=True, exist_ok=True)

    instance = json.loads(args.instance.read_text())
    instance_id = instance["instance_id"]
    patch_text = args.patch.read_text() if args.patch.exists() else ""

    run_id = args.run_id or f"amplifier-{instance_id}-{int(time.time())}"

    predictions_path = args.output / "predictions.jsonl"
    prediction_record = {
        "instance_id": instance_id,
        "model_name_or_path": args.model_name,
        "model_patch": patch_text,
    }
    predictions_path.write_text(json.dumps(prediction_record) + "\n")

    work_dir = args.output / "harness_workdir"
    work_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "swebench.harness.run_evaluation",
        "--dataset_name",
        dataset_name,
        "--split",
        split,
        "--predictions_path",
        str(predictions_path.resolve()),
        "--run_id",
        run_id,
        "--max_workers",
        str(args.max_workers),
        "--instance_ids",
        instance_id,
    ]

    print(f"[grade] running harness: {' '.join(cmd)}", file=sys.stderr)
    start = time.monotonic()
    stdout_path = args.output / "harness_stdout.txt"
    stderr_path = args.output / "harness_stderr.txt"
    with stdout_path.open("w") as stdout_f, stderr_path.open("w") as stderr_f:
        proc = subprocess.run(
            cmd,
            stdout=stdout_f,
            stderr=stderr_f,
            cwd=str(work_dir),
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
        )
    wall = time.monotonic() - start
    print(
        f"[grade] harness finished in {wall:.1f}s with exit code {proc.returncode}",
        file=sys.stderr,
    )

    summary_path = _find_top_level_summary(work_dir, run_id)
    report_path = _find_per_instance_report(work_dir, args.model_name, instance_id)

    summary_data: dict = {}
    if summary_path and summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text())
        except json.JSONDecodeError as exc:
            print(f"[grade] WARNING: could not parse summary: {exc}", file=sys.stderr)
        shutil.copy(summary_path, args.output / "summary.json")

    report_data: dict = {}
    if report_path and report_path.exists():
        try:
            report_data = json.loads(report_path.read_text())
        except json.JSONDecodeError as exc:
            print(f"[grade] WARNING: could not parse report: {exc}", file=sys.stderr)
        shutil.copy(report_path, args.output / "harness_report.json")

    resolved, status = _is_resolved(instance_id, report_data)

    verdict = {
        "resolved": resolved,
        "instance_id": instance_id,
        "harness_run_id": run_id,
        "harness_exit_code": proc.returncode,
        "harness_wall_seconds": round(wall, 2),
        "model_name_or_path": args.model_name,
        "patch_chars": len(patch_text),
        "patch_was_empty": not patch_text.strip(),
        "summary": summary_data,
        "status": status,
    }
    (args.output / "verdict.json").write_text(json.dumps(verdict, indent=2))

    print(
        f"[grade] verdict: resolved={resolved} "
        f"f2p_pass={status['fail_to_pass']['success_count']}"
        f"/{status['fail_to_pass']['success_count'] + status['fail_to_pass']['failure_count']} "
        f"p2p_pass={status['pass_to_pass']['success_count']}"
        f"/{status['pass_to_pass']['success_count'] + status['pass_to_pass']['failure_count']}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()