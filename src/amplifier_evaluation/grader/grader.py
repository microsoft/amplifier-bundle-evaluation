"""Grader: an Amplifier Foundation session that audits an agent's work in a DTU.

- SYSTEM_INSTRUCTION (fixed): auditor framing + Digital Twin Universe bash
  wrapper rules.
- Evaluation steps (per-run): from the grader.yaml's `evaluations[].steps`.
- Evaluation rubric (per-run): from `evaluations[].rubric`, also embedded as
  the `submit_rubric` tool's input schema.

For each evaluation in the grader.yaml the Grader runs one session with three
phases on a single multi-turn session:

1. Explore the DTU and write a free-text initial report.
2. Submit the structured rubric via the `submit_rubric` tool.
3. If validation fails, ask for fixes (max 2 retries).

The final weighted score is computed across all evaluations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from amplifier_foundation import Bundle, load_bundle

from amplifier_evaluation.grader.schema import Evaluation, GraderConfig
from amplifier_evaluation.grader.tools import (
    CriterionScore,
    SubmitRubricTool,
    validate_rubric_submission,
)

logger = logging.getLogger(__name__)


DEFAULT_FOUNDATION_SOURCE = "git+https://github.com/microsoft/amplifier-foundation@main"
DEFAULT_PROVIDER_SOURCE = (
    "git+https://github.com/microsoft/amplifier-foundation@main"
    "#subdirectory=providers/anthropic-sonnet.yaml"
)

MAX_RETRIES = 2


SYSTEM_INSTRUCTION = """\
You are an auditor evaluating another AI agent's deliverables. Remain
impartial, critical, and objective. You will receive a list of steps to follow
during the audit and a rubric to score the agent's work against.

The agent's work lives inside a Digital Twin Universe container. You will
receive its id (like `dtu-abc12345`). You have a `bash` tool. To run a command
inside the Digital Twin Universe, prefix it with the exec wrapper:

    amplifier-digital-twin exec <dtu_id> -- <command>

For commands with tricky quoting or multi-line input, write your message to a
host file first and push it in:

    echo "<message>" > /tmp/msg.txt
    amplifier-digital-twin file-push <dtu_id> /tmp/msg.txt /tmp/msg.txt
    amplifier-digital-twin exec <dtu_id> -- bash -c 'cmd --input "$(cat /tmp/msg.txt)"'

ABSOLUTE RULES (NON-NEGOTIABLE):

- You must NEVER modify the agent's code or files. Changing its output is like
  a teacher changing a student's exam.
- You are NOT debugging or troubleshooting. Evaluate the work as-is. If
  something does not work after following the agent's instructions, note that
  and move on. Do not fix it.
- You should not need to obtain API keys. They are provided as environment
  variables in the container.
- Never read large PDFs or binary files directly. Write code to parse them
  into text instead.
- If a tool times out or hangs, treat that as a failure for that criterion.
- Ignore stale files or build artifacts from previous runs. Evaluate based
  only on what you observe during this audit.
- Be concise. Score what you saw with one or two sentences of reasoning per
  criterion.
"""


PHASE1_PROMPT_TEMPLATE = """\
The agent was asked to do the following:
\"\"\"
{task_context}
\"\"\"

You will evaluate the agent's work against this rubric. Each criterion has a
maximum point value and a description of what to look for:

{rubric_json}

The agent's work lives inside Digital Twin Universe `{dtu_id}`. Use bash with
`amplifier-digital-twin exec` to explore.

Follow these steps:

{steps}

After completing the steps, write a free-text "initial report" as your final
assistant message. The report should describe:

- What you observed in the DTU.
- For each criterion: your tentative scoring intent and what you saw.
- Anything you are uncertain about and how that affects scoring.

Do NOT call submit_rubric yet. Your final assistant message in this turn is
the initial report.
"""


PHASE2_PROMPT = """\
Now submit the structured rubric by calling the `submit_rubric` tool exactly
once.

For each criterion in the rubric, provide:

- points_awarded: integer in [0, max_points]
- reasoning: one or two sentences citing what you saw

Use the observations from your initial report. Do not run more bash commands
unless absolutely necessary. After submit_rubric, do not call any other tools.
"""


PHASE3_RETRY_TEMPLATE = """\
Your submit_rubric call had these problems:

{errors}

