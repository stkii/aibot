"""Talk-thread registry ORM model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from src.aibot.db.base import Base


class TalkThread(Base):
    """A thread created by /talk in which the bot keeps conversing.

    `created_at` is stored as a naive datetime representing UTC, matching the
    convention used by the other tables.
    """

    __tablename__ = "talk_threads"

    thread_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime)
