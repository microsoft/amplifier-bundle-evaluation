#!/usr/bin/env python3
"""Host-side HLE sampler (multi-task).

Downloads cais/hle from HuggingFace, picks N samples (either by a pinned id
list or by random.Random(seed).sample over the full pool), and stages them
into the run directory:

    <output>/
        task-1/
            sample.json
            question.md
            question_image.<ext>   (only if the sample has an image)
        task-2/
            ...
        task-3/
            ...

If a pinned-id file is provided and contains at least N ids (one per line),
the script uses those ids. Otherwise it samples N unique tasks randomly with
the given seed and writes the chosen ids back to the pinned file so
subsequent runs reuse the same tasks.

Run via uv to avoid polluting the host env:
    uv run --quiet --with huggingface_hub --with pyarrow \
        python3 hle/sample_hle.py --output results/<date>/_samples/hle \
                                  --num 3 \
                                  --pinned-file hle/PINNED_SAMPLE_IDS
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import random
import re
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_REPO_ID = "cais/hle"
_FILENAME = "data/test-00000-of-00001.parquet"


@dataclass(frozen=True)
class HLESample:
    id: str
    question: str
    answer: str
    answer_type: str
    image: str | None


def _hf_token() -> str | None:
    return os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")


def _download_dataset(cache_dir: Path) -> Path:
    from huggingface_hub import hf_hub_download  # pyright: ignore[reportMissingImports]

    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / "hle_test.parquet"
    if output_path.exists():
        return output_path

    token = _hf_token()
    if not token:
        print(
            "ERROR: HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) is not set.\n"
            "       cais/hle is a gated dataset.\n",
            file=sys.stderr,
        )
        sys.exit(2)

    try:
        cached_path = hf_hub_download(
            repo_id=_REPO_ID,
            filename=_FILENAME,
            repo_type="dataset",
            token=token,
        )
    except Exception as exc:
        print(f"ERROR: HuggingFace download failed: {exc}", file=sys.stderr)
        sys.exit(2)
    shutil.copy(cached_path, output_path)
    return output_path


def _load_all_samples(parquet_path: Path) -> list[HLESample]:
    import pyarrow.parquet as pq  # pyright: ignore[reportMissingImports]

    table = pq.read_table(parquet_path)
    samples: list[HLESample] = []
    for i in range(table.num_rows):
        row = {col: table.column(col)[i].as_py() for col in table.column_names}
        samples.append(
            HLESample(
                id=row["id"],
                question=row["question"],
                answer=row["answer"],
                answer_type=row["answer_type"],
                image=row.get("image") or None,
            )
        )
    return samples


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _save_image(sample: HLESample, out_dir: Path) -> str | None:
    if not sample.image:
        return None
    match = re.match(r"data:image/(\w+);base64,(.+)", sample.image, re.DOTALL)
    if match is None:
        raise ValueError(f"Unexpected image data URI format for sample {sample.id}")
    ext = match.group(1)
    data = base64.b64decode(match.group(2))
    image_name = f"question_image.{ext}"
    (out_dir / image_name).write_bytes(data)
    return image_name


def _select_samples(
    samples: list[HLESample],
    pinned_ids: list[str],
    num: int,
    seed: int,
) -> list[HLESample]:
    by_id = {s.id: s for s in samples}
    chosen: list[HLESample] = []
    if len(pinned_ids) >= num:
        for pid in pinned_ids[:num]:
            if pid not in by_id:
                raise SystemExit(f"ERROR: pinned id {pid!r} not in dataset")
            chosen.append(by_id[pid])
        return chosen
    rng = random.Random(seed)
    return rng.sample(samples, num)


def _write_task(task_dir: Path, sample: HLESample, parquet_sha: str, seed: int | None, pinned: bool) -> None:
    task_dir.mkdir(parents=True, exist_ok=True)
    record = asdict(sample)
    has_image = bool(record.pop("image", None))
    record["has_image"] = has_image
    record["parquet_sha256"] = parquet_sha
    record["seed"] = seed
    record["pinned"] = pinned

    (task_dir / "question.md").write_text(sample.question)
    image_name = _save_image(sample, task_dir)
    if image_name:
        record["image_filename"] = image_name
    (task_dir / "sample.json").write_text(json.dumps(record, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample N HLE questions to disk")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--num", type=int, default=3)
    parser.add_argument("--pinned-file", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "amplifier-eval-hle",
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

    print(f"[sample_hle] downloading {_REPO_ID}/{_FILENAME}", file=sys.stderr)
    parquet_path = _download_dataset(args.cache_dir)
    parquet_sha = _file_sha256(parquet_path)
    print(f"[sample_hle] parquet sha256={parquet_sha[:16]}...", file=sys.stderr)

    samples = _load_all_samples(parquet_path)
    print(f"[sample_hle] loaded {len(samples)} total samples", file=sys.stderr)

    chosen = _select_samples(samples, pinned_ids, args.num, args.seed)
    chosen_ids = [s.id for s in chosen]
    print(
        f"[sample_hle] selected {len(chosen)} tasks: {chosen_ids}",
        file=sys.stderr,
    )

    pinned = bool(pinned_ids and len(pinned_ids) >= args.num)
    if not pinned and args.pinned_file:
        args.pinned_file.parent.mkdir(parents=True, exist_ok=True)
        args.pinned_file.write_text("\n".join(chosen_ids) + "\n")
        print(
            f"[sample_hle] pinned {len(chosen_ids)} ids to {args.pinned_file}",
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
        )
        print(
            f"[sample_hle] task-{idx}: id={sample.id} answer_type={sample.answer_type} image={bool(sample.image)}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()