#!/usr/bin/env python3
"""Replay the PATCHED driver's continuity logic over every captured S3 run. $0.

For each `driver_record.json` in the evals repo's capture tree that carries a
`session_continuity_ok` field, this re-derives the session id of every turn
from that turn's own `turn<n>.out` -- using the PATCHED driver's own
`capture_sid` and `continuity_ok`, imported by path, so the number below is
produced by the shipped fix and not by a second implementation of it.

Usage:
    python3 replay_corpus_continuity.py [--driver <patched scripted_driver.py>]
                                        [--captures <treatment-validation dir>]

Reads only. Writes nothing. Spends nothing.
"""

from __future__ import annotations

import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path

DEFAULT_CAPTURES = Path(
    "/home/bkrabach/dev/openai-evals-team-ci/.amplifier/evaluation/treatment-validation"
)


def load_driver(path: Path):
    spec = importlib.util.spec_from_file_location("s3_driver_replay", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "continuity_ok"):
        sys.exit(
            f"{path} has no continuity_ok(): point --driver at the PATCHED driver "
            "(apply i0cm-scripted-driver-continuity.patch to a copy first)."
        )
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--driver", required=True, type=Path)
    ap.add_argument("--captures", default=DEFAULT_CAPTURES, type=Path)
    args = ap.parse_args()
    mod = load_driver(args.driver)

    total = 0
    flag_true = 0
    fixed_true = 0
    disagreements: list[tuple[str, str]] = []
    per_root: dict[str, list[int]] = collections.defaultdict(lambda: [0, 0])
    empty_runs = 0
    empty_turns = 0

    for dr in sorted(args.captures.rglob("driver_record.json")):
        try:
            rec = json.loads(dr.read_text())
        except Exception:
            continue
        if "session_continuity_ok" not in rec:
            continue
        total += 1
        root = dr.relative_to(args.captures).parts[0]
        flag_true += bool(rec.get("session_continuity_ok"))

        turns = []
        for t in rec.get("turns", []):
            out_path = dr.parent / f"turn{t['n']}.out"
            out = out_path.read_text(errors="replace") if out_path.exists() else ""
            turns.append({"session_id": mod.capture_sid(out), "out_len": len(out)})
        n_empty = sum(1 for t in turns if t["out_len"] == 0)
        if n_empty:
            empty_runs += 1
            empty_turns += n_empty

        ok = mod.continuity_ok(turns)
        per_root[root][1] += 1
        if ok:
            fixed_true += 1
            per_root[root][0] += 1
        else:
            ids = sorted({t["session_id"] for t in turns if t["session_id"]})
            why = (
                f"{len(ids)} distinct session ids {ids}"
                if len(ids) > 1
                else f"{len(turns) - len([t for t in turns if t['session_id']]) - n_empty} turn(s) with output but no session line"
            )
            disagreements.append((str(dr.parent.relative_to(args.captures)), why))

    print(f"driver records carrying session_continuity_ok : {total}")
    print(f"  driver's OWN flag True                      : {flag_true}")
    print(f"  PATCHED continuity_ok True                  : {fixed_true}")
    print(f"  PATCHED continuity_ok False                 : {total - fixed_true}")
    print(f"  runs with >=1 empty turn capture            : {empty_runs} ({empty_turns} turns)")
    print("\nruns the CORRECTED check still calls broken:")
    for run, why in disagreements:
        print(f"  {run}\n      {why}")
    print("\nper capture root (corrected_true / total):")
    for root in sorted(per_root):
        ok, n = per_root[root]
        print(f"  {root:<34} {ok:>3}/{n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
