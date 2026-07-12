"""Slash command modules. Importing them registers the commands on the tree."""

from src.aibot.discord.commands import chat, limit, remind, remind_ch

__all__ = ["chat", "limit", "remind", "remind_ch"]
