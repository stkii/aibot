"""Persistence for `/ai` execution logs (the `agent_runs` table)."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.aibot.db.models.agent_run import AgentRun

_OUTPUT_PREVIEW_MAX = 2000


def _utc_now_naive() -> datetime:
    """Return the current UTC time as a naive datetime (storage convention)."""
    return datetime.now(UTC).replace(tzinfo=None)


async def record_success(  # noqa: PLR0913
    session: AsyncSession,
    *,
    run_id: str,
    session_id: str,
    intent: str,
    agent_key: str,
    model: str | None,
    usage: dict[str, Any] | None,
    latency_ms: int | None,
    tool_calls: list[dict[str, Any]] | None = None,
    handoffs: list[dict[str, Any]] | None = None,
    output_preview: str | None = None,
) -> None:
    """Record a successful agent run."""
    usage = usage or {}
    run = AgentRun(
        run_id=run_id,
        session_id=session_id,
        created_at=_utc_now_naive(),
        intent=intent,
        agent_key=agent_key,
        model=model,
        input_tokens=usage.get("input_tokens") or usage.get("prompt_tokens"),
        output_tokens=usage.get("output_tokens") or usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
        latency_ms=latency_ms,
        status="succeeded",
        error=None,
        tool_calls=json.dumps(tool_calls or []),
        handoffs=json.dumps(handoffs or []),
        output_preview=(output_preview or "")[:_OUTPUT_PREVIEW_MAX],
    )
    session.add(run)


async def record_error(  # noqa: PLR0913
    session: AsyncSession,
    *,
    run_id: str,
    session_id: str,
    intent: str | None,
    agent_key: str | None,
    model: str | None,
    latency_ms: int | None,
    error: str,
) -> None:
    """Record a failed agent run."""
    run = AgentRun(
        run_id=run_id,
        session_id=session_id,
        created_at=_utc_now_naive(),
        intent=intent,
        agent_key=agent_key,
        model=model,
        input_tokens=None,
        output_tokens=None,
        total_tokens=None,
        latency_ms=latency_ms,
        status="failed",
        error=error,
        tool_calls="[]",
        handoffs="[]",
        output_preview="",
    )
    session.add(run)


async def get_recent_for_session(
    session: AsyncSession,
    session_id: str,
    limit: int = 5,
) -> list[AgentRun]:
    """Return the most recent runs for a session, newest first."""
    result = await session.scalars(
        select(AgentRun)
        .where(AgentRun.session_id == session_id)
        .order_by(AgentRun.id.desc())
        .limit(limit),
    )
    return list(result.all())