Call submit_rubric again with corrections. Only change the entries that were
flagged; leave correct entries as they were.
"""


async def _push_mounts(
    dtu_id: str,
    mounts: list,
    grader_data_dir: Path,
) -> None:
    """Push `Mount` entries from the host into the running DTU.

    Each mount is resolved as `grader_data_dir / source` on the host and
    pushed to its `destination` inside the DTU via `amplifier-digital-twin
    file-push`. Raises RuntimeError on the first failed push so the caller
    can mark the evaluation as failed deterministically.
    """
    for m in mounts:
        src = (grader_data_dir / m.source).resolve()
        if not src.exists():
            raise RuntimeError(
                f"mount source not found: {src} "
                f"(grader_data_dir={grader_data_dir}, source={m.source})"
            )
        logger.info("grader.mounts: pushing %s -> %s:%s", src, dtu_id, m.destination)
        proc = await asyncio.create_subprocess_exec(
            "amplifier-digital-twin",
            "file-push",
            dtu_id,
            str(src),
            m.destination,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"file-push failed for {src} -> {dtu_id}:{m.destination} "
                f"(exit {proc.returncode}): "
                f"{stderr.decode('utf-8', errors='replace').strip()}"
            )


@dataclass
class EvaluationResult:
    """Outcome of one evaluation's audit pass."""

    name: str
    weight: float
    initial_report: str
    rubric_scores: dict[str, CriterionScore] | None
    points_awarded: int
    points_possible: int
    score: float  # 0..1, points_awarded / points_possible (0.0 if unscored)
    validation_errors: list[str] = field(default_factory=list)
    submit_rubric_attempts: int = 0
    grader_session_id: str | None = None
    elapsed_s: float = 0.0


@dataclass
class GraderResult:
    """Outcome of grading a DTU against a grader.yaml."""

    dtu_id: str
    grader_yaml_path: str
    evaluations: list[EvaluationResult]
    overall_score: float  # weighted average, 0..1
    elapsed_s: float

    def to_json(self) -> str:
        """Serialize as a JSON string (dataclasses recursed via asdict)."""
        return json.dumps(asdict(self), indent=2)


