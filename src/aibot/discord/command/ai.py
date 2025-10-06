from __future__ import annotations

import time
import uuid

from discord import Interaction, app_commands

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorator.usage import has_daily_usage_left
from src.aibot.infrastructure.api.agents import generate_agents_response
from src.aibot.infrastructure.dao.agent import AgentDAO
from src.aibot.logger import logger

client = BotClient.get_instance()


def _build_session_id(interaction: Interaction) -> str:
    guild_id = interaction.guild.id if interaction.guild else 0
    ch = interaction.channel
    if ch is None:
        return f"guild:{guild_id}:channel:0:thread:0"
    parent = getattr(ch, "parent", None)
    channel_id = getattr(parent, "id", None) or getattr(ch, "id", 0)
    thread_id = ch.id if parent is not None else 0
    return f"guild:{guild_id}:channel:{channel_id}:thread:{thread_id or 0}"


@client.tree.command(
    name="ai",
    description="AIと対話します",
)
@has_daily_usage_left()
@app_commands.rename(user_msg="message")
async def ai_command(interaction: Interaction, user_msg: str) -> None:
    try:
        run_id = str(uuid.uuid4())
        session_id = _build_session_id(interaction)
        t0 = time.perf_counter()

        await interaction.response.defer()

        res = await generate_agents_response(user_msg)
        text = res.get("text", "")
        meta = res.get("meta", {})

        await interaction.followup.send(text)

        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Normalize usage to a dict if possible
        usage_val = (meta or {}).get("usage") if isinstance(meta, dict) else None
        if not isinstance(usage_val, dict):
            usage_val = None

        agent_dao = AgentDAO()
        await agent_dao.record_success(
            run_id=run_id,
            session_id=session_id,
            intent="ai",
            agent_key=(meta or {}).get("agent_key") or "unknown",
            model=(meta or {}).get("model"),
            usage=usage_val,
            latency_ms=latency_ms,
            tool_calls=(meta or {}).get("tool_calls"),
            handoffs=(meta or {}).get("handoffs"),
            output_preview=text,
        )
    except Exception as e:
        logger.exception("Error in /ai command: %s", e)
        try:
            # Attempt to record failure metadata
            latency_ms = int(
                (time.perf_counter() - locals().get("t0", time.perf_counter())) * 1000,
            )
            run_id = locals().get("run_id", str(uuid.uuid4()))
            session_id = locals().get("session_id", _build_session_id(interaction))
            agent_dao = AgentDAO()
            await agent_dao.record_error(
                run_id=run_id,
                session_id=session_id,
                intent="ai",
                agent_key=None,
                model=None,
                latency_ms=latency_ms,
                error=f"{type(e).__name__}: {e}",
            )
        except Exception:
            # Swallow DAO errors to avoid masking original error handling
            logger.debug("Failed to record /ai error to AgentDAO")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "`/ai` コマンドの実行中にエラーが発生しました。",
                ephemeral=True,
            )
