"""The Discord bot client (singleton)."""

import asyncio

from src.aibot.db.engine import get_session, init_db
from src.aibot.discord import AllowedMentions, Client, Guild, Intents, Messageable, app_commands
from src.aibot.discord.guild_guard import (
    GuildGuardCommandTree,
    allowed_guild_ids,
    is_guild_allowed,
)
from src.aibot.logger import logger
from src.aibot.services import reminder as reminder_service
from src.aibot.services.scheduler import Scheduler

intents = Intents.default()
intents.members = True


class BotClient(Client):
    """A singleton bot client class."""

    _instance: "BotClient"
    tree: app_commands.CommandTree

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = GuildGuardCommandTree(self)
        self.scheduler = Scheduler(on_fire=self._fire_reminder)
        self._restored = False
        self._reset_task: asyncio.Task[None] | None = None

    @classmethod
    def get_instance(cls) -> "BotClient":
        """Get the singleton instance of the bot client."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    async def setup_hook(self) -> None:
        """The hook called once before websocket connection."""
        # Importing the commands package runs the decorators that register
        # every slash command on the command tree before we sync it.
        from src.aibot.discord import commands  # noqa: F401, PLC0415

        await init_db()
        logger.debug(
            "Registered slash commands: %s",
            [cmd.name for cmd in self.tree.get_commands()],
        )
        await self.tree.sync()

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready."""
        logger.info("Logged in as %s", self.user)
        await self._leave_unauthorized_guilds()
        if not self._restored:
            from src.aibot.discord.events import startup  # noqa: PLC0415
            from src.aibot.services.daily_reset import run_daily_reset_loop  # noqa: PLC0415

            await startup.restore_reminders(self)
            self._reset_task = asyncio.create_task(run_daily_reset_loop())
            self._restored = True

    async def on_guild_join(self, guild: Guild) -> None:
        """Leave immediately when added to a guild that is not allowlisted."""
        if not is_guild_allowed(guild.id):
            logger.warning(
                "Leaving unauthorized guild on join: %s (%s)",
                guild.name,
                guild.id,
            )
            await guild.leave()

    async def _leave_unauthorized_guilds(self) -> None:
        """Leave unauthorized guilds on startup, but only when an allowlist is set.

        Skipping when the allowlist is empty avoids accidentally leaving every
        server because `ALLOWED_GUILD_IDS` was forgotten.
        """
        allowed = allowed_guild_ids()
        if not allowed:
            return
        for guild in list(self.guilds):
            if guild.id not in allowed:
                logger.warning(
                    "Leaving unauthorized guild on startup: %s (%s)",
                    guild.name,
                    guild.id,
                )
                await guild.leave()

    async def _fire_reminder(self, reminder_id: int) -> None:
        """Deliver a due reminder to its channel, then remove it from the database."""
        async with get_session() as session:
            reminder = await reminder_service.get_reminder(session, reminder_id)
            if reminder is None:
                return
            content = (
                f"<@{reminder.target_id}> "
                f"{reminder.author_name}さんからのリマインダー: {reminder.message}"
            )
            channel_id = reminder.channel_id

        try:
            channel = self.get_channel(channel_id) or await self.fetch_channel(channel_id)
            if isinstance(channel, Messageable):
                await channel.send(content, allowed_mentions=AllowedMentions(users=True))
            else:
                logger.warning(
                    "Reminder %s: channel %s is not messageable",
                    reminder_id,
                    channel_id,
                )
        except Exception:
            logger.exception("Could not deliver reminder %s", reminder_id)

        async with get_session() as session:
            await reminder_service.delete_reminder(session, reminder_id)
