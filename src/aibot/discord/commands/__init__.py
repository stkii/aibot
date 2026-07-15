"""Slash command modules. Importing them registers the commands on the tree."""

from src.aibot.discord.commands import chat, forget, limit, remind, remind_ch, talk

__all__ = ["chat", "forget", "limit", "remind", "remind_ch", "talk"]
