"""Slash command modules. Importing them registers the commands on the tree."""

from src.aibot.discord.commands import (
    chat,
    forget,
    limit,
    remind,
    remind_cancel,
    remind_ch,
    remind_list,
    talk,
)

__all__ = [
    "chat",
    "forget",
    "limit",
    "remind",
    "remind_cancel",
    "remind_ch",
    "remind_list",
    "talk",
]
