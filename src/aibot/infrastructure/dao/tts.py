import datetime
from typing import TypedDict

import aiosqlite

from ._base import DAOBase


class TTSSession(TypedDict):
    guild_id: str
    text_channel_id: str
    voice_channel_id: str
    is_active: bool
    is_reading_enabled: bool
    reading_channel_id: str | None
    created_at: datetime.datetime


class TTSSpeakerSettings(TypedDict):
    guild_id: str
    speaker: str
    style: str
    updated_at: datetime.datetime


class TTSSessionDAO(DAOBase):
    """Data Access Object for managing TTS sessions."""

    TABLE_NAME: str = "tts_sessions"
    SETTINGS_TABLE_NAME: str = "tts_settings"

    async def create_table(self) -> None:
        """Create table if it doesn't exist."""
        if not self.validate_table_name(self.TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)
        if not self.validate_table_name(self.SETTINGS_TABLE_NAME):
            msg = "INVALID TABLENAME: Only alphanumeric characters and underscores are allowed."
            raise ValueError(msg)

        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            session_query = f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                guild_id           TEXT PRIMARY KEY,
                text_channel_id    TEXT NOT NULL,
                voice_channel_id   TEXT NOT NULL,
                is_active          BOOLEAN NOT NULL DEFAULT FALSE,
                is_reading_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                reading_channel_id TEXT,
                created_at         DATETIME NOT NULL
            );
            """
            settings_query = f"""
            CREATE TABLE IF NOT EXISTS {self.SETTINGS_TABLE_NAME} (
                guild_id      TEXT PRIMARY KEY,
                speaker       TEXT NOT NULL,
                style         TEXT NOT NULL,
                updated_at    DATETIME NOT NULL
            );
            """
            await conn.execute(session_query)
            await conn.execute(settings_query)
            await conn.commit()
        finally:
            await conn.close()

    async def create_tts_session(
        self,
        guild_id: str,
        text_channel_id: str,
        voice_channel_id: str,
    ) -> None:
        """Create TTS session."""
        conn = await aiosqlite.connect(super().DB_NAME)
        created_at = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            INSERT OR REPLACE INTO tts_sessions (
                guild_id,
                text_channel_id,
                voice_channel_id,
                is_active,
                is_reading_enabled,
                reading_channel_id,
                created_at
            )
            VALUES (?, ?, ?, 1, 0, NULL, ?); -- TRUE is 1, FALSE is 0
            """
            await conn.execute(query, (guild_id, text_channel_id, voice_channel_id, created_at))
            await conn.commit()
        finally:
            await conn.close()

    async def get_active_tts_session(
        self,
        guild_id: str,
    ) -> TTSSession | None:
        """Get active TTS session."""
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT * FROM tts_sessions
            WHERE guild_id = ? AND is_active = 1;
            """
            cursor = await conn.execute(query, (guild_id,))
            row = await cursor.fetchone()
            if row:
                return TTSSession(
                    guild_id=row[0],
                    text_channel_id=row[1],
                    voice_channel_id=row[2],
                    is_active=bool(row[3]),
                    is_reading_enabled=bool(row[4]),
                    reading_channel_id=row[5],
                    created_at=row[6],
                )
            return None
        finally:
            await conn.close()

    async def end_tts_session(self, guild_id: str) -> None:
        """End TTS session."""
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            UPDATE tts_sessions
            SET is_active = 0, is_reading_enabled = 0, reading_channel_id = NULL
            WHERE guild_id = ?;
            """
            await conn.execute(query, (guild_id,))
            await conn.commit()
        finally:
            await conn.close()

    async def toggle_reading(self, guild_id: str, text_channel_id: str) -> bool:
        """Toggle reading status for a guild.

        Parameters
        ----------
        guild_id : str
            Guild ID
        text_channel_id : str
            Text channel ID to read from

        Returns
        -------
        bool
            New reading status (True if enabled, False if disabled)

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            # Get current status
            query = """
            SELECT is_reading_enabled
            FROM tts_sessions
            WHERE guild_id = ? AND is_active = 1;
            """
            cursor = await conn.execute(query, (guild_id,))
            row = await cursor.fetchone()

            if row is None:
                return False  # No active session

            current_status = bool(row[0])
            new_status = not current_status

            # Update status
            if new_status:
                # Enable reading
                update_query = """
                UPDATE tts_sessions
                SET is_reading_enabled = 1, reading_channel_id = ?
                WHERE guild_id = ? AND is_active = 1;
                """
                await conn.execute(update_query, (text_channel_id, guild_id))
            else:
                # Disable reading
                update_query = """
                UPDATE tts_sessions
                SET is_reading_enabled = 0, reading_channel_id = NULL
                WHERE guild_id = ? AND is_active = 1;
                """
                await conn.execute(update_query, (guild_id,))

            await conn.commit()
            return new_status
        finally:
            await conn.close()

    async def is_reading_enabled(self, guild_id: str) -> tuple[bool, str | None]:
        """Check if reading is enabled for a guild.

        Parameters
        ----------
        guild_id : str
            Guild ID

        Returns
        -------
        tuple[bool, str | None]
            Tuple of (is_reading_enabled, reading_channel_id)

        """
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT is_reading_enabled, reading_channel_id
            FROM tts_sessions
            WHERE guild_id = ? AND is_active = 1;
            """
            cursor = await conn.execute(query, (guild_id,))
            row = await cursor.fetchone()

            if row:
                return (bool(row[0]), row[1])
            return (False, None)
        finally:
            await conn.close()

    async def upsert_speaker_settings(
        self,
        guild_id: str,
        speaker: str,
        style: str,
    ) -> None:
        """Create or update speaker settings for a guild."""
        conn = await aiosqlite.connect(super().DB_NAME)
        now = datetime.datetime.now(super().TIMEZONE)
        try:
            query = """
            INSERT INTO tts_settings (guild_id, speaker, style, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                speaker = excluded.speaker,
                style = excluded.style,
                updated_at = excluded.updated_at;
            """
            await conn.execute(query, (guild_id, speaker, style, now))
            await conn.commit()
        finally:
            await conn.close()

    async def get_speaker_settings(
        self,
        guild_id: str,
    ) -> TTSSpeakerSettings | None:
        """Get speaker settings for a guild."""
        conn = await aiosqlite.connect(super().DB_NAME)
        try:
            query = """
            SELECT guild_id, speaker, style, updated_at
            FROM tts_settings
            WHERE guild_id = ?;
            """
            cursor = await conn.execute(query, (guild_id,))
            row = await cursor.fetchone()
            if row:
                return TTSSpeakerSettings(
                    guild_id=row[0],
                    speaker=row[1],
                    style=row[2],
                    updated_at=row[3],
                )
            return None
        finally:
            await conn.close()
