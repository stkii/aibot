"""Reminder ORM model."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.aibot.db.base import Base


class Reminder(Base):
    """A scheduled reminder.

    `remind_at` is stored as a naive datetime representing UTC, because SQLite
    does not preserve timezone information. The service layer owns the
    conversion to and from timezone-aware UTC datetimes.
    """

    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    author_id: Mapped[int] = mapped_column(BigInteger)
    author_name: Mapped[str] = mapped_column(String(100))
    target_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str] = mapped_column(String(2000))
    remind_at: Mapped[datetime] = mapped_column(DateTime)
