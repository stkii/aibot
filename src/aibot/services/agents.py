"""Agent loading and execution via the OpenAI Agents SDK.

Loads the agent roster from `resources/agents.yml`, exposes every non-base
agent to the base persona as a specialist tool, and runs the conversation
through `Runner.run`.
"""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import yaml
from agents import Agent, Runner, SessionSettings, SQLiteSession

from src.aibot.logger import logger

if TYPE_CHECKING:
    from agents.items import TResponseInputItem

BASE_AGENT_NAME = "general"

# Conversation memory lives in its own SQLite file, next to aibot.db.
_SESSIONS_DB_PATH = "agent_sessions.db"
_FALLBACK_HISTORY_MAX_ITEMS = 40


def _history_max_items() -> int:
    """Per-request history budget from TALK_HISTORY_MAX_ITEMS (falls back to 40)."""
    raw = os.getenv("TALK_HISTORY_MAX_ITEMS")
    if raw is None:
        return _FALLBACK_HISTORY_MAX_ITEMS
    try:
        return max(1, int(raw))
    except ValueError:
        return _FALLBACK_HISTORY_MAX_ITEMS


def _is_user_message(item: object) -> bool:
    return isinstance(item, dict) and item.get("role") == "user"


class BoundedSession(SQLiteSession):
    """A SQLiteSession whose trimmed history always starts at a user message.

    Limiting to the latest N items can cut a tool call away from its output,
    and the model API rejects such orphans, so anything before the first user
    message is dropped as well.
    """

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        """Return the latest items, trimmed to start at a user message."""
        items = await super().get_items(limit)
        for index, item in enumerate(items):
            if _is_user_message(item):
                return items[index:]
        return []


def build_conversation_session(session_id: str) -> SQLiteSession:
    """Create the bounded persistent memory for a continuing conversation."""
    return BoundedSession(
        session_id,
        db_path=_SESSIONS_DB_PATH,
        session_settings=SessionSettings(limit=_history_max_items()),
    )


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

        agent = Agent(
            name=agent_key,
            instructions=instruction,
            model=agent_data.get("model"),
            # Ensure tools is always a list as required by agents.Agent
            tools=agent_data.get("tools") or [],
        )
        agents.append(agent)

    return agents


def _extract_text(result: object) -> str:
    """Extract plain text from an Agents SDK run result."""
    return str(getattr(result, "final_output", None) or getattr(result, "text", None) or "")


def _extract_usage(result: object) -> dict[str, Any] | None:
    usage = getattr(result, "usage", None)
    if usage is None:
        context_wrapper = getattr(result, "context_wrapper", None)
        usage = getattr(context_wrapper, "usage", None)

    if usage is None:
        return None

    if isinstance(usage, dict):
        return {
            "requests": usage.get("requests", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    return {
        "requests": getattr(usage, "requests", 0),
        "input_tokens": getattr(usage, "input_tokens", 0),
        "output_tokens": getattr(usage, "output_tokens", 0),
        "total_tokens": getattr(usage, "total_tokens", 0),
    }


def _build_base_instructions(
    base_instructions: str | None,
    *,
    has_specialist_tools: bool,
) -> str:
    tool_guidance = dedent(
        """
        ## Specialist Tool Usage
        - You are the base persona, and you must always produce the final user-facing answer.
        - Use specialist agent tools only when their analysis is clearly useful for the request.
        - Do not use tools for casual conversation, simple questions, or tasks you can handle well.
        - Treat tool output as source material; integrate it naturally instead of pasting it as-is.
        - Do not mention internal tool names or tool-calling steps unless that detail is needed.
        """,
    ).rstrip()
    if has_specialist_tools:
        return f"{base_instructions or ''}{tool_guidance}"
    return base_instructions or ""


def _build_tool_description(agent: Agent[Any]) -> str:
    return dedent(
        f"""
        Use this specialist agent when the user request is best handled by {agent.name}.
        Return analysis or draft content for the base persona to use in its final answer.
        """,
    ).strip()


def _extract_tool_calls(result: object) -> list[dict[str, str]]:
    tool_calls = []
    for item in getattr(result, "new_items", []):
        if getattr(item, "type", None) != "tool_call_item":
            continue

        tool_name = getattr(item, "tool_name", None)
        if tool_name:
            tool_calls.append({"tool_name": str(tool_name)})
    return tool_calls


async def generate_agents_response(user_msg: str, *, session_id: str | None = None) -> dict:
    """Generate response using configured agents and return text + meta.

    When `session_id` is given, the run reads and extends that conversation's
    persistent memory (bounded to the latest N items); otherwise it is
    a stateless single-turn run.

    Returns
    -------
    dict
        { "text": str, "meta": { "agent_key": str|None, "model": str|None,
          "usage": dict|None, "tool_calls": list|None, "handoffs": list|None } }

    """
    agents = get_all_agents()

    if not agents:
        return {
            "text": "エージェントが設定されていません。resources/agents.yml を確認してください。",
            "meta": {
                "agent_key": None,
                "model": None,
                "usage": None,
                "tool_calls": None,
                "handoffs": None,
            },
        }

    base_agent = next((agent for agent in agents if agent.name == BASE_AGENT_NAME), agents[0])
    specialist_agents = [agent for agent in agents if agent.name != base_agent.name]

    specialist_tools = [
        agent.as_tool(
            tool_name=f"{agent.name}_agent",
            tool_description=_build_tool_description(agent),
        )
        for agent in specialist_agents
    ]
    base_instructions = (
        base_agent.instructions if isinstance(base_agent.instructions, str) else None
    )
    base_agent_with_tools = base_agent.clone(
        instructions=_build_base_instructions(
            base_instructions,
            has_specialist_tools=bool(specialist_tools),
        ),
        tools=[*base_agent.tools, *specialist_tools],
    )

    memory = build_conversation_session(session_id) if session_id else None
    final_result = await Runner.run(base_agent_with_tools, input=user_msg, session=memory)
    text = _extract_text(final_result)
    tool_calls = _extract_tool_calls(final_result)

    return {
        "text": text,
        "meta": {
            "agent_key": base_agent.name,
            "specialist_agent_key": ", ".join(call["tool_name"] for call in tool_calls) or None,
            "model": str(base_agent.model) if base_agent.model is not None else None,
            "usage": _extract_usage(final_result),
            "tool_calls": tool_calls,
            "handoffs": [
                {
                    "from": base_agent.name,
                    "to": call["tool_name"],
                    "via": "tool",
                }
                for call in tool_calls
            ],
        },
    }
