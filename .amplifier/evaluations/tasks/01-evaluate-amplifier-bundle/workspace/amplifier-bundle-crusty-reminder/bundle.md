---
bundle:
  name: crusty-reminder
  version: 0.1.0
  description: Foundation plus a hook that reminds the agent to consult crusty-old-engineer after implementation work

# This bundle is a thin wrapper over foundation that adds one hook.
# Installing it as the `--app` bundle gives the agent everything
# foundation provides (skills, tools, agents, etc.) plus the
# crusty-reminder hook.
#
# Foundation already includes amplifier-bundle-skills (which ships the
# crusty-old-engineer skill the hook will reference), so we do not
# include it separately.
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-crusty-reminder@main#subdirectory=behaviors/crusty-reminder.yaml
---

# Crusty Reminder Bundle

A foundation-derived bundle that adds one hook: a system reminder
injected before each LLM call telling the agent that if it implemented
anything this turn, it should consult the `crusty-old-engineer` skill
at the end of the turn for review and concrete next steps.

This bundle exists as the artifact-under-test for evaluation example 02.
It is intentionally minimal: one behavior file, one hook, no
configuration knobs.

The hook fires on `provider:request`, the same event used by
`hooks-todo-reminder`.
