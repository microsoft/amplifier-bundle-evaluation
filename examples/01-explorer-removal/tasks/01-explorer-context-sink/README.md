# Task: 01-explorer-context-sink

A real code-exploration task used to measure what the `foundation:explorer`
agent contributes.

## Prompt

> Explore /workspace/agent-framework. Explain how it handles switching between
> AI providers (e.g. OpenAI vs Anthropic). Include code references in file:line
> form as evidence for each claim.

## Environment

`profile.yaml` provisions Ubuntu + uv, clones `microsoft/agent-framework` into
`/workspace/agent-framework`, and redirects `amplifier-foundation` clones to a
Gitea mirror repo chosen per trial via the `FOUNDATION_REPO` launch variable:

- `amplifier-foundation-with-explorer` -- foundation as-is (explorer present)
- `amplifier-foundation-without-explorer` -- explorer agent and all its
  delegation-guidance references removed

Both mirror repos hold their state on `main`, so the agent's `bundle add @main`
resolves correctly. The harness (`../../harness.py`) supplies the variable.

## Grading

`grader.yaml` scores ANSWER QUALITY only (provider abstraction identified,
switching mechanism explained, citations valid). The context-sink effect --
root-context tokens, delegations, citation counts -- is measured separately by
`../../compare.py`, not by the grader.
