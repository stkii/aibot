"""Guild allowlist gating: keep the bot working only in approved servers.

Gating is fail-closed: an interaction is allowed only when it comes from a
guild listed in `ALLOWED_GUILD_IDS`. DMs (no guild) are always rejected.
"""

import os

from src.aibot.discord import Interaction, app_commands
from src.aibot.logger import logger

_DENY_MESSAGE = "このサーバーでは利用できません。"


def allowed_guild_ids() -> set[int]:
    """Parse the approved guild IDs from the `ALLOWED_GUILD_IDS` env var."""
    raw = os.getenv("ALLOWED_GUILD_IDS", "")
    return {int(i) for i in raw.split(",") if i.strip()}


def is_guild_allowed(guild_id: int | None) -> bool:
    """Return True only for a guild on the allowlist (DM/`None` is never allowed)."""
    if guild_id is None:
        return False
    return guild_id in allowed_guild_ids()


class GuildGuardCommandTree(app_commands.CommandTree):
    """A command tree that rejects interactions outside the approved guilds.

    `interaction_check` runs before every slash command, so unauthorized
    guilds (and DMs) are blocked here — `/ai` never reaches the OpenAI call.
    """

    async def interaction_check(self, interaction: Interaction) -> bool:
        if is_guild_allowed(interaction.guild_id):
            return True

        logger.warning(
            "Blocked command in unauthorized context (guild_id=%s, user=%s)",
            interaction.guild_id,
            interaction.user.id,
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(_DENY_MESSAGE, ephemeral=True)
        return False
