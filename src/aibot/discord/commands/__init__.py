"""Slash command modules. Importing them registers the commands on the tree."""

from src.aibot.discord.commands import ai, limit, remind, remind_ch

__all__ = ["ai", "limit", "remind", "remind_ch"]
