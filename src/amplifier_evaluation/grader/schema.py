"""Parse grader.yaml into typed evaluation configs.

A grader.yaml describes a list of weighted evaluations. Each evaluation has
its own steps (what to do in the DTU) and rubric (criteria with points and
descriptions). The Grader runs one full audit pass per evaluation, then
aggregates a weighted overall score.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Criterion:
    """One scored item in an evaluation's rubric."""

    name: str
    points: int
    description: str


@dataclass
class Evaluation:
    """One weighted scored audit within a grader.yaml.

    `steps` is plain markdown describing what the auditor should do inside the
    Digital Twin Universe to inform its scoring. `rubric` is the ordered list
    of criteria; the JSON name in grader.yaml becomes `Criterion.name` and is
    used as the key when scoring is submitted.
    """

    name: str
    weight: float
    steps: str
    rubric: list[Criterion]

    @property
    def total_points(self) -> int:
        return sum(c.points for c in self.rubric)

    def rubric_dict(self) -> dict[str, dict[str, Any]]:
        """Return the rubric as a JSON-serializable dict for prompt rendering."""
        return {
            c.name: {"points": c.points, "description": c.description}
            for c in self.rubric
        }


@dataclass
class GraderConfig:
    """Parsed grader.yaml."""

    evaluations: list[Evaluation]

    @classmethod
    def from_yaml(cls, path: Path | str) -> "GraderConfig":
        text = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        if not isinstance(data, dict) or "evaluations" not in data:
            raise ValueError(f"{path}: expected top-level `evaluations:` list")

        raw_evals = data["evaluations"]
        if not isinstance(raw_evals, list) or not raw_evals:
            raise ValueError(f"{path}: `evaluations:` must be a non-empty list")

        evaluations: list[Evaluation] = []
        for i, ev in enumerate(raw_evals):
            try:
                evaluations.append(_parse_evaluation(ev))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}: evaluations[{i}]: {exc}") from exc
        return cls(evaluations=evaluations)


def _parse_evaluation(data: dict[str, Any]) -> Evaluation:
    if not isinstance(data, dict):
        raise ValueError("evaluation entry must be a mapping")
    name = str(data["name"])
    weight = float(data["weight"])
    steps = str(data["steps"])

    rubric_raw = data.get("rubric")
    if not isinstance(rubric_raw, dict) or not rubric_raw:
        raise ValueError("`rubric:` must be a non-empty mapping")

    rubric: list[Criterion] = []
    for key, crit in rubric_raw.items():
        if not isinstance(crit, dict):
            raise ValueError(f"rubric[{key}]: must be a mapping")
        rubric.append(
            Criterion(
                name=str(key),
                points=int(crit["points"]),
                description=str(crit["description"]),
            )
        )

    return Evaluation(name=name, weight=weight, steps=steps, rubric=rubric)
