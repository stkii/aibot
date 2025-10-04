from __future__ import annotations

from pathlib import Path

import yaml
from agents import Agent

from src.aibot.logger import logger

from .instruction import InstructionService


def _load_agents_config() -> dict:
    """Load resources/agents.yml configuration."""
    curr = Path(__file__).resolve()
    cfg_path: Path | None = None
    for parent in curr.parents:
        if (parent / "pyproject.toml").exists():
            candidate = parent / "resources" / "agents.yml"
            if candidate.exists():
                cfg_path = candidate
            break

    if cfg_path is None:
        logger.warning("resources/agents.yml not found")
        return {}

    with cfg_path.open("r", encoding="utf-8") as f:
        try:
            return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            logger.warning("failed to parse %s: %s", cfg_path, e)
            return {}


def get_all_agents() -> list[Agent]:
    """Get all agents defined in YAML."""
    config = _load_agents_config()
    agents_config = config.get("agents", {})

    agents = []
    for agent_key, agent_data in agents_config.items():
        instruction = agent_data.get("instruction")

        # For backward compatibility
        if not instruction:
            instruction_service = InstructionService.get_instance()
            instruction = instruction_service.load_static_instruction("default")

        agent = Agent(
            name=agent_key,
            instructions=instruction,
            model=agent_data.get("model"),
            tools=agent_data.get("tools", []) or None,
        )
        agents.append(agent)

    return agents
