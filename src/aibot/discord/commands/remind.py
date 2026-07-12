"""/remind slash command."""

from datetime import datetime, timedelta

from src.aibot.db.engine import get_session
from src.aibot.discord import (
    Interaction,
    Member,
    SelectOption,
    TextStyle,
    app_commands,
    ui,
)
from src.aibot.discord.client import BotClient
from src.aibot.services import channel_config as channel_config_service
from src.aibot.services import reminder as reminder_service
from src.aibot.services.reminder import JST, ReminderError

client = BotClient.get_instance()

# The delivered message also carries a mention and the author name, and the
# whole thing must fit in Discord's 2000-character limit.
_MESSAGE_MAX_CHARS = 1800

# Today plus two weeks; a select menu holds at most 25 options.
_DATE_CHOICE_DAYS = 14

_WEEKDAYS_JA = "月火水木金土日"

_GUILD_ONLY_MESSAGE = "このコマンドはサーバー内でだけ使えるよ"
_NO_CHANNEL_MESSAGE = "先に /remind-ch で送り先チャンネルを設定してね"


def _date_options() -> list[SelectOption]:
    """Build date choices from today (JST) through two weeks ahead."""
    today = datetime.now(JST)
    options: list[SelectOption] = []
    for offset in range(_DATE_CHOICE_DAYS + 1):
        day = today + timedelta(days=offset)
        prefix = "今日 " if offset == 0 else "明日 " if offset == 1 else ""
        label = f"{prefix}{day.month}/{day.day}（{_WEEKDAYS_JA[day.weekday()]}）"
        options.append(
            SelectOption(label=label, value=day.strftime("%Y%m%d"), default=offset == 0),
        )
    return options


class RemindModal(ui.Modal, title="リマインドの設定"):
    """A tap-only reminder form: date/hour/minute selects plus a message box."""

    def __init__(self, member: Member) -> None:
        super().__init__()
        self.member = member

        self.date_select = ui.Select(options=_date_options())
        self.hour_select = ui.Select(
            placeholder="時を選んでね",
            options=[SelectOption(label=f"{h}時", value=f"{h:02d}") for h in range(24)],
        )
        self.minute_select = ui.Select(
            placeholder="分を選んでね",
            options=[
                SelectOption(label=f"{m:02d}分", value=f"{m:02d}") for m in range(0, 60, 10)
            ],
        )
        self.message_input = ui.TextInput(
            style=TextStyle.long,
            placeholder="リマインドする内容",
            max_length=_MESSAGE_MAX_CHARS,
        )

        self.add_item(ui.Label(text="日付", component=self.date_select))
        self.add_item(ui.Label(text="時", component=self.hour_select))
        self.add_item(ui.Label(text="分", component=self.minute_select))
        self.add_item(ui.Label(text="内容", component=self.message_input))

    async def on_submit(self, interaction: Interaction) -> None:
        """Validate the selections and persist/schedule the reminder."""
        date = self.date_select.values[0]
        time = f"{self.hour_select.values[0]}{self.minute_select.values[0]}"
        try:
            remind_at = reminder_service.parse_remind_at(date, time)
        except ReminderError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        guild_id = interaction.guild_id
        if guild_id is None:
            await interaction.response.send_message(_GUILD_ONLY_MESSAGE, ephemeral=True)
            return

        message = self.message_input.value
        async with get_session() as session:
            channel_id = await channel_config_service.get_channel(session, guild_id)
            if channel_id is None:
                await interaction.response.send_message(_NO_CHANNEL_MESSAGE, ephemeral=True)
                return
            reminder = await reminder_service.create_reminder(
                session,
                guild_id=guild_id,
                channel_id=channel_id,
                author_id=interaction.user.id,
                author_name=interaction.user.display_name,
                target_id=self.member.id,
                message=message,
                remind_at=remind_at,
            )
            reminder_id = reminder.id

        client.scheduler.schedule(reminder_id, remind_at)

        await interaction.response.send_message(
            f"{self.member.display_name} さんへ {reminder_service.format_jst(remind_at)} に"
            f"「{message}」をリマインドするね",
            ephemeral=True,
        )


@client.tree.command(
    name="remind",
    description="指定した日時にメンションでリマインダーを送るよ",
)
@app_commands.describe(member="リマインドする相手")
async def remind(interaction: Interaction, member: Member) -> None:
    """Open the reminder form for `member` after the guild-side checks pass."""
    if interaction.guild_id is None:
        await interaction.response.send_message(_GUILD_ONLY_MESSAGE, ephemeral=True)
        return

    # Checked here too so nobody fills in the whole form only to be told to
    # run /remind-ch first; on_submit re-fetches as the source of truth.
    async with get_session() as session:
        channel_id = await channel_config_service.get_channel(session, interaction.guild_id)
    if channel_id is None:
        await interaction.response.send_message(_NO_CHANNEL_MESSAGE, ephemeral=True)
        return

    await interaction.response.send_modal(RemindModal(member))
