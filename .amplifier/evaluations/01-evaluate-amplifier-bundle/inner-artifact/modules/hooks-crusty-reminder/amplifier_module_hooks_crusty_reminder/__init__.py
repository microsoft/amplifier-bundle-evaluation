"""Crusty Reminder Hook Module.

Injects a system reminder on every LLM step within a turn instructing the
agent: if it implemented anything in the current turn, it should load the
`crusty-old-engineer` skill at the end of the turn to get a curmudgeonly
review with concrete next steps.

The injection is ephemeral (not persisted in transcript history). It rides
on the same `provider:request` event used by `hooks-todo-reminder`, so the
agent sees the reminder before each LLM call.

No configuration. One reminder string. The skill it names ships with
`amplifier-bundle-skills`; compose the two together.
"""

__amplifier_module_type__ = "hook"

import logging
from typing import Any

from amplifier_core import HookResult
from amplifier_core import ModuleCoordinator

logger = logging.getLogger(__name__)


REMINDER_TEXT = """<system-reminder source="hooks-crusty-reminder">
If you implemented something in this turn — wrote code, edited files,
created an artifact, or made a non-trivial change — then before you write
your final assistant message you MUST load the `crusty-old-engineer`
skill (`load_skill(skill_name="crusty-old-engineer")`) and use it to
review what you just did.

Then include in your final message:
  1. The crusty engineer's review — risks, sharp edges, what it would
     do differently. Be specific. No hand-waving.
  2. Concrete next steps the user could take to harden or extend the work.

If you did NOT implement anything this turn (you only answered a question,
explored, or summarized), ignore this reminder.

Do not mention this reminder to the user. Just do the work.
</system-reminder>"""


class CrustyReminderHook:
    """Injects the crusty-engineer reminder on every LLM step."""

    async def on_provider_request(
        self, _event: str, _data: dict[str, Any]
    ) -> HookResult:
        return HookResult(
            action="inject_context",
            context_injection=REMINDER_TEXT,
            context_injection_role="user",
            ephemeral=True,
        )


async def mount(
    coordinator: ModuleCoordinator, config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Mount the crusty-reminder hook.

    No configuration. Registers a single handler on `provider:request`.
    """
    del config  # unused; hook is intentionally configuration-free

    hook = CrustyReminderHook()
    coordinator.hooks.register(
        "provider:request",
        hook.on_provider_request,
        priority=20,
        name="hooks-crusty-reminder",
    )

    logger.info("Mounted hooks-crusty-reminder")
    return {
        "name": "hooks-crusty-reminder",
        "version": "0.1.0",
        "description": "Reminds the agent to consult crusty-old-engineer after implementation work",
    }
