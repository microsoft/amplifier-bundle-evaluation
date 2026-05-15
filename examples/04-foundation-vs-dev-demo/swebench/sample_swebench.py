#!/usr/bin/env python3
"""Host-side SWE-bench Multimodal sampler (multi-task).

Downloads princeton-nlp/SWE-bench_Multimodal (open access, no HF_TOKEN
required), picks N instances from the dev split (either by pinned ids or by
random.Random(seed).sample), and stages them into the run directory:

    <output>/
        task-1/
            instance.json
            problem_statement.md
        task-2/
            ...
        task-3/
            ...

If a pinned-id file is provided and contains at least N ids (one per line),
those ids are used. Otherwise N unique instances are sampled randomly with
the given seed and the chosen ids are written back to the pinned file.

Run via uv to avoid polluting the host env:
    uv run --quiet --with huggingface_hub --with pyarrow \
        python3 swebench/sample_swebench.py \
            --output results/<date>/_samples/swebench \
            --num 3 \
            --pinned-file swebench/PINNED_INSTANCE_IDS
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Dataset configuration. The "multimodal" dataset uses the dev split (102
# JS instances, public test patches, gradable locally). The "verified" dataset
# uses the test split (500 Python instances, all human-curated to be locally
# gradable). image_assets is only present on the multimodal dataset.
_DATASETS = {
    "multimodal": {
        "repo_id": "princeton-nlp/SWE-bench_Multimodal",
        "filename": "data/dev-00000-of-00001.parquet",
        "split": "dev",
        "language": "javascript",
    },
    "verified": {
        "repo_id": "princeton-nlp/SWE-bench_Verified",
        "filename": "data/test-00000-of-00001.parquet",
        "split": "test",
        "language": "python",
    },
}


@dataclass(frozen=True)
class SWEBenchSample:
    instance_id: str
    repo: str
    base_commit: str
    patch: str
    test_patch: str
    problem_statement: str
    hints_text: str
    created_at: str
    image_assets: str
    version: str
    fail_to_pass: str
    pass_to_pass: str


def _download_dataset(cache_dir: Path, dataset: str) -> Path:
    from huggingface_hub import hf_hub_download  # pyright: ignore[reportMissingImports]

    cfg = _DATASETS[dataset]
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / f"swebench_{dataset}_{cfg['split']}.parquet"
    if output_path.exists():
        return output_path

    try:
        cached_path = hf_hub_download(
            repo_id=cfg["repo_id"],
            filename=cfg["filename"],
            repo_type="dataset",
        )
    except Exception as exc:
        print(f"ERROR: HuggingFace download failed: {exc}", file=sys.stderr)
        sys.exit(2)
    shutil.copy(cached_path, output_path)
    return output_path


def _load_all_samples(parquet_path: Path) -> list[SWEBenchSample]:
    import pyarrow.parquet as pq  # pyright: ignore[reportMissingImports]

    table = pq.read_table(parquet_path)
    samples: list[SWEBenchSample] = []
    for i in range(table.num_rows):
        row = {col: table.column(col)[i].as_py() for col in table.column_names}
        samples.append(
            SWEBenchSample(
                instance_id=row["instance_id"],
                repo=row["repo"],
                base_commit=row["base_commit"],
                patch=row["patch"],
                test_patch=row["test_patch"],
                problem_statement=row["problem_statement"],
                hints_text=row.get("hints_text", "") or "",
                created_at=row["created_at"],
                image_assets=row.get("image_assets", "") or "",
                version=row.get("version", "") or "",
                fail_to_pass=row["FAIL_TO_PASS"],
                pass_to_pass=row["PASS_TO_PASS"],
            )
        )
    return samples


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _select_samples(
    samples: list[SWEBenchSample],
    pinned_ids: list[str],
    num: int,
    seed: int,
) -> list[SWEBenchSample]:
    by_id = {s.instance_id: s for s in samples}
    chosen: list[SWEBenchSample] = []
    if len(pinned_ids) >= num:
        for pid in pinned_ids[:num]:
            if pid not in by_id:
                raise SystemExit(
                    f"ERROR: pinned id {pid!r} not in dev split"
                )
            chosen.append(by_id[pid])
        return chosen
    rng = random.Random(seed)
    return rng.sample(samples, num)


def _count_tests(value: str) -> int:
    if not value:
        return 0
    try:
        parsed = json.loads(value)
        return len(parsed) if isinstance(parsed, list) else 0
    except json.JSONDecodeError:
        return 0


def _count_image_assets(value: str) -> int:
    if not value:
        return 0
    try:
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            return 0
        ps = parsed.get("problem_statement", [])
        return len(ps) if isinstance(ps, list) else 0
    except json.JSONDecodeError:
        return 0


def _write_task(task_dir: Path, sample: SWEBenchSample, parquet_sha: str, seed: int | None, pinned: bool, dataset: str) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    record = asdict(sample)
    record["parquet_sha256"] = parquet_sha
    record["seed"] = seed
    record["pinned"] = pinned
    record["dataset"] = dataset
    record["language"] = _DATASETS[dataset]["language"]
    record["fail_to_pass_count"] = _count_tests(sample.fail_to_pass)
    record["pass_to_pass_count"] = _count_tests(sample.pass_to_pass)
    record["image_count_problem_statement"] = _count_image_assets(sample.image_assets)

    (task_dir / "instance.json").write_text(json.dumps(record, indent=2))
    (task_dir / "problem_statement.md").write_text(sample.problem_statement)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample N SWE-bench instances to disk"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num", type=int, default=3)
    parser.add_argument("--pinned-file", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--dataset",
        choices=list(_DATASETS.keys()),
        default="multimodal",
        help="Which SWE-bench dataset to sample from (default: multimodal)",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "amplifier-eval-swebench",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    pinned_ids: list[str] = []
    if args.pinned_file and args.pinned_file.exists():
        pinned_ids = [
            line.strip()
            for line in args.pinned_file.read_text().splitlines()
            if line.strip()
        ]

    cfg = _DATASETS[args.dataset]
    print(
        f"[sample_swebench] dataset={args.dataset} ({cfg['repo_id']}, split={cfg['split']})",
        file=sys.stderr,
    )
    parquet_path = _download_dataset(args.cache_dir, args.dataset)
    parquet_sha = _file_sha256(parquet_path)
    print(
        f"[sample_swebench] parquet sha256={parquet_sha[:16]}...", file=sys.stderr
    )

    samples = _load_all_samples(parquet_path)
    print(
        f"[sample_swebench] loaded {len(samples)} {cfg['split']}-split instances",
        file=sys.stderr,
    )

    chosen = _select_samples(samples, pinned_ids, args.num, args.seed)
    chosen_ids = [s.instance_id for s in chosen]
    print(
        f"[sample_swebench] selected {len(chosen)} tasks: {chosen_ids}",
        file=sys.stderr,
    )

    pinned = bool(pinned_ids and len(pinned_ids) >= args.num)
    if not pinned and args.pinned_file:
        args.pinned_file.parent.mkdir(parents=True, exist_ok=True)
        args.pinned_file.write_text("\n".join(chosen_ids) + "\n")
        print(
            f"[sample_swebench] pinned {len(chosen_ids)} ids to {args.pinned_file}",
            file=sys.stderr,
        )

    for idx, sample in enumerate(chosen, 1):
        task_dir = args.output / f"task-{idx}"
        _write_task(
            task_dir,
            sample,
            parquet_sha,
            seed=None if pinned else args.seed,
            pinned=pinned,
            dataset=args.dataset,
        )
        print(
            f"[sample_swebench] task-{idx}: id={sample.instance_id} repo={sample.repo} "
            f"F2P={_count_tests(sample.fail_to_pass)} P2P={_count_tests(sample.pass_to_pass)}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()