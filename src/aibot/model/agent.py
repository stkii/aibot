from dataclasses import dataclass
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class AgentParams:
    name: str
    instructions: str
    model: str
    tools: list[str] | None = None


class Intent(str, Enum):
    CODE = "code"
    GENERAL = "general"


@dataclass
class AgentsResult:
    output_text: str | None = None
    intent: Intent | None = None
    metadata: dict[str, Any] | None = None
