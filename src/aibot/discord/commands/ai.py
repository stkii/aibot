"""/ai slash command: converse with the configured agents."""

from __future__ import annotations

import os
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
from src.aibot.logger import logger
from src.aibot.services import agent_runs as agent_runs_service
from src.aibot.services.agents import generate_agents_response

client = BotClient.get_instance()

# Discord rejects any single message longer than 2000 characters.
DISCORD_MAX_CHARS = 2000


def _resolve_chunk_limit() -> int:
    """Resolve the per-message character limit, capped at Discord's 2000."""
    raw = os.getenv("MAX_CHARS_PER_MESSAGE")
    if raw is None:
        return DISCORD_MAX_CHARS
    try:
        return max(1, min(int(raw), DISCORD_MAX_CHARS))
    except ValueError:
        return DISCORD_MAX_CHARS


def _chunk_text(text: str, limit: int) -> list[str]:
    """Split text into chunks that each fit within Discord's length limit.

    Prefers splitting on newlines so paragraphs and code blocks stay intact;
    falls back to a hard cut when a single line exceeds the limit.
    """
    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at <= 0:
            chunks.append(remaining[:limit])
            remaining = remaining[limit:]
        else:
            chunks.append(remaining[:split_at])
            remaining = remaining[split_at + 1 :]
    chunks.append(remaining)
    return chunks


async def _send_chunked(interaction: Interaction, text: str) -> None:
    """Send a possibly long response as one or more Discord messages."""
    for chunk in _chunk_text(text, _resolve_chunk_limit()):
        await interaction.followup.send(chunk)


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
@has_daily_tokens_left()
@track_token_usage()
@app_commands.rename(user_msg="message")
async def ai_command(interaction: Interaction, user_msg: str) -> None:
    try:
        run_id = str(uuid.uuid4())
        session_id = _build_session_id(interaction)
        t0 = time.perf_counter()

        await interaction.response.defer()

        res = await generate_agents_response(user_msg)
        text = res.get("text", "") or "応答が空でした。"
        meta = res.get("meta", {})

        await _send_chunked(interaction, text)

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
                intent="ai",
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
        logger.exception("Error in /ai command: %s", e)
        try:
            # Attempt to record failure metadata
            latency_ms = int(
                (time.perf_counter() - locals().get("t0", time.perf_counter())) * 1000,
            )
            run_id = locals().get("run_id", str(uuid.uuid4()))
            session_id = locals().get("session_id", _build_session_id(interaction))
            async with get_session() as session:
                await agent_runs_service.record_error(
                    session,
                    run_id=run_id,
                    session_id=session_id,
                    intent="ai",
                    agent_key=None,
                    model=None,
                    latency_ms=latency_ms,
                    error=f"{type(e).__name__}: {e}",
                )
        except Exception:
            # Swallow service errors to avoid masking original error handling
            logger.debug("Failed to record /ai error to agent_runs")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    "`/ai` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
            else:
                await interaction.response.send_message(
                    "`/ai` コマンドの実行中にエラーが発生しました。",
                    ephemeral=True,
                )
        except Exception:
            logger.debug("Failed to notify user about /ai error")
