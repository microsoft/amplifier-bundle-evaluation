#!/usr/bin/env python3
"""njpd -- FAN-OUT WIDTH per delegation (PRE-REGISTERED SECONDARY, never gating).

8rugb's real finding was not that the split suppresses delegation -- both arms
delegated on 13 of 14 runs, same turn, same agent -- but that it narrows the
WIDTH of the fan-out: arm A spawned two parallel explorers for one survey where
arm B spawned one.

`root_delegate_calls` (the gating metric) cannot see that: it is a flat count of
`delegate:agent_spawned` events in the root session. This groups those same
events two ways, both mechanical, both reported, neither used in the verdict:

  fanout_per_turn -- spawns grouped by the root TURN they occur in; a turn
                     boundary is a `prompt:complete` event in the root session.
                     Reported only for turns with >=1 spawn. This is the
                     definition that matches 8rugb's observation.
  fanout_burst    -- spawns grouped into bursts by timestamp; a new burst starts
                     when the gap from the previous spawn exceeds BURST_GAP_S.
                     Proxy for "dispatched in the same parallel tool-call batch",
                     which turn-grouping cannot separate from two sequential
                     delegations inside one turn.

Usage: fanout.py <run-outdir> <root_sid>   -> writes <outdir>/fanout.json
"""
import datetime, glob, json, os, sys

BURST_GAP_S = 5.0

def parse_ts(ts):
    try:
        return datetime.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None

def root_events_path(all_sessions_dir, root_sid):
    for ev in glob.glob(os.path.join(all_sessions_dir, "**", "sessions", "*", "events.jsonl"), recursive=True):
        if "/context-intelligence/" in ev:
            continue
        if ev.split("/sessions/")[1].split("/")[0] == root_sid:
            return ev
    return None

def main():
    outdir = sys.argv[1]
    root_sid = sys.argv[2] if len(sys.argv) > 2 else ""
    path = root_events_path(os.path.join(outdir, "all-sessions"), root_sid) if root_sid else None
    rec = {"root_sid": root_sid, "measurable": False, "spawns_total": 0, "turns_total": 0,
           "delegating_turns": 0, "fanout_per_turn": [], "fanout_burst": [],
           "fanout_per_turn_max": None, "fanout_per_turn_mean": None,
           "fanout_burst_max": None, "fanout_burst_mean": None, "agents_by_turn": []}
    if path and os.path.exists(path):
        rec["measurable"] = True
        turn = 0; per_turn = {}; agents_turn = {}; spawn_ts = []
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"delegate:agent_spawned"' not in line and '"prompt:complete"' not in line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ev = e.get("event")
                if ev == "delegate:agent_spawned":
                    per_turn[turn] = per_turn.get(turn, 0) + 1
                    agents_turn.setdefault(turn, []).append((e.get("data") or {}).get("agent"))
                    t = parse_ts(e.get("ts"))
                    if t: spawn_ts.append(t)
                elif ev == "prompt:complete":
                    turn += 1
        rec["turns_total"] = turn
        widths = [per_turn[k] for k in sorted(per_turn) if per_turn[k] > 0]
        rec["spawns_total"] = sum(widths); rec["delegating_turns"] = len(widths)
        rec["fanout_per_turn"] = widths
        rec["agents_by_turn"] = [{"turn": k, "width": per_turn[k], "agents": agents_turn.get(k, [])}
                                 for k in sorted(per_turn) if per_turn[k] > 0]
        if widths:
            rec["fanout_per_turn_max"] = max(widths)
            rec["fanout_per_turn_mean"] = round(sum(widths)/len(widths), 3)
        spawn_ts.sort(); bursts = []
        for t in spawn_ts:
            if bursts and (t - bursts[-1][-1]).total_seconds() <= BURST_GAP_S:
                bursts[-1].append(t)
            else:
                bursts.append([t])
        bw = [len(b) for b in bursts]
        rec["fanout_burst"] = bw
        if bw:
            rec["fanout_burst_max"] = max(bw); rec["fanout_burst_mean"] = round(sum(bw)/len(bw), 3)
    with open(os.path.join(outdir, "fanout.json"), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    print(json.dumps({k: rec[k] for k in ("measurable","spawns_total","delegating_turns","fanout_per_turn","fanout_burst")}))

if __name__ == "__main__":
    main()
