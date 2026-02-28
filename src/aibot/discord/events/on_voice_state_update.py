from discord import Member, VoiceClient, VoiceState

from src.aibot.discord.client import BotClient
from src.aibot.discord.command.voice import _get_guild_speaker_settings
from src.aibot.infrastructure.dao.tts import TTSSessionDAO
from src.aibot.service.tts import TTSService

client = BotClient.get_instance()
tts_service = TTSService.get_instance()
tts_session_dao = TTSSessionDAO()


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
    # ボット自身の状態変化は無視
    if member == client.user:
        return

    # ============== メンバーがボイスチャンネルから退出した場合の処理 ==============
    if before.channel and not after.channel:
        guild_id = member.guild.id
        # アクティブなTTSセッションがあるか確認
        session = await tts_session_dao.get_active_tts_session(str(guild_id))
        if not session:
            return
        # このハンドラを発火させたチャンネルがセッション対象かどうか確認
        voice_channel = client.get_channel(int(session["voice_channel_id"]))
        if not voice_channel or before.channel.id != voice_channel.id:
            return

        # 退出したメンバーの名前を読み上げ
        if not member.bot:  # ボットの退出は読み上げない
            leave_message = f"{member.display_name}さんが退出しました"
            settings = _get_guild_speaker_settings(guild_id)
            await tts_service.queue_message(
                leave_message,
                settings["speaker"],
                guild_id,
                settings["style"],
            )

        member_count = len([m for m in voice_channel.members if not m.bot])
        # ボット以外のメンバーが0人になったら自動切断
        if member_count == 0:
            voice_client = member.guild.voice_client
            if (
                voice_client
                and isinstance(voice_client, VoiceClient)
                and voice_client.is_connected()
            ):
                await voice_client.disconnect()
                await tts_session_dao.end_tts_session(str(member.guild.id))
                await tts_service.stop_guild(member.guild.id)
