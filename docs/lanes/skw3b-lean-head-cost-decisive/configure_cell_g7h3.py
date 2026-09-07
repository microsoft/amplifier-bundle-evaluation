#!/usr/bin/env python3
"""Configure a launched eval container for one matrix cell (S5/S6).

Runs INSIDE the container (via the amplifier tool-venv python, which has pyyaml).
This is the single arm-parameterization primitive the matrix session drives:
given {provider-id, model, effort}, it forces that provider to priority 0 so the
root session-under-test uses THIS cell's model/effort.

It ALSO exposes the one knob S5-CRAC needs: --max-tokens, which patches the
loop-streaming orchestrator's context-window budget in the cached anchors-amp-dev
bundle.md. Lowering it makes `auto_compact` (compact_threshold 0.8) fire after a
few substantial turns instead of the default 240k-token (0.8 * 300000) budget --
i.e. it lets a bounded 15-25 turn scenario reliably cross >=2 compaction
boundaries at a fraction of the cost. It changes WHEN compaction fires, not the
mechanism being tested (constraint retention ACROSS a compaction).

Usage (inside container):
  PY=/root/.local/share/uv/tools/amplifier/bin/python
  $PY configure_cell.py --provider-id sonnet --model claude-sonnet-5 --effort xhigh
  $PY configure_cell.py --provider-id sonnet --model claude-sonnet-5 --effort xhigh --max-tokens 45000

Prints a single PRIMARY_OK / MAXTOK_OK verification line the caller greps.
"""

from __future__ import annotations

import argparse
import glob
import re
import sys

import yaml

SETTINGS = "/root/.amplifier/settings.yaml"


def find_bundle_md() -> str:
    """g7h3 FIX: return the bundle.md that actually CARRIES `max_tokens:`.

    Upstream `anchors-amp-dev/bundle.md` was refactored into a pure include of
    `anchors` ("this order reproduces the previously shipped mount plan
    byte-for-byte ... the DRY change moves no wire bytes"), so the
    `context.config.max_tokens` line now lives in `bundles/anchors/bundle.md`.
    The original function hardcoded the anchors-amp-dev path, found a file with
    no `max_tokens:` line, and exited 5 -- which scripted_driver.py swallows.

    Order is deliberate: anchors-amp-dev FIRST (so a container that still
    carries the value there behaves exactly as before), anchors as the
    fallback. Selection is by CONTENT -- a candidate is only accepted if it
    actually contains the line the caller is about to patch -- so this can
    never silently pick a file the patch will not apply to.
    """
    candidates = []
    for root in glob.glob("/root/.amplifier/cache/amplifier-foundation-*"):
        if "skills" in root or "chatgpt" in root:
            continue
        candidates.append(f"{root}/bundles/anchors-amp-dev/bundle.md")
        candidates.append(f"{root}/bundles/anchors/bundle.md")
    for p in candidates:
        try:
            raw = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"^\s*max_tokens:\s*\d+\s*$", raw, flags=re.MULTILINE):
            return p
    return ""


def set_primary(provider_id: str, model: str, effort: str) -> str:
    d = yaml.safe_load(open(SETTINGS))
    provs = d.get("config", {}).get("providers", [])
    target = next((p for p in provs if p.get("id") == provider_id), None)
    if target is None:
        print(
            f"FAIL: provider id {provider_id!r} not found in settings", file=sys.stderr
        )
        sys.exit(3)
    for p in provs:  # demote current primary
        c = p.get("config", {})
        if str(c.get("priority")) == "0" and p.get("id") != provider_id:
            c["priority"] = 9
    tc = target.setdefault("config", {})
    tc["default_model"] = model
    tc["reasoning_effort"] = effort
    tc["priority"] = 0
    yaml.safe_dump(d, open(SETTINGS, "w"), sort_keys=False)
    return f"id={provider_id} model={model} effort={effort} priority=0"


