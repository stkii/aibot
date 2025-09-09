from __future__ import annotations

import datetime
from typing import TypedDict

import aiosqlite

from src.aibot.logger import logger

from ._base import DAOBase

# Types
DatetimeLike = str | datetime.datetime


class ConnectionInfo(TypedDict):
    """Connection status snapshot."""

    channel_id: str
    guild_id: str | None
    connected_at: DatetimeLike
    last_updated: DatetimeLike


class ConnectionDAO(DAOBase):
    """Data Access Object for logging voice channel connection history.

    This DAO only manages connection history for analytics and debugging.
    Connection status is handled by discord.py's native VoiceClient.

    Attributes
    ----------
    HISTORY_TABLE_NAME : str
        Name of the database table for connection history.

    """

    HISTORY_TABLE_NAME: str = "connection_history"

    async def create_table(self) -> None:
        """Create connection history table if it doesn't exist.

        This table logs all connection events for analytics and debugging.

        Raises
        ------
        ValueError
            If the table name contains invalid characters.

        """
        if not self.validate_table_name(self.HISTORY_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = f"""
            CREATE TABLE IF NOT EXISTS {self.HISTORY_TABLE_NAME} (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id     TEXT NOT NULL,
                guild_id       TEXT,
                action         TEXT NOT NULL CHECK
                    (action IN ('CONNECT', 'DISCONNECT', 'ERROR')),
                timestamp      DATETIME NOT NULL,
                error_message  TEXT
            );
            """
            await conn.execute(query)
            await conn.commit()
        except Exception:
            logger.exception("Failed to create history table")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def log_connect(self, channel_id: str, guild_id: str | None = None) -> None:
        """Log connection event to history.

        Parameters
        ----------
        channel_id : str
            The ID of the voice channel connected to.
        guild_id : str | None
            The ID of the guild (server) containing the channel.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)

        try:
            await self._log_history(conn, channel_id, guild_id, "CONNECT", now)
            await conn.commit()
        except Exception as e:
            try:
                await self._log_history(
                    conn,
                    channel_id,
                    guild_id,
                    "ERROR",
                    now,
                    f"Connection log failed: {type(e).__name__}: {e}",
                )
                await conn.commit()
            except Exception as log_err:
                logger.error(f"Failed to log error: {log_err}")
            logger.exception("log_connect() failed")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def log_disconnect(self, channel_id: str, guild_id: str | None = None) -> None:
        """Log disconnect event to history.

        Parameters
        ----------
        channel_id : str
            The ID of the voice channel disconnected from.
        guild_id : str | None
            The ID of the guild (server) containing the channel.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)

        try:
            await self._log_history(conn, channel_id, guild_id, "DISCONNECT", now)
            await conn.commit()
        except Exception as e:
            try:
                await self._log_history(
                    conn,
                    channel_id,
                    guild_id,
                    "ERROR",
                    now,
                    f"Disconnect log failed: {type(e).__name__}: {e}",
                )
                await conn.commit()
            except Exception as log_err:
                logger.error(f"Failed to log error: {log_err}")
            logger.exception("log_disconnect() failed")
            raise
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def log_error(self, channel_id: str, guild_id: str | None, error_msg: str) -> None:
        """Log error event to history.

        Parameters
        ----------
        channel_id : str
            The ID of the voice channel where error occurred.
        guild_id : str | None
            The ID of the guild (server) containing the channel.
        error_msg : str
            Error message to log.

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)

        try:
            await self._log_history(conn, channel_id, guild_id, "ERROR", now, error_msg)
            await conn.commit()
        except Exception as e:
            logger.error(f"Failed to log error to history: {e}")
        finally:
            try:
                await conn.close()
            except Exception as close_err:
                logger.error(f"Failed to close connection: {close_err}")

    async def _log_history(  # noqa: PLR0913
        self,
        conn: aiosqlite.Connection,
        channel_id: str,
        guild_id: str | None,
        action: str,
        timestamp: datetime.datetime,
        error_message: str | None = None,
    ) -> None:
        """Log connection event to history table.

        Parameters
        ----------
        conn : aiosqlite.Connection
            Database connection to use.
        channel_id : str
            ID of the voice channel.
        guild_id : str | None
            ID of the guild.
        action : str
            Action type ('CONNECT', 'DISCONNECT', 'ERROR').
        timestamp : datetime.datetime
            When the event occurred.
        error_message : str | None
            Error message if action is 'ERROR'.

        """
        query = """
        INSERT INTO connection_history
        (channel_id, guild_id, action, timestamp, error_message)
        VALUES (?, ?, ?, ?, ?);
        """
        await conn.execute(
            query,
            (
                channel_id,
                guild_id,
                action,
                timestamp,
                error_message,
            ),
        )
