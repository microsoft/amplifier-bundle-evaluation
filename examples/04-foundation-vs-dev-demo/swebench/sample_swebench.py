#!/usr/bin/env python3
"""Host-side SWE-bench Multimodal sampler.

Downloads the SWE-bench Multimodal dataset from HuggingFace (open access, no
HF_TOKEN required), picks one instance from the dev split (either by pinned id
or by seed=42), and stages it into the run directory:

    <output>/
        instance.json          # full SWE-bench record (incl. gold patch + test_patch)
        problem_statement.md   # just the issue text (this is what goes into the DTU)

If a pinned-id file is provided and exists, the script uses that id. Otherwise
it samples randomly with the given seed and writes the chosen id to the pinned
file so subsequent runs reuse the same instance.

Run via uv to avoid polluting the host env:
    uv run --quiet --with huggingface_hub --with pyarrow \\
        python3 swebench/sample_swebench.py \\
            --output results/<date>/run-1/sample \\
            --pinned-file swebench/PINNED_INSTANCE_ID
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

_REPO_ID = "princeton-nlp/SWE-bench_Multimodal"
# dev split has 102 instances, all with public test patches (gradable locally).
_FILENAME = "data/dev-00000-of-00001.parquet"


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


def _download_dataset(cache_dir: Path) -> Path:
    """Download the SWE-bench Multimodal dev parquet from HuggingFace if absent."""
    from huggingface_hub import hf_hub_download  # pyright: ignore[reportMissingImports]

    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / "swebench_mm_dev.parquet"
    if output_path.exists():
        return output_path

    try:
        cached_path = hf_hub_download(
            repo_id=_REPO_ID,
            filename=_FILENAME,
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


def _select_sample(
    samples: list[SWEBenchSample],
    pinned_id: str | None,
    seed: int,
    filter_repo: str | None,
) -> SWEBenchSample:
    if pinned_id:
        for s in samples:
            if s.instance_id == pinned_id:
                return s
        raise SystemExit(
            f"ERROR: pinned instance id {pinned_id!r} not found in dev split"
        )

    pool = samples
    if filter_repo:
        pool = [s for s in samples if s.repo == filter_repo]
        if not pool:
            raise SystemExit(f"ERROR: no instances for repo={filter_repo!r}")
    rng = random.Random(seed)
    return rng.choice(pool)


def _count_tests(value: str) -> int:
    """FAIL_TO_PASS / PASS_TO_PASS are stored as JSON-string lists."""
    if not value:
        return 0
    try:
        parsed = json.loads(value)
        return len(parsed) if isinstance(parsed, list) else 0
    except json.JSONDecodeError:
        return 0


def _count_image_assets(value: str) -> int:
    """image_assets is stored as a JSON-string dict {field: [urls...]}."""
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample one SWE-bench Multimodal instance to disk"
    )
    parser.add_argument(
        "--output", type=Path, required=True, help="output dir for sample files"
    )
    parser.add_argument(
        "--pinned-file",
        type=Path,
        default=None,
        help="path to a file containing the pinned instance id "
        "(read if exists, written if pinning)",
    )
    parser.add_argument(
        "--instance-id",
        type=str,
        default=None,
        help="explicit instance id override",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="random seed when no pin is set"
    )
    parser.add_argument(
        "--filter-repo",
        type=str,
        default=None,
        help="optionally restrict the sampling pool to a specific repo "
        "(e.g. chartjs/Chart.js, markedjs/marked). Default: full dev split.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "amplifier-eval-swebench-mm",
        help="where to cache the downloaded parquet",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    pinned_id = args.instance_id
    if pinned_id is None and args.pinned_file and args.pinned_file.exists():
        content = args.pinned_file.read_text().strip()
        pinned_id = content if content else None

    print(
        f"[sample_swebench] downloading {_REPO_ID}/{_FILENAME}",
        file=sys.stderr,
    )
    parquet_path = _download_dataset(args.cache_dir)
    parquet_sha = _file_sha256(parquet_path)
    print(f"[sample_swebench] parquet sha256={parquet_sha[:16]}...", file=sys.stderr)

    samples = _load_all_samples(parquet_path)
    print(
        f"[sample_swebench] loaded {len(samples)} dev-split instances",
        file=sys.stderr,
    )

    chosen = _select_sample(samples, pinned_id, args.seed, args.filter_repo)
    fail_n = _count_tests(chosen.fail_to_pass)
    pass_n = _count_tests(chosen.pass_to_pass)
    img_n = _count_image_assets(chosen.image_assets)
    print(
        f"[sample_swebench] selected instance_id={chosen.instance_id} "
        f"repo={chosen.repo} "
        f"FAIL_TO_PASS={fail_n} PASS_TO_PASS={pass_n} images={img_n}",
        file=sys.stderr,
    )

    if pinned_id is None and args.pinned_file:
        args.pinned_file.parent.mkdir(parents=True, exist_ok=True)
        args.pinned_file.write_text(chosen.instance_id + "\n")
        print(
            f"[sample_swebench] pinned {chosen.instance_id} to {args.pinned_file}",
            file=sys.stderr,
        )

    record = asdict(chosen)
    record["parquet_sha256"] = parquet_sha
    record["seed"] = args.seed if pinned_id is None else None
    record["pinned"] = pinned_id is not None
    record["fail_to_pass_count"] = fail_n
    record["pass_to_pass_count"] = pass_n
    record["image_count_problem_statement"] = img_n

    (args.output / "instance.json").write_text(json.dumps(record, indent=2))
    (args.output / "problem_statement.md").write_text(chosen.problem_statement)

    print(f"[sample_swebench] wrote sample to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
