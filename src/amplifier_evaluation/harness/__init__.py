"""Evaluation harness: orchestrates AI User, Extractor, and Grader across many trials.

The harness is intentionally modular. Each submodule has a single responsibility
and a small typed contract so consumers can either:

- call the assembled `run()` from `harness.run` to do everything end-to-end, or
- import individual pieces (loaders, the DTU wrapper, the trial runner, the
  scheduler) and compose their own flow.

The default flow per trial is deterministic:

    launch DTU -> install agent -> seed workspace + task -> AIUser
    -> Extractor -> Grader -> destroy DTU

State for every trial is persisted to disk under
`<output_dir>/trials/<trial-id>/state.json`. The scheduler reads and writes
this file at every stage transition, which means:

- A crashed harness can be re-run and it will pick up unfinished trials.
- An external agent can read the state files to see what's happening, and can
  write `cancel_requested: true` or `retry_requested: true` to a trial's
  state.json to course-correct a long-running batch.
"""

from amplifier_evaluation.harness.schema import (
    AgentSpec,
    RunSpec,
    RunResult,
    TaskSpec,
    TrialResult,
    TrialSpec,
    TrialState,
)

__all__ = [
    "AgentSpec",
    "RunResult",
    "RunSpec",
    "TaskSpec",
    "TrialResult",
    "TrialSpec",
    "TrialState",
]
