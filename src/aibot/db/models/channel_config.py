"""Per-guild reminder channel configuration ORM model."""

from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from src.aibot.db.base import Base


class ChannelConfig(Base):
    """The reminder destination channel for a single guild (one row per guild)."""

    __tablename__ = "channel_configs"

    guild_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