class Grader:
    """Compose Foundation + provider + auditor system instruction, then grade."""

    def __init__(
        self,
        foundation_source: str = DEFAULT_FOUNDATION_SOURCE,
        provider_source: str = DEFAULT_PROVIDER_SOURCE,
    ) -> None:
        """Construct a Grader.

        Args:
            foundation_source: Source for the foundation bundle. Defaults to
                the canonical git URL so no local checkout is required.
                Accepts any string `load_bundle` understands.
            provider_source: Source for the provider bundle YAML. Defaults to
                the canonical foundation `anthropic-sonnet.yaml`.
        """
        self.foundation_source = foundation_source
        self.provider_source = provider_source
        self._prepared = None

    async def setup(self) -> None:
        """Load + compose + prepare the bundle. Expensive; call once."""
        foundation = await load_bundle(self.foundation_source)
        provider = await load_bundle(self.provider_source)
        system_bundle = Bundle(
            name="grader-system",
            version="0.1.0",
            instruction=SYSTEM_INSTRUCTION,
        )
        composed = foundation.compose(provider).compose(system_bundle)
        self._prepared = await composed.prepare()

    async def run(
        self,
        grader_yaml_path: Path | str,
        task_context: str,
        dtu_id: str,
        output_dir: Path | str,
        grader_data_dir: Path | str | None = None,
    ) -> GraderResult:
        """Audit a DTU against a grader.yaml. Runs each evaluation in turn.

        Args:
            grader_yaml_path: Path to the grader.yaml describing evaluations.
            task_context: The original task instructions handed to the agent
                under test, as a plain string. Provided as context to the
                auditor so it knows what the agent was supposed to do.
            dtu_id: The Digital Twin Universe instance id.
            output_dir: Directory on the host where initial reports and rubric
                JSON files will be written. Per-evaluation subdirectories are
                created under here.
            grader_data_dir: Host directory where `mounts[].source` paths are
                resolved against. Defaults to `<grader.yaml parent>/grader-data`
                if that directory exists, else the grader.yaml's parent.
        """
        if self._prepared is None:
            raise RuntimeError("Grader.setup() must be called before run().")

        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        grader_yaml = Path(grader_yaml_path)
        if grader_data_dir is None:
            default = grader_yaml.parent / "grader-data"
            data_dir = default if default.is_dir() else grader_yaml.parent
        else:
            data_dir = Path(grader_data_dir)

        config = GraderConfig.from_yaml(grader_yaml_path)

        start = time.monotonic()
        # Each evaluation runs in its own Foundation session against the same
        # live DTU; they are independent audits. Run them concurrently. The
        # absolute rule "never modify the agent's files" makes parallel reads
        # safe; if a future evaluation needs write access we will need to
        # serialize again.
        eval_dirs = []
        for evaluation in config.evaluations:
            eval_dir = out / evaluation.name
            eval_dir.mkdir(parents=True, exist_ok=True)
            eval_dirs.append(eval_dir)

        eval_results: list[EvaluationResult] = list(
            await asyncio.gather(
                *(
                    self._run_one_evaluation(
                        evaluation=evaluation,
                        task_context=task_context,
                        dtu_id=dtu_id,
                        eval_dir=eval_dir,
                        grader_data_dir=data_dir,
                    )
                    for evaluation, eval_dir in zip(
                        config.evaluations, eval_dirs, strict=True
                    )
                )
            )
        )

        total_weight = sum(e.weight for e in config.evaluations) or 1.0
        overall = sum(r.score * r.weight for r in eval_results) / total_weight

        grader_result = GraderResult(
            dtu_id=dtu_id,
            grader_yaml_path=str(grader_yaml_path),
            evaluations=eval_results,
            overall_score=overall,
            elapsed_s=time.monotonic() - start,
        )
        (out / "grader_result.json").write_text(
            grader_result.to_json(), encoding="utf-8"
        )
        return grader_result

    async def _run_one_evaluation(
        self,
        evaluation: Evaluation,
        task_context: str,
        dtu_id: str,
        eval_dir: Path,
        grader_data_dir: Path,
    ) -> EvaluationResult:
        if self._prepared is None:
            raise RuntimeError("Grader.setup() must be called before run().")
        start = time.monotonic()

        # Deterministic file pushes before the auditor runs. The grader yaml's
        # `mounts:` lists host -> DTU copies; we resolve sources against the
        # grader-data directory.
        if evaluation.mounts:
            await _push_mounts(
                dtu_id=dtu_id,
                mounts=evaluation.mounts,
                grader_data_dir=grader_data_dir,
            )

        submit_tool = SubmitRubricTool(evaluation)

        session_id = f"grader-{evaluation.name}-{uuid.uuid4().hex[:8]}"
        session = await self._prepared.create_session(
            session_id=session_id,
            session_cwd=Path.cwd(),
        )
        await session.coordinator.mount("tools", submit_tool, name=submit_tool.name)

        rubric_json = json.dumps(evaluation.rubric_dict(), indent=2)
        phase1_prompt = PHASE1_PROMPT_TEMPLATE.format(
            task_context=task_context.strip(),
            rubric_json=rubric_json,
            dtu_id=dtu_id,
            steps=evaluation.steps.strip(),
        )

        initial_report = ""
        validation_errors: list[str] = []
        rubric_scores: dict[str, CriterionScore] | None = None
        points_awarded = 0

        async with session:
            # Phase 1: explore + initial report (free text response).
            initial_report = await session.execute(phase1_prompt)
            (eval_dir / "initial_report.md").write_text(
                initial_report, encoding="utf-8"
            )

            # Phase 2/3: submit + retries.
            attempt_prompt = PHASE2_PROMPT
            for attempt in range(MAX_RETRIES + 1):
                _ = await session.execute(attempt_prompt)
                submission = submit_tool.last_submission
                if submission is None:
                    validation_errors = ["submit_rubric was not called"]
                else:
                    validation_errors = validate_rubric_submission(
                        submission, evaluation
                    )
                if not validation_errors and submission is not None:
                    rubric_scores = submission.scores
                    break
                if attempt < MAX_RETRIES:
                    attempt_prompt = PHASE3_RETRY_TEMPLATE.format(
                        errors="\n".join(f"  - {e}" for e in validation_errors)
                    )

        if rubric_scores is not None:
            points_awarded = sum(s.points_awarded for s in rubric_scores.values())
            (eval_dir / "rubric.json").write_text(
                json.dumps(
                    {k: asdict(v) for k, v in rubric_scores.items()},
                    indent=2,
                ),
                encoding="utf-8",
            )

        points_possible = evaluation.total_points
        score = (points_awarded / points_possible) if points_possible > 0 else 0.0

        return EvaluationResult(
            name=evaluation.name,
            weight=evaluation.weight,
            initial_report=initial_report,
            rubric_scores=rubric_scores,
            points_awarded=points_awarded,
            points_possible=points_possible,
            score=score,
            validation_errors=validation_errors,
            submit_rubric_attempts=submit_tool.call_count,
            grader_session_id=session_id,
            elapsed_s=time.monotonic() - start,
        )
