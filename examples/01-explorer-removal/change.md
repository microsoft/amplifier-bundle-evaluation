# Change: Remove foundation:explorer agent

## Summary

Cleanly remove the `foundation:explorer` agent from `amplifier-foundation`. The agent file is deleted, and every line that names it in the active delegation guidance is deleted entirely. No substitute agent is named in its place.

The goal is to evaluate the impact of removing foundation explorer on quality, tokens used and time.


## Edits applied (deletions only, no substitutions)

```
agents/explorer.md
   deleted

bundle.md
   line "    - foundation:explorer" deleted from the agents.include list

context/agents/delegation-instructions.md
context/agents/multi-agent-patterns.md
   every line containing the string "foundation:explorer" is deleted

   This includes:
     - rows in the "Delegate To" tables that named explorer
     - "Immediate Delegation Triggers" rows that named explorer
     - example delegate(agent="foundation:explorer", ...) snippets
     - parallel-dispatch examples that listed explorer
```

The implementation is `sed -i '/foundation:explorer/d' <files>`, a strictly destructive line-deletion. Any text that mentioned the agent's name is gone; no other agent's name is inserted to take its place.
