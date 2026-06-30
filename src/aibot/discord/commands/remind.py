"""/remind slash command."""

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, Member, app_commands
from src.aibot.discord.client import BotClient
from src.aibot.services import channel_config as channel_config_service
from src.aibot.services import reminder as reminder_service
from src.aibot.services.reminder import ReminderError

client = BotClient.get_instance()


@client.tree.command(
    name="remind",
    description="指定した日時にメンションでリマインダーを送るよ",
)
@app_commands.describe(
    member="リマインドする相手",
    date="日付（8桁の数字・例: 20260701）",
    time="時刻（4桁の数字・例: 0900）",
    message="リマインドの内容",
)
async def remind(
    interaction: Interaction,
    member: Member,
    date: str,
    time: str,
    message: str,
) -> None:
    """Schedule a reminder that mentions `member` at the given JST date/time."""
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "このコマンドはサーバー内でだけ使えるよ",
            ephemeral=True,
        )
        return

    try:
        remind_at = reminder_service.parse_remind_at(date, time)
    except ReminderError as exc:
        await interaction.response.send_message(str(exc), ephemeral=True)
        return

    async with get_session() as session:
        channel_id = await channel_config_service.get_channel(session, interaction.guild_id)
        if channel_id is None:
            await interaction.response.send_message(
                "先に /remind-ch で送り先チャンネルを設定してね",
                ephemeral=True,
            )
            return
        reminder = await reminder_service.create_reminder(
            session,
            guild_id=interaction.guild_id,
            channel_id=channel_id,
            author_id=interaction.user.id,
            author_name=interaction.user.display_name,
            target_id=member.id,
            message=message,
            remind_at=remind_at,
        )
        reminder_id = reminder.id

    client.scheduler.schedule(reminder_id, remind_at)

    await interaction.response.send_message(
        f"{member.display_name} さんへ {reminder_service.format_jst(remind_at)} に"
        f"「{message}」をリマインドするね",
        ephemeral=True,
    )