def find_context_simple() -> str:
    for p in glob.glob(
        "/root/.amplifier/cache/amplifier-module-context-simple-*/"
        "amplifier_module_context_simple/__init__.py"
    ):
        return p
    return ""


CAP_LINE = "        budget = min(budget, self.max_tokens)  # S5-CRAC harness: cap budget at configured max_tokens"


def patch_max_tokens(new_max: int) -> str:
    """Two coordinated edits so compaction fires at the configured max_tokens:

    1. bundle.md context.config max_tokens -> new_max (sets self.max_tokens).
    2. context-simple _calculate_budget result is CAPPED at self.max_tokens.
       Without (2), the loop always passes the provider, and _calculate_budget
       returns the model's context_window (200k, or 1M with enable_1m_context),
       so the configured max_tokens is dead and compaction never fires in a
       bounded run. Capping is provider-agnostic (works for openai + anthropic
       arms alike) and is the sanctioned S5 tuning knob. Idempotent.
    """
    out = []
    # ---- 1. bundle.md value ----
    bundle = find_bundle_md()
    if not bundle:
        print(
            "FAIL: bundle.md not found for max_tokens patch (run a warm-up first)",
            file=sys.stderr,
        )
        sys.exit(4)
    raw = open(bundle, encoding="utf-8").read()
    m = re.search(r"^(\s*)max_tokens:\s*\d+\s*$", raw, flags=re.MULTILINE)
    if not m:
        print("FAIL: 'max_tokens:' line not found in context config", file=sys.stderr)
        sys.exit(5)
    indent = m.group(1)
    raw2 = re.sub(
        r"^(\s*)max_tokens:\s*\d+\s*$",
        f"{indent}max_tokens: {new_max}",
        raw,
        count=1,
        flags=re.MULTILINE,
    )
    open(bundle, "w", encoding="utf-8").write(raw2)
    check = re.search(r"^\s*max_tokens:\s*(\d+)\s*$", raw2, flags=re.MULTILINE)
    out.append(f"max_tokens={check.group(1) if check else '??'}")

    # ---- 2. context-simple budget cap ----
    cs = find_context_simple()
    if not cs:
        print(
            "FAIL: context-simple __init__.py not found in cache (run a warm-up first)",
            file=sys.stderr,
        )
        sys.exit(6)
    src = open(cs, encoding="utf-8").read()
    if "S5-CRAC harness: cap budget" in src:
        out.append(f"budget_cap=already cs={cs}")
    else:
        anchor = "        budget = self._calculate_budget(token_budget, provider)\n"
        if anchor not in src:
            print(
                "FAIL: budget-calc anchor not found in context-simple", file=sys.stderr
            )
            sys.exit(7)
        src2 = src.replace(anchor, anchor + CAP_LINE + "\n", 1)
        open(cs, "w", encoding="utf-8").write(src2)
        # drop compiled bytecode so the next fresh `amplifier run` process re-imports source
        import pathlib

        for pyc in pathlib.Path(cs).parent.glob("__pycache__/*context*"):
            try:
                pyc.unlink()
            except OSError:
                pass
        out.append(f"budget_cap=inserted cs={cs}")
    return " ".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider-id")
    ap.add_argument("--model")
    ap.add_argument("--effort")
    ap.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="patch loop-streaming orchestrator max_tokens (forces earlier compaction)",
    )
    args = ap.parse_args()

    parts = []
    if args.provider_id:
        if not (args.model and args.effort):
            print("FAIL: --provider-id requires --model and --effort", file=sys.stderr)
            return 2
        parts.append(
            "PRIMARY_OK " + set_primary(args.provider_id, args.model, args.effort)
        )
    if args.max_tokens is not None:
        parts.append("MAXTOK_OK " + patch_max_tokens(args.max_tokens))
    if not parts:
        print(
            "FAIL: nothing to do (pass --provider-id ... and/or --max-tokens)",
            file=sys.stderr,
        )
        return 2
    print(" | ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
