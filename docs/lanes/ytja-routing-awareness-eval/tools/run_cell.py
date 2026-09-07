#!/usr/bin/env python3
"""ytja routing-awareness driver.

One launch = one FRESH amplifier session in an arm container, given exactly one
short prompt. The run's root session is identified by diffing the container's
session directory before and after the launch -- never by parsing stdout, which
`8rugb` showed is unreliable (empty stdout on large turns) and which `i0cm`
showed can silently disagree with the real session id.

Resumable: a run already present in runs.jsonl is skipped.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ADT = "amplifier-digital-twin"


def dtu_exec(dtu: str, script: str, timeout: int = 1200) -> tuple[int, str, str]:
    """Run a bash script in the container. Unwraps the DTU JSON envelope and
    returns the INNER exit code -- the envelope's own rc is not the command's."""
    p = subprocess.run(
        [ADT, "exec", "--timeout", str(timeout), dtu, "--", "bash", "-lc", script],
        capture_output=True,
        text=True,
        timeout=timeout + 120,
    )
    raw = p.stdout
    try:
        env = json.loads(raw)
        return (
            int(env.get("exit_code", p.returncode)),
            env.get("stdout", ""),
            env.get("stderr", ""),
        )
    except (json.JSONDecodeError, ValueError):
        return p.returncode, raw, p.stderr


def session_ids(dtu: str) -> set[str]:
    rc, out, _ = dtu_exec(
        dtu, "ls /root/.amplifier/projects/*/sessions 2>/dev/null || true", timeout=120
    )
    return {
        ln.strip()
        for ln in out.splitlines()
        if ln.strip() and "-" in ln and ":" not in ln
    }


def shell_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dtu", required=True)
    ap.add_argument("--arm", required=True)
    ap.add_argument(
        "--provider",
        required=True,
        help="provider id in settings.yaml, e.g. opus / terra",
    )
    ap.add_argument("--model", required=True)
    ap.add_argument("--prompts", required=True, help="path to prompts.json")
    ap.add_argument("--out", required=True, help="capture root")
    ap.add_argument("--reps", type=int, required=True)
    ap.add_argument("--rep-start", type=int, default=1)
    ap.add_argument(
        "--only", default="", help="comma-separated prompt ids to run (default all)"
    )
    ap.add_argument("--timeout", type=int, default=900)
    args = ap.parse_args()

    spec = json.loads(Path(args.prompts).read_text())
    items = [(p["id"], p["prompt"], "hidden") for p in spec["hidden"]]
    items += [(c["id"], c["prompt"], "control") for c in spec["controls"]]
    if args.only:
        keep = {x.strip() for x in args.only.split(",") if x.strip()}
        items = [it for it in items if it[0] in keep]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = out / "runs.jsonl"
    done: set[str] = set()
    if ledger.exists():
        for ln in ledger.read_text().splitlines():
            try:
                done.add(json.loads(ln)["run_id"])
            except Exception:
                pass

    for rep in range(args.rep_start, args.rep_start + args.reps):
        for pid, ptext, kind in items:
            run_id = f"{args.arm}-{args.provider}-{pid}-r{rep:02d}"
            if run_id in done:
                print(f"[skip] {run_id}", flush=True)
                continue
            before = session_ids(args.dtu)
            cmd = (
                f"cd /root/work && amplifier run -p {args.provider} -m {args.model} "
                f"{shell_quote(ptext)} 2>&1 | tail -c 4000"
            )
            t0 = time.time()
            rc, sout, serr = dtu_exec(args.dtu, cmd, timeout=args.timeout)
            wall = time.time() - t0
            after = session_ids(args.dtu)
            new = sorted(after - before)
            rec = {
                "run_id": run_id,
                "arm": args.arm,
                "dtu": args.dtu,
                "provider": args.provider,
                "model": args.model,
                "prompt_id": pid,
                "kind": kind,
                "rep": rep,
                "rc": rc,
                "wall_s": round(wall, 1),
                "new_sessions": new,
                "stdout_tail": sout[-1500:],
                "stderr_tail": serr[-800:],
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            with ledger.open("a") as f:
                f.write(json.dumps(rec) + "\n")
            print(
                f"[run ] {run_id} rc={rc} wall={wall:.0f}s new_sessions={len(new)}",
                flush=True,
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
