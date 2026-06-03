#!/usr/bin/env python3
"""Custom A/B harness for the explorer-removal eval.

Rather than the stock `run()` entry point in `amplifier_evaluation.harness.run`
(which runs agent x task pairs and stops at grading), this harness assembles the lower-level
building blocks to run ONE agent and ONE task as two trials -- foundation WITH
and WITHOUT the foundation:explorer agent -- and then computes the root-context
metric comparison that is the whole point of this example.

The variant is selected per trial via the `FOUNDATION_REPO` launch variable,
which the task profile's url_rewrites uses to redirect the amplifier-foundation
clone to one of two pre-seeded Gitea mirror repos. The two mirrors are
independent repositories, so the two trials never conflict.

Pipeline per trial (provided by run_trial): launch DTU -> install agent ->
seed -> AIUser drives the single exploration turn -> Extractor pulls the session
artifacts -> Grader scores answer quality -> destroy DTU. Afterwards compare.py
reads the two trials' extracted events.jsonl and writes the A/B comparison.

Invoked by run.sh, which provisions the mirrors and supplies GITEA_URL /
GITEA_TOKEN. See run.sh for the surrounding setup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from amplifier_evaluation.ai_user import AIUser
from amplifier_evaluation.extractor import Extractor
from amplifier_evaluation.grader import Grader
from amplifier_evaluation.harness.loaders import load_agent, load_task
from amplifier_evaluation.harness.schema import TrialSpec

# compare.py is a sibling module (same directory as this script).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare  # noqa: E402

# run_trial is imported lazily-safe at module load; it is a coroutine.
from amplifier_evaluation.harness.trial import run_trial  # noqa: E402

log = logging.getLogger("explorer-removal")

# (variant label, Gitea repo name) -- label is also the trial output subdir.
VARIANTS = [
    ("with-explorer", "amplifier-foundation-with-explorer"),
    ("without-explorer", "amplifier-foundation-without-explorer"),
]


async def run(args: argparse.Namespace) -> int:
    agent_dir = Path(args.agents_dir) / args.agent_id
    task_dir = Path(args.tasks_dir) / args.task_id
    agent = load_agent(agent_dir)
    task = load_task(task_dir)
    log.info("agent=%s task=%s", agent.id, task.id)

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    # The three eval-infrastructure sessions. setup() is expensive; do it once
    # and reuse across both trials (sequentially -- they are LLM sessions).
    log.info("setting up AIUser / Grader / Extractor sessions")
    ai_user, grader, extractor = AIUser(), Grader(), Extractor()
    await ai_user.setup()
    await grader.setup()
    await extractor.setup()

    repo_override = {
        "with-explorer": args.with_repo,
        "without-explorer": args.without_repo,
    }
    summary: dict[str, dict] = {}
    for label, default_repo in VARIANTS:
        repo = repo_override[label] or default_repo
        trial_dir = output / label
        spec = TrialSpec(
            agent=agent,
            task=task,
            trial_number=0,
            launch_variables={
                "GITEA_URL": args.gitea_url,
                "GITEA_TOKEN": args.gitea_token,
                "FOUNDATION_REPO": repo,
            },
        )
        log.info("=== trial %s (FOUNDATION_REPO=%s) ===", label, repo)
        try:
            result = await run_trial(
                spec, trial_dir, ai_user=ai_user, grader=grader, extractor=extractor
            )
            summary[label] = {
                "state": result.state,
                "grader_overall": (result.grader or {}).get("overall_score"),
                "error": result.error,
            }
            log.info("trial %s finished: state=%s", label, result.state)
        except Exception as exc:  # keep going so the other arm + comparison run
            summary[label] = {"state": "FAILED", "error": repr(exc)}
            log.exception("trial %s raised", label)

    # ---- metric comparison over the two extracted trials --------------------
    log.info("computing A/B metric comparison")
    comparison = compare.compare(output / "with-explorer", output / "without-explorer")
    (output / "comparison.json").write_text(json.dumps(comparison, indent=2))
    md = compare.render_markdown(comparison)
    (output / "comparison.md").write_text(md)

    summary["comparison"] = comparison.get("diff", {})
    (output / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n" + md)
    log.info("results: %s", output)

    failed = [
        k
        for k, v in summary.items()
        if isinstance(v, dict) and v.get("state") == "FAILED"
    ]
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent
    ap.add_argument("--agents-dir", default=str(here / "agents"), type=str)
    ap.add_argument("--tasks-dir", default=str(here / "tasks"), type=str)
    ap.add_argument("--agent-id", default="amplifier-foundation")
    ap.add_argument("--task-id", default="01-explorer-context-sink")
    ap.add_argument(
        "--output",
        required=True,
        help="run output dir (gets with-explorer/ + without-explorer/)",
    )
    ap.add_argument("--gitea-url", required=True)
    ap.add_argument("--gitea-token", required=True)
    ap.add_argument("--with-repo", default="amplifier-foundation-with-explorer")
    ap.add_argument("--without-repo", default="amplifier-foundation-without-explorer")
    ap.add_argument("--log-level", default="INFO")
    args = ap.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
