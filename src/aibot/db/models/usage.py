"""Token usage and per-user limit ORM models."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.aibot.db.base import Base


class UserTokenLimit(Base):
    """A user's daily token limit (one row per user).

    `user_id` 0 is reserved to represent the default limit applied to every
    user who has no row of their own.
    """

    __tablename__ = "user_token_limits"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    daily_token_limit: Mapped[int] = mapped_column(Integer)
    last_updated: Mapped[datetime] = mapped_column(DateTime)


class DailyTokenUsage(Base):
    """A user's accumulated token usage for a single day.

    `usage_date` is the calendar date in JST; the service layer owns the
    timezone conversion when deciding which day a request belongs to.
    """

    __tablename__ = "daily_token_usage"
    __table_args__ = (UniqueConstraint("user_id", "usage_date", name="uq_daily_usage_user_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    usage_date: Mapped[date] = mapped_column(Date)
    request_count: Mapped[int] = mapped_column(Integer, default=0)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
