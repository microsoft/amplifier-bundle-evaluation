#!/usr/bin/env python3
"""8rugb per-run summary. Applies the PRE-REGISTERED validity gate and reads the
S3 grader's own pass rule + dw_measure's own root_delegate_calls. Nothing is
recomputed or reinterpreted here."""
import json, sys
from pathlib import Path

out = Path(sys.argv[1]); runid, arm, prov = sys.argv[2], sys.argv[3], sys.argv[4]

def load(p):
    try: return json.loads((out / p).read_text())
    except Exception: return None


def continuity_from_transcript(out: Path, drv) -> bool:
    """Continuity = every session id the CLI actually printed is the SAME id.

    A turn whose stdout capture came back EMPTY (out_len == 0) prints nothing and is
    not evidence of a break -- the container still recorded the turn (see the
    root_prompt_completes == 5 gate, which is checked separately and is the real proof).
    `amplifier run --resume` prints "Resuming session: <sid>", not "Session ID: <sid>",
    which is why the shared driver's own flag is never true for any arm.
    """
    import re
    sids = []
    for n in range(1, 6):
        f = out / f"turn{n}.out"
        if not f.exists():
            return False
        t = f.read_text(errors="replace")
        if not t.strip():
            continue  # empty capture -- transport artifact, counted in turn_captures_empty
        m = re.search(r"Session ID:\s*([0-9a-f-]{8,})", t) or re.search(r"Resuming session:\s*([0-9a-f-]{8,})", t)
        if m:
            sids.append(m.group(1))
    return len(sids) >= 1 and len(set(sids)) == 1


def root_prompt_completes(out: Path, root_sid) -> int:
    if not root_sid: return -1
    for ev in (out / "all-sessions").rglob("events.jsonl"):
        if "/context-intelligence/" in str(ev): continue
        if f"/{root_sid}/" not in str(ev) + "/": continue
        n = 0
        with open(ev, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"prompt:complete"' in line: n += 1
        return n
    return -1

drv, sc, ms = load("driver_record.json"), load("scorecard.json"), load("measure.json")
reasons = []
turns_done = sum(1 for t in (drv or {}).get("turns", []) if t.get("done"))
if not drv: reasons.append("no driver_record (turn loop never returned)")
else:
    if turns_done != 5: reasons.append(f"turns_done={turns_done} (need 5)")
    if any(t.get("marker") == "TIMEOUT" for t in drv.get("turns", [])): reasons.append("a turn hit TIMEOUT")
    # NOTE (deviation, decided before any score was read): the shared driver's own
    # session_continuity_ok is a FALSE NEGATIVE BY CONSTRUCTION -- it re-greps every turn's
    # stdout for "Session ID: <sid>", but `amplifier run --resume` prints
    # "Resuming session: <sid>" instead, so turns 2-5 never match and the flag is never true
    # for ANY run of ANY arm. Continuity is therefore read from the evidence that actually
    # carries it: turn 1's printed session id, each later turn's printed resume target, and
    # the root session file's own prompt:complete count.
    if not continuity_from_transcript(out, drv): reasons.append("session continuity broken (transcript ids disagree)")
    if root_prompt_completes(out, (drv or {}).get("root_session_id")) != 5:
        reasons.append("root session does not carry 5 prompt:complete events")
if not sc or "total" not in (sc or {}): reasons.append("no gradeable scorecard")
if not ms or not ms.get("tree_sessions"): reasons.append("no measurable session tree")

rec = {
    "run": runid, "arm": arm, "provider": prov,
    "valid": not reasons, "invalid_reasons": reasons,
    "turns_done": turns_done,
    "continuity_ok": continuity_from_transcript(out, drv),
    "driver_flag_session_continuity_ok": (drv or {}).get("session_continuity_ok"),
    "root_prompt_completes": root_prompt_completes(out, (drv or {}).get("root_session_id")),
    "turn_captures_empty": sum(1 for t in (drv or {}).get("turns", []) if t.get("out_len") == 0),
    "score_total": (sc or {}).get("total"),
    "pass": (sc or {}).get("pass"),
    "dims": (sc or {}).get("dimensions"),
    "delegate_calls": (ms or {}).get("root_delegate_calls"),
    "sub_agents_total": (ms or {}).get("sub_agents_total"),
    "sub_agent_hist": (ms or {}).get("sub_agent_hist"),
    "cost_usd": (ms or {}).get("cost_usd"),
    "llm_calls": (ms or {}).get("llm_calls"),
    "root_llm_calls": (ms or {}).get("root_llm_calls"),
    "models": (ms or {}).get("models"),
    "wall_s": (drv or {}).get("wall_s"),
    "root_sid": (ms or {}).get("root_sid"),
}
(out / "summary.json").write_text(json.dumps(rec, indent=2))
print(json.dumps({k: rec[k] for k in
      ("run","arm","provider","valid","score_total","pass","delegate_calls","cost_usd","wall_s")}))
if reasons: print("INVALID:", "; ".join(reasons))
