#!/usr/bin/env python3
"""Host-side HLE sampler.

Downloads cais/hle from HuggingFace, picks a single sample (either by pinned id
or by seed=42 over answer_type=='exactMatch' rows), and stages it into the run
directory:

    <output>/
        sample.json          # full HLE record (includes ground-truth answer)
        question.md          # just the question text (this is what goes into the DTU)
        question_image.<ext> # decoded image if the sample has one

If a pinned-id file is provided and exists, the script uses that id. Otherwise
it samples randomly with the given seed and writes the chosen id to the pinned
file so subsequent runs reuse the same sample.

Run via uv to avoid polluting the host env:
    uv run --with huggingface_hub --with pyarrow \\
        python3 hle/sample_hle.py --output results/<date>/run-1/sample \\
                                  --pinned-file hle/PINNED_SAMPLE_ID
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
    """Download the HLE parquet file from HuggingFace if not already present."""
    from huggingface_hub import hf_hub_download  # pyright: ignore[reportMissingImports]

    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / "hle_test.parquet"
    if output_path.exists():
        return output_path

    token = _hf_token()
    if not token:
        print(
            "ERROR: HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) is not set.\n"
            "       The cais/hle dataset is gated; you need to:\n"
            "         1. Accept terms at https://huggingface.co/datasets/cais/hle\n"
            "         2. Create a read token at https://huggingface.co/settings/tokens\n"
            "         3. Export HF_TOKEN or add it to ~/.amplifier/keys.env\n",
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
        print(
            "       If this is a 403, you have not accepted the cais/hle terms yet:\n"
            "       visit https://huggingface.co/datasets/cais/hle and accept.",
            file=sys.stderr,
        )
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


def _select_sample(
    samples: list[HLESample],
    pinned_id: str | None,
    seed: int,
    filter_answer_type: str | None,
) -> HLESample:
    if pinned_id:
        for s in samples:
            if s.id == pinned_id:
                return s
        raise SystemExit(f"ERROR: pinned sample id {pinned_id!r} not found in dataset")

    pool = samples
    if filter_answer_type:
        pool = [s for s in samples if s.answer_type == filter_answer_type]
        if not pool:
            raise SystemExit(
                f"ERROR: no samples with answer_type={filter_answer_type!r}"
            )
    rng = random.Random(seed)
    return rng.choice(pool)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample one HLE question to disk")
    parser.add_argument(
        "--output", type=Path, required=True, help="output dir for sample files"
    )
    parser.add_argument(
        "--pinned-file",
        type=Path,
        default=None,
        help="path to a file containing the pinned sample id (read if exists, written if pinning)",
    )
    parser.add_argument(
        "--sample-id", type=str, default=None, help="explicit sample id override"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="random seed when no pin is set"
    )
    parser.add_argument(
        "--filter-answer-type",
        type=str,
        default=None,
        help="optionally restrict the sampling pool to a specific answer_type "
        "(e.g. exactMatch, multipleChoice). Default: no filter; sample from the "
        "full dataset. The HLE judge prompt handles all answer types semantically.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path.home() / ".cache" / "amplifier-eval-hle",
        help="where to cache the downloaded parquet",
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    pinned_id = args.sample_id
    if pinned_id is None and args.pinned_file and args.pinned_file.exists():
        pinned_id = args.pinned_file.read_text().strip() or None

    print(f"[sample_hle] downloading {_REPO_ID}/{_FILENAME}", file=sys.stderr)
    parquet_path = _download_dataset(args.cache_dir)
    parquet_sha = _file_sha256(parquet_path)
    print(f"[sample_hle] parquet sha256={parquet_sha[:16]}...", file=sys.stderr)

    samples = _load_all_samples(parquet_path)
    print(f"[sample_hle] loaded {len(samples)} total samples", file=sys.stderr)

    chosen = _select_sample(samples, pinned_id, args.seed, args.filter_answer_type)
    print(
        f"[sample_hle] selected id={chosen.id} answer_type={chosen.answer_type} image={bool(chosen.image)}",
        file=sys.stderr,
    )

    if pinned_id is None and args.pinned_file:
        args.pinned_file.parent.mkdir(parents=True, exist_ok=True)
        args.pinned_file.write_text(chosen.id + "\n")
        print(f"[sample_hle] pinned {chosen.id} to {args.pinned_file}", file=sys.stderr)

    # Strip the image from the saved record metadata to keep sample.json small;
    # the decoded image is saved separately. We still record whether one was present.
    record = asdict(chosen)
    has_image = bool(record.pop("image", None))
    record["has_image"] = has_image
    record["parquet_sha256"] = parquet_sha
    record["seed"] = args.seed if pinned_id is None else None
    record["pinned"] = pinned_id is not None or args.pinned_file is not None

    (args.output / "sample.json").write_text(json.dumps(record, indent=2))
    (args.output / "question.md").write_text(chosen.question)
    image_name = _save_image(chosen, args.output)
    if image_name:
        # update sample.json with the image filename
        record["image_filename"] = image_name
        (args.output / "sample.json").write_text(json.dumps(record, indent=2))

    print(f"[sample_hle] wrote sample to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
