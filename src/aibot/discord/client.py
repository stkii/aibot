from typing import ClassVar

from discord import Client, Intents, Message, app_commands

from src.aibot.discord.conversation import run_talk_turn
from src.aibot.infrastructure.db.dao.talk_thread_dao import TalkThreadDao
from src.aibot.infrastructure.db.dao.token_limit_dao import DailyTokenUsageDao, UserTokenLimitDao
from src.aibot.logger import logger


class BotClient(Client):
    _instance: ClassVar["BotClient | None"] = None

    def __init__(self) -> None:
        intents = Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    @classmethod
    def get_instance(cls) -> "BotClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def setup_hook(self) -> None:
        from src.aibot.discord import commands  # noqa: PLC0415, F401

        await UserTokenLimitDao().create_table("user_token_limits")
        await DailyTokenUsageDao().create_table("daily_token_usage")
        await TalkThreadDao().create_table()
        await self.tree.sync()

    async def on_ready(self) -> None:
        logger.info("Logged in as %s", self.user)

    async def on_message(self, message: Message) -> None:
        await run_talk_turn(message)
