"""Parallel scheduler for trial execution.

The scheduler is intentionally tiny: an `asyncio.Semaphore` caps concurrency,
each trial runs in its own task, and results are returned in trial-order
when all are done. There are no events or pub/sub: the progress UI polls
each trial's `state.json` instead. This keeps the scheduler pure and means
external observers (an agent watching the run, a CI script) see the same
data the UI does.

For course-correction mid-run, an operator can:

- write `cancel_requested: true` to a running trial's state.json (the trial
  will stop at the next stage boundary, destroy its DTU, and transition to
  `cancelled`); or
- write `retry_requested: true` to a `failed` or `cancelled` trial's state
  and re-invoke the harness (`run_trials` will resume work because terminal
  trials with retry_requested are reset and re-queued).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from pathlib import Path

from amplifier_evaluation.ai_user import AIUser
from amplifier_evaluation.extractor import Extractor
from amplifier_evaluation.grader import Grader

from amplifier_evaluation.harness.schema import TrialResult, TrialSpec
from amplifier_evaluation.harness.trial import run_trial


logger = logging.getLogger(__name__)


OnTrialFinished = Callable[[TrialResult], None]


async def run_trials(
    specs: list[TrialSpec],
    trials_root: Path,
    *,
    ai_user: AIUser,
    grader: Grader,
    extractor: Extractor,
    max_parallel: int = 2,
    on_finished: OnTrialFinished | None = None,
) -> list[TrialResult]:
    """Run every trial in `specs` concurrently, capped at `max_parallel`.

    Each trial writes its state.json to `trials_root/<trial_id>/`. Results
    are returned in input order.

    Failures inside one trial never propagate: the trial transitions to
    `failed` on disk and a `TrialResult` is still returned for it. This is
    the property that lets a multi-day run survive individual trial
    crashes.
    """
    if max_parallel < 1:
        raise ValueError("max_parallel must be >= 1")
    sem = asyncio.Semaphore(max_parallel)

    async def _one(spec: TrialSpec) -> TrialResult:
        async with sem:
            trial_dir = trials_root / spec.trial_id
            trial_dir.mkdir(parents=True, exist_ok=True)
            logger.info("starting trial %s", spec.trial_id)
            try:
                result = await run_trial(
                    spec,
                    trial_dir=trial_dir,
                    ai_user=ai_user,
                    grader=grader,
                    extractor=extractor,
                )
            except Exception as exc:
                # run_trial is supposed to catch everything itself, but be
                # defensive: convert any escape into a synthetic failed result.
                logger.exception("trial %s raised through run_trial", spec.trial_id)
                from amplifier_evaluation.harness.schema import TrialState, utcnow_iso

                result = TrialResult(
                    trial_id=spec.trial_id,
                    agent_id=spec.agent.id,
                    task_id=spec.task.id,
                    trial_number=spec.trial_number,
                    state=TrialState.FAILED.value,
                    dtu_id=None,
                    started_at=None,
                    finished_at=utcnow_iso(),
                    elapsed_s=0.0,
                    error=f"unhandled in scheduler: {type(exc).__name__}: {exc}",
                )
            if on_finished is not None:
                try:
                    on_finished(result)
                except Exception:
                    logger.exception("on_finished callback raised")
            return result

    tasks = [asyncio.create_task(_one(s), name=f"trial:{s.trial_id}") for s in specs]
    return list(await asyncio.gather(*tasks))
