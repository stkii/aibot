from discord import Member, StageChannel, VoiceChannel, VoiceClient, VoiceState

from src.aibot.discord.client import BotClient
from src.aibot.discord.command.voice import _get_guild_speaker_settings
from src.aibot.infrastructure.dao.tts import TTSSessionDAO
from src.aibot.service.tts import TTSService

client = BotClient.get_instance()
tts_service = TTSService.get_instance()
tts_session_dao = TTSSessionDAO()


def _has_left_voice_channel(before: VoiceState, after: VoiceState) -> bool:
    """Return True when member has left the previous voice channel.

    This includes both:
    - Disconnected from voice (`after.channel is None`)
    - Moved to a different voice/stage channel
    """
    return before.channel is not None and (
        after.channel is None or after.channel.id != before.channel.id
    )


async def _stop_tts_session(guild_id: int, voice_client: VoiceClient | None) -> None:
    """Disconnect voice client and tear down TTS session for the guild."""
    if voice_client is not None and voice_client.is_connected():
        await voice_client.disconnect()
    await tts_session_dao.end_tts_session(str(guild_id))
    await tts_service.stop_guild(guild_id)


async def _get_session_voice_channel(guild_id: int) -> VoiceChannel | StageChannel | None:
    """Resolve active TTS session voice channel for the guild."""
    session = await tts_session_dao.get_active_tts_session(str(guild_id))
    if not session:
        return None

    channel = client.get_channel(int(session["voice_channel_id"]))
    if isinstance(channel, (VoiceChannel, StageChannel)):
        return channel
    return None


@client.event
async def on_voice_state_update(
    member: Member,
    before: VoiceState,
    after: VoiceState,
) -> None:
    """Event handler when a member changes their voice state.

    Called when:
      - A member joins a voice channel or stage channel.
      - A member leaves a voice channel or stage channel.
      - A member mutes their microphone or speaker.
      - A member is muted by a guild administrator.
    """
    if not _has_left_voice_channel(before, after):
        return

    before_channel = before.channel
    if before_channel is None:
        return

    guild_id = member.guild.id

    # ボット自身が監視VCから離脱した場合はセッションを確実に終了する
    if member == client.user:
        guild_voice_client = member.guild.voice_client
        voice_client = guild_voice_client if isinstance(guild_voice_client, VoiceClient) else None
        await _stop_tts_session(guild_id, voice_client)
        return

    # ============== メンバーが監視VCから離脱した場合の処理 ==============
    channel = await _get_session_voice_channel(guild_id)
    if channel is None or before_channel.id != channel.id:
        return

    # 離脱したメンバーの名前を読み上げ
    if not member.bot:  # ボットの離脱は読み上げない
        leave_message = f"{member.display_name}さんが退出しました"
        settings = await _get_guild_speaker_settings(guild_id)
        await tts_service.queue_message(
            leave_message,
            settings["speaker"],
            guild_id,
            settings["style"],
        )

    member_count = len([m for m in channel.members if not m.bot])
    # ボット以外のメンバーが0人になったら自動切断
    if member_count == 0:
        guild_voice_client = member.guild.voice_client
        voice_client = guild_voice_client if isinstance(guild_voice_client, VoiceClient) else None
        await _stop_tts_session(member.guild.id, voice_client)
