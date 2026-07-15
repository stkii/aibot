"""/remind-list slash command: show the caller's pending reminders."""

from src.aibot.db.engine import get_session
from src.aibot.discord import Colour, Embed, Interaction
from src.aibot.discord.client import BotClient
from src.aibot.services import reminder as reminder_service

client = BotClient.get_instance()

_GUILD_ONLY_MESSAGE = "このコマンドはサーバー内でだけ使えるよ"
_EMPTY_MESSAGE = "今は登録されてるリマインダーはないよ"

# One reminder per line; short previews keep even a full list well within
# the embed description limit (4096 chars).
_LIST_MAX_ITEMS = 25
_PREVIEW_MAX_CHARS = 60


def _preview(message: str) -> str:
    """Collapse whitespace and truncate the message for one-line display."""
    collapsed = " ".join(message.split())
    if len(collapsed) > _PREVIEW_MAX_CHARS:
        return collapsed[:_PREVIEW_MAX_CHARS] + "…"
    return collapsed


@client.tree.command(
    name="remind-list",
    description="きみが登録したリマインダーの一覧を表示するよ",
)
async def remind_list(interaction: Interaction) -> None:
    """Show the caller's pending reminders in this guild (ephemeral)."""
    guild_id = interaction.guild_id
    if guild_id is None:
        await interaction.response.send_message(_GUILD_ONLY_MESSAGE, ephemeral=True)
        return

    async with get_session() as session:
        reminders = await reminder_service.get_reminders_by_author(
            session,
            guild_id=guild_id,
            author_id=interaction.user.id,
        )

    if not reminders:
        await interaction.response.send_message(_EMPTY_MESSAGE, ephemeral=True)
        return

    lines = [
        f"**{reminder_service.format_jst(reminder_service.remind_at_aware(reminder))}** "
        f"<@{reminder.target_id}> 「{_preview(reminder.message)}」"
        for reminder in reminders[:_LIST_MAX_ITEMS]
    ]
    if len(reminders) > _LIST_MAX_ITEMS:
        lines.append(f"…ほかに {len(reminders) - _LIST_MAX_ITEMS} 件あるよ")

    embed = Embed(
        title="登録中のリマインダー",
        description="\n".join(lines),
        colour=Colour.blurple(),
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)
