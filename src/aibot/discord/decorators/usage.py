from collections.abc import Callable
from typing import TypeVar

import aiosqlite
from discord import Interaction, Member, app_commands

from src.aibot.discord.conversation import has_tokens_left
from src.aibot.logger import logger

T = TypeVar("T")


def has_daily_tokens_left() -> Callable[[T], T]:
    """Require remaining daily tokens, allowing administrators to bypass the limit."""

    async def predicate(interaction: Interaction) -> bool:
        user = interaction.user
        if not isinstance(user, Member):
            msg = "このコマンドはサーバー内で使ってね。"
            raise app_commands.CheckFailure(msg)
        try:
            allowed = await has_tokens_left(user)
        except aiosqlite.Error as error:
            logger.exception("Could not check token limit")
            msg = "使用量を確認できなかったよ。少し待ってから試してね。"
            raise app_commands.CheckFailure(msg) from error
        if not allowed:
            msg = "今日のトークン上限に達したよ。また明日話そう。"
            raise app_commands.CheckFailure(msg)
        return True

    return app_commands.check(predicate)
