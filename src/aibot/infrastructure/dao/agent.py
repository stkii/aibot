from __future__ import annotations

import datetime
import json
from typing import Any

import aiosqlite

from ._base import DAOBase


class AgentDAO(DAOBase):
    TABLE: str = "agent_runs"

    async def create_table(self) -> None:
        """Create table if it doesn't exist."""
        if not self.validate_table_name(self.TABLE):
            msg = "INVALID TABLENAME: Only alphanumerics and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE} (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id         TEXT UNIQUE,
                session_id     TEXT NOT NULL,
                created_at     DATETIME NOT NULL,
                intent         TEXT,
                agent_key      TEXT,
                model          TEXT,
                input_tokens   INTEGER,
                output_tokens  INTEGER,
                total_tokens   INTEGER,
                latency_ms     INTEGER,
                status         TEXT CHECK(status IN ('succeeded','failed')),
                error          TEXT,
                tool_calls     TEXT,
                handoffs       TEXT,
                output_preview TEXT
            );
            """
            await conn.execute(query)
            await conn.commit()
        finally:
            await conn.close()

    async def record_success(  # noqa: PLR0913
        self,
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
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            now = datetime.datetime.now(super().TIMEZONE)
            query = """
            INSERT INTO agent_runs (
                run_id, session_id, created_at, intent, agent_key, model,
                input_tokens, output_tokens, total_tokens, latency_ms,
                status, error, tool_calls, handoffs, output_preview
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'succeeded', NULL, ?, ?, ?)
            """
            await conn.execute(
                query,
                (
                    run_id,
                    session_id,
                    now,
                    intent,
                    agent_key,
                    model,
                    (usage or {}).get("prompt_tokens"),
                    (usage or {}).get("completion_tokens"),
                    (usage or {}).get("total_tokens"),
                    latency_ms,
                    json.dumps(tool_calls or []),
                    json.dumps(handoffs or []),
                    (output_preview or "")[:2000],
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def record_error(  # noqa: PLR0913
        self,
        *,
        run_id: str,
        session_id: str,
        intent: str | None,
        agent_key: str | None,
        model: str | None,
        latency_ms: int | None,
        error: str,
    ) -> None:
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            now = datetime.datetime.now(super().TIMEZONE)
            query = """
            INSERT INTO agent_runs (
                run_id, session_id, created_at, intent, agent_key, model,
                input_tokens, output_tokens, total_tokens, latency_ms,
                status, error, tool_calls, handoffs, output_preview
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, 'failed', ?, '[]', '[]', '')
            """
            await conn.execute(
                query,
                (
                    run_id,
                    session_id,
                    now,
                    intent,
                    agent_key,
                    model,
                    latency_ms,
                    error,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def get_recent_for_session(
        self,
        session_id: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT run_id, created_at, intent, agent_key, model,
                   input_tokens, output_tokens, total_tokens,
                   latency_ms, status, error, output_preview
            FROM agent_runs
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """
            cursor = await conn.execute(query, (session_id, limit))
            rows = await cursor.fetchall()
            return [
                {
                    "run_id": r[0],
                    "created_at": r[1],
                    "intent": r[2],
                    "agent_key": r[3],
                    "model": r[4],
                    "input_tokens": r[5],
                    "output_tokens": r[6],
                    "total_tokens": r[7],
                    "latency_ms": r[8],
                    "status": r[9],
                    "error": r[10],
                    "output_preview": r[11],
                }
                for r in rows
            ]
        finally:
            await conn.close()
