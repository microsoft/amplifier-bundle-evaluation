"""AIUser: an Amplifier Foundation session that drives an agent in a Digital Twin Universe.

The AI User is a Foundation session with three layers of instruction:

- SYSTEM_INSTRUCTION (fixed): operational rules. How to use bash to drive
  the agent via `amplifier-digital-twin exec`, when to conclude.
- Persona (per-run): who you are roleplaying. Plain string.
- Scenario (per-run): what you are trying to accomplish. Plain string.
- Invocation guide (per-run): how the agent's CLI works, assumed to be
  running inside the Digital Twin Universe. Plain markdown string.

Foundation already provides `bash`, `filesystem`, `web`, and other tools.
The AI User uses bash to wrap each agent invocation with the Digital Twin
Universe exec command. There is no Python transport layer; the LLM drives
the agent directly through tool calls, guided by the invocation guide.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from amplifier_foundation import Bundle, load_bundle

from amplifier_evaluation.ai_user.tools import ConcludeResult, ConcludeTool


# Canonical bundle sources. Plain strings so the constructor can accept either
# a git URL (default, no local checkout required) or a local path override.
DEFAULT_FOUNDATION_SOURCE = "git+https://github.com/microsoft/amplifier-foundation@main"
DEFAULT_PROVIDER_SOURCE = (
    "git+https://github.com/microsoft/amplifier-foundation@main"
    "#subdirectory=providers/anthropic-sonnet.yaml"
)


SYSTEM_INSTRUCTION = """\
You are an "AI User" that tests AI agents by interacting with them the way a
real person would.

You have a `bash` tool. The agent you are testing is running inside a Digital
Twin Universe container. You will receive its id (like `dtu-abc12345`).

To run a command inside the Digital Twin Universe, prefix it with the exec
wrapper:

    amplifier-digital-twin exec <dtu_id> -- <command>

For commands with tricky quoting or multi-line input, write your message to
a host file first and push it in:

    echo "<message>" > /tmp/msg.txt
    amplifier-digital-twin file-push <dtu_id> /tmp/msg.txt /tmp/msg.txt
    amplifier-digital-twin exec <dtu_id> -- bash -c 'cmd --input "$(cat /tmp/msg.txt)"'

You will also receive:

- A persona describing who you are.
- A scenario describing what you want to do.
- An invocation guide describing the agent's CLI: which commands to run,
  what responses look like, what "broken" looks like. The guide assumes
  you are already inside the Digital Twin Universe shell. You wrap each
  command with `amplifier-digital-twin exec ...` to actually run it.

Stay in character as the persona. Use bash to talk to the agent according to
the guide. When the scenario is done or the agent is broken, call `conclude`.

Rules:

- Be concise. Real users do not write essays.
- If a bash command exits non-zero, hangs, or returns garbage, treat that
  as the agent crashing and conclude with verdict=failure.
- Do not invent requirements beyond what the scenario states.
- Stay in role. Talk only to the agent's CLI. Do not poke at workspace
  files, processes, or anything outside the agent's interface.
- After conclude, do not run more bash commands and do not write a long
  final reply.
"""


DEFAULT_PERSONA = (
    "A typical software developer using an AI coding assistant. You are "
    "pragmatic and outcome-oriented: you describe what you want clearly and "
    "judge the result by whether it actually works. You ask follow-up "
    "questions when the agent's response is incomplete, but you do not "
    "nitpick."
)


def _render_opening_prompt(
    persona: str,
    scenario: str,
    dtu_id: str,
    invocation_guide: str,
) -> str:
    return (
        "You are now playing this persona:\n"
        '"""\n'
        f"{persona.strip()}\n"
        '"""\n\n'
        "Scenario:\n"
        '"""\n'
        f"{scenario.strip()}\n"
        '"""\n\n'
        f"The agent you are testing is running inside Digital Twin Universe "
        f"`{dtu_id}`.\n\n"
        "How to talk to it (its CLI behavior, assuming you are inside the\n"
        "Digital Twin Universe shell):\n"
        '"""\n'
        f"{invocation_guide.strip()}\n"
        '"""\n\n'
        "Use bash to drive the agent. Call `conclude` when done."
    )


@dataclass
class InteractionResult:
    """Outcome of running the AI User against a Digital Twin Universe agent."""

    scenario: str
    persona: str
    dtu_id: str
    conclude: ConcludeResult | None
    """The verdict and summary captured by the conclude tool, or None if
    the AI User never called conclude (e.g. ran out of iterations)."""

    final_assistant_text: str
    ai_user_session_id: str | None
    elapsed_s: float


class AIUser:
    """Compose Amplifier Foundation + system instruction, then run scenarios."""

    def __init__(
        self,
        foundation_source: str = DEFAULT_FOUNDATION_SOURCE,
        provider_source: str = DEFAULT_PROVIDER_SOURCE,
    ) -> None:
        """Construct an AI User.

        Args:
            foundation_source: Source for the foundation bundle. Defaults
                to the canonical git URL so no local checkout is required.
                Accepts any string `load_bundle` understands (git URL or
                local path).
            provider_source: Source for the provider bundle YAML. Defaults
                to the canonical foundation `anthropic-sonnet.yaml`. Same
                URL/path flexibility as `foundation_source`.
        """
        self.foundation_source = foundation_source
        self.provider_source = provider_source
        self._prepared = None

    async def setup(self) -> None:
        """Load + compose + prepare the bundle. Expensive; call once.

        Foundation already provides bash, filesystem, web, search, etc.
        We just compose a small system-instruction bundle on top.
        """
        foundation = await load_bundle(self.foundation_source)
        provider = await load_bundle(self.provider_source)
        system_bundle = Bundle(
            name="ai-user-system",
            version="0.1.0",
            instruction=SYSTEM_INSTRUCTION,
        )
        composed = foundation.compose(provider).compose(system_bundle)
        self._prepared = await composed.prepare()

    async def run(
        self,
        scenario: str,
        dtu_id: str,
        invocation_guide: str,
        persona: str | None = None,
    ) -> InteractionResult:
        """Drive the agent in the Digital Twin Universe through the scenario.

        Args:
            scenario: What the persona is trying to accomplish.
            dtu_id: The Digital Twin Universe instance id (e.g. dtu-abc12345).
            invocation_guide: Markdown text describing the agent's CLI. The
                caller is responsible for sourcing this however they want
                (read from a file, fetched from a database, inlined).
            persona: The character to roleplay, as a plain string. If None,
                DEFAULT_PERSONA is used.
        """
        if self._prepared is None:
            raise RuntimeError("AIUser.setup() must be called before run().")

        if persona is None:
            persona = DEFAULT_PERSONA

        start = time.monotonic()
        conclude_tool = ConcludeTool()

        session_id = f"ai-user-{int(time.time())}"
        session = await self._prepared.create_session(
            session_id=session_id,
            session_cwd=Path.cwd(),
        )
        await session.coordinator.mount("tools", conclude_tool, name=conclude_tool.name)

        opening = _render_opening_prompt(persona, scenario, dtu_id, invocation_guide)

        async with session:
            final_text = await session.execute(opening)

        return InteractionResult(
            scenario=scenario,
            persona=persona,
            dtu_id=dtu_id,
            conclude=conclude_tool.result,
            final_assistant_text=final_text,
            ai_user_session_id=session_id,
            elapsed_s=time.monotonic() - start,
        )
