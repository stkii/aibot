"""Registry of threads created by /talk."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.aibot.db.models.talk_thread import TalkThread


async def register_thread(
    session: AsyncSession,
    *,
    thread_id: int,
    guild_id: int,
    channel_id: int,
    owner_id: int,
) -> None:
    """Register a newly created talk thread."""
    session.add(
        TalkThread(
            thread_id=thread_id,
            guild_id=guild_id,
            channel_id=channel_id,
            owner_id=owner_id,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        ),
    )


async def get_thread(session: AsyncSession, thread_id: int) -> TalkThread | None:
    """Return the talk-thread record, or None when the thread is not one of ours."""
    return await session.get(TalkThread, thread_id)
