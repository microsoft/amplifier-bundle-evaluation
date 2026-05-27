"""Run one evaluation trial end to end.

A trial is the atomic unit of work: one (agent, task, trial_number) tuple
isolated in its own Digital Twin Universe instance. The trial runner is the
only place that knows the full sequence of stages.

Stages (deterministic order):

    launching   -> launch DTU from the resolved profile
    installing  -> run agent setup_cmds inside the launched DTU
    seeding     -> push task workspace + task instructions
    running_agent -> AIUser drives the agent until conclude / timeout
    extracting  -> Extractor pulls agent artifacts to host
    grading     -> Grader audits the live DTU
    cleaning_up -> destroy DTU

Extraction runs *before* grading because the grader may modify the DTU
state and we want to preserve a clean snapshot of the agent's work.

Every stage writes the new state to `state.json` (atomic). External agents
can read state.json to observe progress, or write `cancel_requested: true`
to it to ask the trial to stop gracefully at the next stage boundary.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from dataclasses import asdict
from pathlib import Path

from amplifier_evaluation.ai_user import AIUser
from amplifier_evaluation.extractor import Extractor
from amplifier_evaluation.grader import Grader

from amplifier_evaluation.harness import state as state_io
from amplifier_evaluation.harness.dtu import DTU, DTUError
from amplifier_evaluation.harness.install import (
    InstallError,
    compose_launch_profile,
    install_agent,
    verify_env,
)
from amplifier_evaluation.harness.schema import (
    StageRecord,
    TrialResult,
    TrialSpec,
    TrialState,
    utcnow_iso,
)
from amplifier_evaluation.harness.state import TrialStateRecord


logger = logging.getLogger(__name__)


class TrialCancelled(Exception):
    """Raised when a trial detects `cancel_requested: true` between stages."""


def _check_cancel(trial_dir: Path) -> None:
    if state_io.check_cancel_requested(trial_dir):
        raise TrialCancelled("cancel_requested set on state.json")


async def run_trial(
    spec: TrialSpec,
    trial_dir: Path,
    *,
    ai_user: AIUser,
    grader: Grader,
    extractor: Extractor,
) -> TrialResult:
    """Run one trial. Returns a `TrialResult` reflecting the final state.

    This function is idempotent in the sense that it always writes the final
    state to disk on completion or failure. The DTU is always destroyed on
    exit (success, failure, or cancellation), so callers don't need to
    handle cleanup themselves.
    """
    trial_dir.mkdir(parents=True, exist_ok=True)

    # Build or reload the on-disk state.
    record = state_io.load_state(trial_dir)
    if record is None:
        record = TrialStateRecord(
            trial_id=spec.trial_id,
            agent_id=spec.agent.id,
            task_id=spec.task.id,
            trial_number=spec.trial_number,
            state=TrialState.PENDING.value,
            started_at=utcnow_iso(),
            history=[StageRecord(state=TrialState.PENDING.value, at=utcnow_iso())],
        )
        state_io.save_state(trial_dir, record)
    elif record.retry_requested:
        # Operator-requested retry: reset terminal state, keep history.
        state_io.append_log(
            trial_dir, f"[{utcnow_iso()}] retry_requested -> resetting state"
        )
        record.state = TrialState.PENDING.value
        record.retry_requested = False
        record.error = None
        record.finished_at = None
        record.history.append(
            StageRecord(state=TrialState.PENDING.value, at=utcnow_iso(), note="retry")
        )
        state_io.save_state(trial_dir, record)

    # Skip already-finished trials unless retry was requested above.
    if record.state in (TrialState.COMPLETED.value, TrialState.CANCELLED.value):
        logger.info(
            "trial %s already terminal (%s); skipping", spec.trial_id, record.state
        )
        return _to_result(record)

    start = time.monotonic()
    dtu: DTU | None = None
    install_log = trial_dir / "install.log"

    try:
        # ---- environment preflight -------------------------------------
        missing = verify_env(spec.agent)
        if missing:
            raise InstallError(
                f"agent {spec.agent.id} requires env vars not present on host: {missing}"
            )

        # ---- launch ----------------------------------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.LAUNCHING)
        # Synthesize a merged profile that adds the agent's `requires.env`
        # entries to the task profile's `passthrough.services`, so agents
        # don't depend on each task profile pre-declaring every possible
        # API key. The merged profile is written to the trial dir for
        # auditability.
        profile_path = compose_launch_profile(
            spec.agent,
            spec.task.profile_path,
            trial_dir / "launch_profile.yaml",
        )
        dtu = await DTU.launch(profile_path)
        record.dtu_id = dtu.id
        state_io.save_state(trial_dir, record)
        state_io.append_log(
            trial_dir, f"[{utcnow_iso()}] launched dtu={dtu.id} profile={profile_path}"
        )

        # ---- install ---------------------------------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.INSTALLING)
        await install_agent(spec.agent, dtu, log_to=install_log)

        # ---- seed ------------------------------------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.SEEDING)
        # Push the task's workspace if it has one. The DTU CLI's file-push
        # last-arg-is-destination rule handles individual files; for a
        # workspace directory we push the directory contents into /workspace.
        if spec.task.workspace_dir.is_dir():
            for child in spec.task.workspace_dir.iterdir():
                await dtu.file_push(child, "/workspace/")
        # Push task instructions for the AI User to reference inside the DTU.
        # The AIUser doesn't actually need this on disk (it embeds the
        # scenario directly), but agents often want to `cat instructions.txt`.
        instructions_path = trial_dir / "instructions.txt"
        instructions_path.write_text(spec.task.instructions, encoding="utf-8")
        await dtu.file_push(instructions_path, "/workspace/instructions.txt")

        # ---- run agent (the AI User drives it) -------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.RUNNING_AGENT)
        ai_start = time.monotonic()
        try:
            ai_result = await asyncio.wait_for(
                ai_user.run(
                    scenario=spec.task.instructions,
                    dtu_id=dtu.id,
                    invocation_guide=spec.agent.invocation_md,
                ),
                timeout=spec.task.timeout_s,
            )
        except asyncio.TimeoutError as exc:
            record.ai_user = {
                "status": "timeout",
                "timeout_s": spec.task.timeout_s,
                "elapsed_s": time.monotonic() - ai_start,
            }
            # Re-raise as TimeoutError (not RuntimeError) so the outer handler
            # records the original exception type in `record.error`. The raw
            # message + traceback is what we store; no separate category.
            raise TimeoutError(
                f"AI User exceeded task timeout of {spec.task.timeout_s}s"
            ) from exc

        record.ai_user = {
            "status": "ok",
            "verdict": ai_result.conclude.verdict if ai_result.conclude else None,
            "summary": ai_result.conclude.summary if ai_result.conclude else None,
            "elapsed_s": ai_result.elapsed_s,
            "session_id": ai_result.ai_user_session_id,
        }
        # Write the AI User's full result alongside trial artifacts.
        (trial_dir / "ai_user.json").write_text(
            json.dumps(asdict(ai_result), indent=2, default=str), encoding="utf-8"
        )
        state_io.save_state(trial_dir, record)

        # ---- extract ---------------------------------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.EXTRACTING)
        if spec.agent.data_yaml_path is not None:
            ext_dir = trial_dir / "extraction"
            try:
                ext_result = await extractor.run(
                    dtu_id=dtu.id,
                    task_context=spec.task.instructions,
                    data_yaml_path=spec.agent.data_yaml_path,
                    output_dir=ext_dir,
                )
                record.extractor = {
                    "status": "ok",
                    "manifest_entries": (
                        len(ext_result.manifest.extracted) if ext_result.manifest else 0
                    ),
                    "missing_items": (
                        len(ext_result.manifest.missing) if ext_result.manifest else 0
                    ),
                    "elapsed_s": ext_result.elapsed_s,
                }
            except Exception as exc:
                # Extraction failure shouldn't kill the trial; we still want
                # to grade and record what happened.
                record.extractor = {"status": "failed", "error": str(exc)}
                logger.exception("extractor failed for trial %s", spec.trial_id)
        else:
            record.extractor = {"status": "skipped", "reason": "no data.yaml"}
        state_io.save_state(trial_dir, record)

        # ---- grade -----------------------------------------------------
        _check_cancel(trial_dir)
        state_io.transition(trial_dir, record, TrialState.GRADING)
        grader_dir = trial_dir / "grader"
        try:
            grader_result = await grader.run(
                grader_yaml_path=spec.task.grader_yaml_path,
                task_context=spec.task.instructions,
                dtu_id=dtu.id,
                output_dir=grader_dir,
                grader_data_dir=spec.task.grader_data_dir,
            )
            record.grader = {
                "status": "ok",
                "overall_score": grader_result.overall_score,
                "evaluations": [
                    {"name": e.name, "score": e.score, "weight": e.weight}
                    for e in grader_result.evaluations
                ],
                "elapsed_s": grader_result.elapsed_s,
            }
        except Exception as exc:
            record.grader = {"status": "failed", "error": str(exc)}
            logger.exception("grader failed for trial %s", spec.trial_id)
        state_io.save_state(trial_dir, record)

        # ---- cleanup ---------------------------------------------------
        state_io.transition(trial_dir, record, TrialState.CLEANING_UP)
        if dtu is not None:
            await dtu.destroy()
            dtu = None

        record.elapsed_s = time.monotonic() - start
        state_io.transition(trial_dir, record, TrialState.COMPLETED)
        return _to_result(record)

    except TrialCancelled as exc:
        record.error = f"cancelled: {exc}"
        record.elapsed_s = time.monotonic() - start
        state_io.transition(trial_dir, record, TrialState.CANCELLED, note=str(exc))
        return _to_result(record)

    except Exception as exc:
        tb = traceback.format_exc(limit=20)
        record.error = f"{type(exc).__name__}: {exc}\n{tb}"
        record.elapsed_s = time.monotonic() - start
        state_io.append_log(
            trial_dir,
            f"[{utcnow_iso()}] FAILED in state={record.state}: {type(exc).__name__}: {exc}",
        )
        state_io.transition(
            trial_dir, record, TrialState.FAILED, note=f"{type(exc).__name__}: {exc}"
        )
        return _to_result(record)

    finally:
        # Always destroy the DTU. Errors during destroy are best-effort.
        if dtu is not None:
            try:
                await dtu.destroy()
            except DTUError as exc:
                logger.warning("dtu destroy on cleanup failed: %s", exc)


def _to_result(record: TrialStateRecord) -> TrialResult:
    return TrialResult(
        trial_id=record.trial_id,
        agent_id=record.agent_id,
        task_id=record.task_id,
        trial_number=record.trial_number,
        state=record.state,
        dtu_id=record.dtu_id,
        started_at=record.started_at,
        finished_at=record.finished_at,
        elapsed_s=record.elapsed_s,
        error=record.error,
        ai_user=record.ai_user,
        extractor=record.extractor,
        grader=record.grader,
        history=list(record.history),
    )
