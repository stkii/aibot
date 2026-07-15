"""/remind-cancel slash command: cancel one of the caller's pending reminders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, SelectOption, ui
from src.aibot.discord.client import BotClient
from src.aibot.services import reminder as reminder_service

if TYPE_CHECKING:
    from src.aibot.db.models.reminder import Reminder

client = BotClient.get_instance()

_GUILD_ONLY_MESSAGE = "このコマンドはサーバー内でだけ使えるよ"
_EMPTY_MESSAGE = "今はキャンセルできるリマインダーはないよ"
_GONE_MESSAGE = "そのリマインダーはもう送信済みか、キャンセルされてるみたい"

# A select menu holds at most 25 options; a label at most 100 characters,
# of which the JST timestamp and separator take 17.
_SELECT_MAX_ITEMS = 25
_PREVIEW_MAX_CHARS = 70
_VIEW_TIMEOUT_SECONDS = 180


def _preview(message: str) -> str:
    """Collapse whitespace and truncate the message for one-line display."""
    collapsed = " ".join(message.split())
    if len(collapsed) > _PREVIEW_MAX_CHARS:
        return collapsed[:_PREVIEW_MAX_CHARS] + "…"
    return collapsed


def _label(reminder: Reminder) -> str:
    when = reminder_service.format_jst(reminder_service.remind_at_aware(reminder))
    return f"{when}｜{_preview(reminder.message)}"


class RemindCancelSelect(ui.Select["RemindCancelView"]):
    """Pick one pending reminder to cancel."""

    def __init__(self, reminders: list[Reminder]) -> None:
        super().__init__(
            placeholder="キャンセルするリマインダーを選んでね",
            options=[
                SelectOption(label=_label(reminder), value=str(reminder.id))
                for reminder in reminders
            ],
        )

    async def callback(self, interaction: Interaction) -> None:
        """Delete the picked reminder and unschedule it."""
        reminder_id = int(self.values[0])
        async with get_session() as session:
            reminder = await reminder_service.get_reminder(session, reminder_id)
            # The reminder may have fired or been cancelled while the menu was
            # open; the author check guards against a stale or forged id.
            if reminder is None or reminder.author_id != interaction.user.id:
                await interaction.response.edit_message(content=_GONE_MESSAGE, view=None)
                return
            when = reminder_service.format_jst(reminder_service.remind_at_aware(reminder))
            preview = _preview(reminder.message)
            await reminder_service.delete_reminder(session, reminder_id)

        client.scheduler.cancel(reminder_id)
        await interaction.response.edit_message(
            content=f"{when} の「{preview}」をキャンセルしたよ",
            view=None,
        )


class RemindCancelView(ui.View):
    """The ephemeral select menu shown by /remind-cancel."""

    def __init__(self, reminders: list[Reminder]) -> None:
        super().__init__(timeout=_VIEW_TIMEOUT_SECONDS)
        self.add_item(RemindCancelSelect(reminders))


@client.tree.command(
    name="remind-cancel",
    description="きみが登録したリマインダーをキャンセルするよ",
)
async def remind_cancel(interaction: Interaction) -> None:
    """Offer the caller's pending reminders in a select menu (ephemeral)."""
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

    await interaction.response.send_message(
        "どのリマインダーをキャンセルする？",
        view=RemindCancelView(reminders[:_SELECT_MAX_ITEMS]),
        ephemeral=True,
    )
