"""Per-guild reminder channel configuration."""

from sqlalchemy.ext.asyncio import AsyncSession

from src.aibot.db.models.channel_config import ChannelConfig


async def set_channel(session: AsyncSession, guild_id: int, channel_id: int) -> None:
    """Set (or update) the reminder destination channel for a guild."""
    config = await session.get(ChannelConfig, guild_id)
    if config is None:
        session.add(ChannelConfig(guild_id=guild_id, channel_id=channel_id))
    else:
        config.channel_id = channel_id


async def get_channel(session: AsyncSession, guild_id: int) -> int | None:
    """Return the configured channel id for a guild, or None if unset."""
    config = await session.get(ChannelConfig, guild_id)
    return config.channel_id if config is not None else None
