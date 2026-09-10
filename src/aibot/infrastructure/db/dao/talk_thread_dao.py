from datetime import UTC, datetime

import aiosqlite


class TalkThreadDao:
    async def create_table(self) -> None:
        async with aiosqlite.connect("aibot.db") as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS talk_threads (
                    thread_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    owner_id INTEGER NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """,
            )
            await conn.commit()

    async def register_thread(
        self,
        *,
        thread_id: int,
        guild_id: int,
        channel_id: int,
        owner_id: int,
    ) -> None:
        async with aiosqlite.connect("aibot.db") as conn:
            try:
                await conn.execute(
                    """
                    INSERT INTO talk_threads
                        (thread_id, guild_id, channel_id, owner_id, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (thread_id, guild_id, channel_id, owner_id, datetime.now(UTC).isoformat()),
                )
                await conn.commit()
            except aiosqlite.Error:
                await conn.rollback()
                raise

    async def get_owner_id(self, thread_id: int) -> int | None:
        async with (
            aiosqlite.connect("aibot.db") as conn,
            conn.execute(
                "SELECT owner_id FROM talk_threads WHERE thread_id = ?",
                (thread_id,),
            ) as cursor,
        ):
            row = await cursor.fetchone()
        return row[0] if row is not None else None
