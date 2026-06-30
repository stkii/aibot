"""/remind-ch slash command."""

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, TextChannel, app_commands
from src.aibot.discord.client import BotClient
from src.aibot.services import channel_config as channel_config_service

client = BotClient.get_instance()


@client.tree.command(
    name="remind-ch",
    description="リマインダーの送り先チャンネルを設定するよ",
)
@app_commands.describe(channel="リマインダーを送るチャンネル")
async def remind_ch(interaction: Interaction, channel: TextChannel) -> None:
    """Set the per-guild destination channel for reminders."""
    if interaction.guild_id is None:
        await interaction.response.send_message(
            "このコマンドはサーバー内でだけ使えるよ",
            ephemeral=True,
        )
        return

    async with get_session() as session:
        await channel_config_service.set_channel(
            session,
            interaction.guild_id,
            channel.id,
        )

    await interaction.response.send_message(
        f"リマインダーの送り先を {channel.mention} に設定したよ",
        ephemeral=True,
    )
