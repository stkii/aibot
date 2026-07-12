"""Shared messaging helpers: length-safe sending and session id building."""

import os

from src.aibot.discord import AllowedMentions, Interaction, Messageable

# Discord rejects any single message longer than 2000 characters.
DISCORD_MAX_CHARS = 2000


def resolve_chunk_limit() -> int:
    """Resolve the per-message character limit, capped at Discord's 2000."""
    raw = os.getenv("MAX_CHARS_PER_MESSAGE")
    if raw is None:
        return DISCORD_MAX_CHARS
    try:
        return max(1, min(int(raw), DISCORD_MAX_CHARS))
    except ValueError:
        return DISCORD_MAX_CHARS


def chunk_text(text: str, limit: int) -> list[str]:
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


async def send_chunked_followup(interaction: Interaction, text: str) -> None:
    """Send a possibly long response as one or more interaction follow-ups."""
    for chunk in chunk_text(text, resolve_chunk_limit()):
        await interaction.followup.send(chunk, allowed_mentions=AllowedMentions.none())


async def send_chunked(channel: Messageable, text: str) -> None:
    """Send a possibly long response as one or more channel messages."""
    for chunk in chunk_text(text, resolve_chunk_limit()):
        await channel.send(chunk, allowed_mentions=AllowedMentions.none())


def build_session_id(guild_id: int | None, channel: object) -> str:
    """Build the `guild:channel:thread` session id used for agent-run records."""
    gid = guild_id or 0
    if channel is None:
        return f"guild:{gid}:channel:0:thread:0"
    parent = getattr(channel, "parent", None)
    channel_id = getattr(parent, "id", None) or getattr(channel, "id", 0)
    thread_id = channel.id if parent is not None else 0  # type: ignore[attr-defined]
    return f"guild:{gid}:channel:{channel_id}:thread:{thread_id or 0}"
