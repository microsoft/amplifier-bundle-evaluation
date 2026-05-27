"""Parse grader.yaml into typed evaluation configs.

A grader.yaml describes a list of weighted evaluations. Each evaluation has
its own steps (what to do in the DTU) and rubric (criteria with points and
descriptions). The Grader runs one full audit pass per evaluation, then
aggregates a weighted overall score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
class Mount:
    """A host -> DTU file/directory copy performed before an evaluation runs.

    `source` is interpreted relative to the grader-data directory (sibling of
    grader.yaml by convention). `destination` is an absolute path inside the
    Digital Twin Universe.
    """

    source: str
    destination: str


@dataclass
class Evaluation:
    """One weighted scored audit within a grader.yaml.

    `steps` is plain markdown describing what the auditor should do inside the
    Digital Twin Universe to inform its scoring. `rubric` is the ordered list
    of criteria; the JSON name in grader.yaml becomes `Criterion.name` and is
    used as the key when scoring is submitted.

    `mounts` lists deterministic file/directory pushes performed *before* the
    auditor runs. Use this for evaluation helper scripts, fixtures, or data
    the auditor needs to see inside the DTU. Paths in `source` are relative
    to the grader-data directory.
    """

    name: str
    weight: float
    steps: str
    rubric: list[Criterion]
    mounts: list[Mount] = field(default_factory=list)

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

    mounts_raw = data.get("mounts", [])
    if not isinstance(mounts_raw, list):
        raise ValueError("`mounts:` must be a list when present")
    mounts: list[Mount] = []
    for i, m in enumerate(mounts_raw):
        if not isinstance(m, dict):
            raise ValueError(f"mounts[{i}]: must be a mapping")
        try:
            mounts.append(
                Mount(source=str(m["source"]), destination=str(m["destination"]))
            )
        except KeyError as exc:
            raise ValueError(f"mounts[{i}]: missing required field {exc}") from exc

    return Evaluation(
        name=name, weight=weight, steps=steps, rubric=rubric, mounts=mounts
    )
