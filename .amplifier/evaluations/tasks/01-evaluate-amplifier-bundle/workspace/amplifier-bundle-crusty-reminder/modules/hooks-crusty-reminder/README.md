# hooks-crusty-reminder

Hook module that injects a system reminder on every LLM step within a turn,
telling the agent: if it implemented anything this turn, it should consult the
`crusty-old-engineer` skill at the end of the turn for review and next steps.

The hook registers on `provider:request` and emits `inject_context` with the
reminder as an ephemeral user message. No configuration.

The reminder names a skill (`crusty-old-engineer`) that lives in
`amplifier-bundle-skills`. Compose the two bundles together.
