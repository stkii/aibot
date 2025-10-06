from __future__ import annotations

from agents import Agent, Runner

from src.aibot.service.agents import get_all_agents


async def generate_agents_response(user_msg: str) -> dict:
    """Generate response using configured agents and return text + meta.

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

    # Build a triage agent that can handoff to all configured agents
    triage_agent = Agent(
        name="triage",
        instructions=(
            "Handoff to the most appropriate sub-agent based on the user's "
            "language, intent, and request content."
        ),
        handoffs=agents,
    )

    result = await Runner.run(triage_agent, input=user_msg)

    # Extract text output with compatibility for different result shapes
    text = getattr(result, "final_output", None) or getattr(result, "text", None) or ""

    # Best-effort meta extraction; attributes may not exist depending on SDK
    agent_key = (
        getattr(result, "selected_agent", None)
        or getattr(result, "agent_key", None)
        or getattr(result, "agent_name", None)
        or getattr(getattr(result, "agent", None), "name", None)
    ) or None
    model = getattr(result, "model", None)
    usage = getattr(result, "usage", None)
    tool_calls = getattr(result, "tool_calls", None)
    handoffs = getattr(result, "handoffs", None)

    return {
        "text": text,
        "meta": {
            "agent_key": agent_key,
            "model": model,
            "usage": usage,
            "tool_calls": tool_calls,
            "handoffs": handoffs,
        },
    }
