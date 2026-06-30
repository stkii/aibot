"""Token usage tracking and per-user daily limits.

The day boundary is JST: a user's quota resets at midnight Japan time.
"""

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.aibot.db.models.usage import DailyTokenUsage, UserTokenLimit

JST = ZoneInfo("Asia/Tokyo")

FALLBACK_DAILY_LIMIT = 100
# user_id 0 is reserved to represent the default limit for all users.
_DEFAULT_LIMIT_USER_ID = 0


def get_default_daily_limit() -> int:
    """Default daily token limit from MAX_DAILY_USAGE (falls back to 100)."""
    raw = os.getenv("MAX_DAILY_USAGE")
    if raw is None:
        return FALLBACK_DAILY_LIMIT
    try:
        return max(1, int(raw))
    except ValueError:
        return FALLBACK_DAILY_LIMIT


def _today_jst() -> date:
    return datetime.now(JST).date()


async def set_daily_token_limit(
    session: AsyncSession,
    daily_token_limit: int,
    user_id: int | None = None,
) -> None:
    """Set or update a daily token limit (default for all users when user_id is None)."""
    target_user_id = user_id if user_id is not None else _DEFAULT_LIMIT_USER_ID
    now = datetime.now(UTC).replace(tzinfo=None)

    row = await session.get(UserTokenLimit, target_user_id)
    if row is None:
        session.add(
            UserTokenLimit(
                user_id=target_user_id,
                daily_token_limit=daily_token_limit,
                last_updated=now,
            ),
        )
    else:
        row.daily_token_limit = daily_token_limit
        row.last_updated = now


async def get_daily_token_limit(
    session: AsyncSession,
    user_id: int | None = None,
) -> int:
    """Return a user's limit, falling back to the default row then the env default."""
    if user_id is not None:
        row = await session.get(UserTokenLimit, user_id)
        if row is not None:
            return row.daily_token_limit

    default_row = await session.get(UserTokenLimit, _DEFAULT_LIMIT_USER_ID)
    if default_row is not None:
        return default_row.daily_token_limit
    return get_default_daily_limit()


async def get_user_daily_token_usage(session: AsyncSession, user_id: int) -> dict[str, int]:
    """Return today's (JST) usage for a user, zeroed when no record exists."""
    row = await session.scalar(
        select(DailyTokenUsage).where(
            DailyTokenUsage.user_id == user_id,
            DailyTokenUsage.usage_date == _today_jst(),
        ),
    )
    if row is None:
        return {
            "request_count": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }
    return {
        "request_count": row.request_count,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
    }


async def add_daily_token_usage(
    session: AsyncSession,
    user_id: int,
    *,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
) -> None:
    """Add token usage to a user's record for today (JST), creating it if needed."""
    today = _today_jst()
    row = await session.scalar(
        select(DailyTokenUsage).where(
            DailyTokenUsage.user_id == user_id,
            DailyTokenUsage.usage_date == today,
        ),
    )
    if row is None:
        session.add(
            DailyTokenUsage(
                user_id=user_id,
                usage_date=today,
                request_count=1,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            ),
        )
    else:
        row.request_count += 1
        row.input_tokens += input_tokens
        row.output_tokens += output_tokens
        row.total_tokens += total_tokens


async def reset_old_usage(session: AsyncSession) -> int:
    """Delete usage records older than yesterday (JST). Returns rows removed."""
    yesterday = (datetime.now(JST) - timedelta(days=1)).date()
    result = await session.execute(
        delete(DailyTokenUsage).where(DailyTokenUsage.usage_date < yesterday),
    )
    return cast("CursorResult[Any]", result).rowcount
