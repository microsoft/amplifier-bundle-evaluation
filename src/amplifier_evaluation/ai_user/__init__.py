"""AI User: drives an agent inside a Digital Twin Universe like a real user would."""

from amplifier_evaluation.ai_user.ai_user import (
    DEFAULT_PERSONA,
    SYSTEM_INSTRUCTION,
    AIUser,
    InteractionResult,
)
from amplifier_evaluation.ai_user.tools import ConcludeResult, ConcludeTool

__all__ = [
    "AIUser",
    "ConcludeResult",
    "ConcludeTool",
    "DEFAULT_PERSONA",
    "InteractionResult",
    "SYSTEM_INSTRUCTION",
]
