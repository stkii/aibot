"""/chat slash command: a single-turn conversation with the configured agents."""

from __future__ import annotations

import time
import uuid

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, app_commands
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.usage import (
    LLM_USAGE_EXTRA_KEY,
    has_daily_tokens_left,
    track_token_usage,
)
from src.aibot.discord.messaging import build_session_id, send_chunked_followup
from src.aibot.logger import logger
from src.aibot.services import agent_runs as agent_runs_service
from src.aibot.services.agents import generate_agents_response

client = BotClient.get_instance()


def _quote(text: str) -> str:
    """Format user input as a Markdown block quote for echoing back."""
    return "\n".join(f"> {line}" for line in text.splitlines()) or ">"


@client.tree.command(
    name="chat",
    description="AIちゃんと1回の対話をします",
)
@has_daily_tokens_left()
@track_token_usage()
@app_commands.rename(user_msg="message")
async def chat_command(interaction: Interaction, user_msg: str) -> None:
    try:
        run_id = str(uuid.uuid4())
        session_id = build_session_id(interaction.guild_id, interaction.channel)
        t0 = time.perf_counter()

        await interaction.response.defer()

        # Echo the prompt back right away: slash-command input is never posted
        # to the channel by Discord, so without this the question vanishes.
        await send_chunked_followup(interaction, _quote(user_msg))

        res = await generate_agents_response(user_msg)
        text = res.get("text", "") or "応答が空でした。"
        meta = res.get("meta", {})

        await send_chunked_followup(interaction, text)

        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Normalize usage to a dict if possible
        usage_val = (meta or {}).get("usage") if isinstance(meta, dict) else None
        if not isinstance(usage_val, dict):
            usage_val = None

        async with get_session() as session:
            await agent_runs_service.record_success(
                session,
                run_id=run_id,
                session_id=session_id,
                intent="chat",
                agent_key=(meta or {}).get("agent_key") or "unknown",
                model=(meta or {}).get("model"),
                usage=usage_val,
                latency_ms=latency_ms,
                tool_calls=(meta or {}).get("tool_calls"),
                handoffs=(meta or {}).get("handoffs"),
                output_preview=text,
            )
        interaction.extras[LLM_USAGE_EXTRA_KEY] = usage_val
    except Exception as e:
        logger.exception("Error in /chat command: %s", e)
        try:
            # Attempt to record failure metadata
            latency_ms = int(
                (time.perf_counter() - locals().get("t0", time.perf_counter())) * 1000,
            )
            run_id = locals().get("run_id", str(uuid.uuid4()))
            session_id = locals().get(
                "session_id",
                build_session_id(interaction.guild_id, interaction.channel),
            )
            async with get_session() as session:
                await agent_runs_service.record_error(
                    session,
                    run_id=run_id,
                    session_id=session_id,
                    intent="chat",
                    agent_key=None,
                    model=None,
                    latency_ms=latency_ms,
                    error=f"{type(e).__name__}: {e}",
                )
        except Exception:
            # Swallow service errors to avoid masking original error handling
            logger.debug("Failed to record /chat error to agent_runs")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "`/chat` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "`/chat` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
        except Exception:
            logger.debug("Failed to notify user about /chat error")
