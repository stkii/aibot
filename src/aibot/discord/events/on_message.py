from discord import Message as DiscordMessage

from src.aibot.discord.client import BotClient
from src.aibot.discord.command.voice import _get_guild_speaker_settings
from src.aibot.infrastructure.dao.tts import TTSSessionDAO
from src.aibot.service.tts import TTSService

client = BotClient.get_instance()
tts_service = TTSService.get_instance()
tts_session_dao = TTSSessionDAO()


@client.event
async def on_message(message: DiscordMessage) -> None:
    """Event handler when a message is sent."""
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return

    # Ignore direct messages (guild is None)
    if message.guild is None:
        return

    guild_id = message.guild.id

    # Ignore slash commands
    if message.content.startswith("/"):
        return

    # Check if there's an active TTS session for this guild
    session = await tts_session_dao.get_active_tts_session(str(guild_id))
    if not session:
        return

    # Check if reading is enabled for this guild
    is_reading_enabled, reading_channel_id = await tts_session_dao.is_reading_enabled(
        str(guild_id),
    )

    if not is_reading_enabled or not reading_channel_id:
        return

    # Only process messages from the reading channel
    if message.channel.id != int(reading_channel_id):
        return

    # Queue the message for TTS
    tts_message = message.content
    settings = _get_guild_speaker_settings(guild_id)
    await tts_service.queue_message(
        tts_message,
        settings["speaker"],
        guild_id,
        settings["style"],
    )
