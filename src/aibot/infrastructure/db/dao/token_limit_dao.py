import os
from datetime import datetime, timedelta, timezone

import aiosqlite

from src.aibot.infrastructure.db.dao._base_dao import BaseDao

# user_id 0 is reserved to represent the default limit for all users.
_DEFAULT_LIMIT_USER_ID = 0
_FALLBACK_DAILY_LIMIT = 100
JST = timezone(timedelta(hours=+9), "JST")


def _get_default_daily_limit() -> int:
    """Read MAX_DAILY_USAGE, falling back to 100 and enforcing a minimum of 1."""
    raw = os.getenv("MAX_DAILY_USAGE")
    if raw is None:
        return _FALLBACK_DAILY_LIMIT
    try:
        return max(1, int(raw))
    except ValueError:
        return _FALLBACK_DAILY_LIMIT


class UserTokenLimitDao(BaseDao):
    def __init__(self) -> None:
        super().__init__()

    async def create_table(self, table_name: str) -> None:
        self.validate_table_name(table_name)
        query = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER NOT NULL UNIQUE,
                daily_token_limit  INTEGER NOT NULL,
                last_updated       DATETIME NOT NULL
            )
        """
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                await conn.execute(query)
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise

    async def get_daily_token_limit(self, user_id: int | None = None) -> int:
        """Return the user's limit, then the default row, then the env default."""
        query = """
            SELECT daily_token_limit
            FROM user_token_limits
            WHERE user_id = ?
        """
        async with aiosqlite.connect("aibot.db") as conn:
            if user_id is not None:
                async with conn.execute(query, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                if row is not None:
                    return row[0]

            async with conn.execute(query, (_DEFAULT_LIMIT_USER_ID,)) as cursor:
                default_row = await cursor.fetchone()
            if default_row is not None:
                return default_row[0]

        return _get_default_daily_limit()

    async def set_daily_token_limit(
        self,
        daily_token_limit: int,
        user_id: int | None = None,
    ) -> None:
        target_user_id = user_id if user_id is not None else _DEFAULT_LIMIT_USER_ID

        query = """
            INSERT INTO user_token_limits (
                user_id,
                daily_token_limit,
                last_updated
            )
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                daily_token_limit = excluded.daily_token_limit,
                last_updated = excluded.last_updated
        """
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                await conn.execute(
                    query,
                    (target_user_id, daily_token_limit, datetime.now(JST).isoformat()),
                )
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise


class DailyTokenUsageDao(BaseDao):
    def __init__(self) -> None:
        super().__init__()

    async def create_table(self, table_name: str) -> None:
        self.validate_table_name(table_name)
        query = f"""
            CREATE TABLE IF NOT EXISTS "{table_name}" (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id            INTEGER NOT NULL,
                usage_date         DATE NOT NULL,
                request_count      INTEGER NOT NULL DEFAULT 0,
                input_tokens       INTEGER NOT NULL DEFAULT 0,
                output_tokens      INTEGER NOT NULL DEFAULT 0,
                total_tokens       INTEGER NOT NULL DEFAULT 0,
                UNIQUE(user_id, usage_date)
            )
        """
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                await conn.execute(query)
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise

    async def get_daily_token_usage(self, user_id: int) -> dict[str, int]:
        """Return today's usage in JST, with zero counts when no record exists."""
        today = datetime.now(JST).date().isoformat()
        query = """
            SELECT request_count, input_tokens, output_tokens, total_tokens
            FROM daily_token_usage
            WHERE user_id = ? AND usage_date = ?
        """
        async with aiosqlite.connect("aibot.db") as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query, (user_id, today)) as cursor:
                row = await cursor.fetchone()
        if row is None:
            return {
                "request_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }
        return {
            "request_count": row["request_count"],
            "input_tokens": row["input_tokens"],
            "output_tokens": row["output_tokens"],
            "total_tokens": row["total_tokens"],
        }

    async def delete_old_records(self) -> int:
        """Delete usage records older than yesterday in JST and return the count."""
        yesterday = (datetime.now(JST).date() - timedelta(days=1)).isoformat()
        query = """
            DELETE FROM daily_token_usage
            WHERE usage_date < ?
        """
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                async with conn.execute(query, (yesterday,)) as cursor:
                    deleted_count = cursor.rowcount
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise

        return deleted_count

    async def insert_daily_token_usage(
        self,
        user_id: int,
        *,
        input_tokens: int,
        output_tokens: int,
        total_tokens: int,
    ) -> None:
        today = datetime.now(JST).date().isoformat()
        query = """
            INSERT INTO daily_token_usage (
                user_id,
                usage_date,
                request_count,
                input_tokens,
                output_tokens,
                total_tokens
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, usage_date) DO UPDATE SET
                request_count = daily_token_usage.request_count + 1,
                input_tokens = daily_token_usage.input_tokens + excluded.input_tokens,
                output_tokens = daily_token_usage.output_tokens + excluded.output_tokens,
                total_tokens = daily_token_usage.total_tokens + excluded.total_tokens
        """
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                await conn.execute(
                    query,
                    (user_id, today, 1, input_tokens, output_tokens, total_tokens),
                )
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise
