"""Agent run log ORM model."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.aibot.db.base import Base


class AgentRun(Base):
    """One recorded execution of the `/ai` command.

    `created_at` is stored as a naive datetime representing UTC, matching the
    convention used by `Reminder`. `tool_calls` and `handoffs` hold JSON-encoded
    strings; the service layer owns the (de)serialization.
    """

    __tablename__ = "agent_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('succeeded', 'failed')",
            name="ck_agent_runs_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True)
    session_id: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime)
    intent: Mapped[str | None] = mapped_column(String(32))
    agent_key: Mapped[str | None] = mapped_column(String(128))
    model: Mapped[str | None] = mapped_column(String(128))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    error: Mapped[str | None] = mapped_column(String(2000))
    tool_calls: Mapped[str] = mapped_column(String, default="[]")
    handoffs: Mapped[str] = mapped_column(String, default="[]")
    output_preview: Mapped[str | None] = mapped_column(String(2000))
