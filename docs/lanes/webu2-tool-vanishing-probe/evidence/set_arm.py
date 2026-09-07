#!/usr/bin/env python3
"""2gxp -- set the arm INSIDE the container by rewriting tool_search on every
provider-openai block of /root/.amplifier/settings.yaml.

The same rewrite path runs for EVERY arm including the control, so the three arms
differ only in the tool_search key and never in how the file was produced.
The arm is still PROVEN per run on that run's own captured wire (PREREG V3);
this script's output is a convenience check, never the evidence.
"""
import sys, pathlib, yaml

ALWAYS = {"a": ["bash", "todo"], "b": ["bash", "todo", "write_file", "edit_file", "delegate"]}
arm = sys.argv[1]
assert arm in ("a", "b", "c"), arm
p = pathlib.Path("/root/.amplifier/settings.yaml")
d = yaml.safe_load(p.read_text())
n = 0
for prov in d["config"]["providers"]:
    if prov.get("module") != "provider-openai":
        continue
    cfg = prov.setdefault("config", {})
    if arm == "c":
        cfg.pop("tool_search", None)
    else:
        cfg["tool_search"] = {"mode": "namespaced", "always_loaded": list(ALWAYS[arm])}
    n += 1
p.write_text(yaml.safe_dump(d, sort_keys=True))
txt = p.read_text()
print(f"ARM_SET arm={arm} openai_blocks={n} tool_search_keys={txt.count('tool_search:')} "
      f"always_loaded_lines={txt.count('always_loaded:')}")
