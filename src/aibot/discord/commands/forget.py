from discord import Interaction, Thread, app_commands

from src.aibot.discord.client import BotClient
from src.aibot.discord.conversation import reset_talk_memory
from src.aibot.infrastructure.db.dao.talk_thread_dao import TalkThreadDao
from src.aibot.logger import logger

client = BotClient.get_instance()
_TALK_THREAD_ONLY = "このコマンドは /talk で作った会話スレッド内で使ってね。"


@client.tree.command(name="forget", description="このスレッドのAIの会話履歴を消去します")
@app_commands.guild_only()
async def forget(interaction: Interaction) -> None:
    channel = interaction.channel
    if interaction.guild_id is None or not isinstance(channel, Thread):
        await interaction.response.send_message(_TALK_THREAD_ONLY, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    try:
        owner_id = await TalkThreadDao().get_owner_id(channel.id)
        if owner_id is None:
            await interaction.followup.send(_TALK_THREAD_ONLY)
            return
        if owner_id != interaction.user.id:
            await interaction.followup.send("会話履歴を消せるのは、この会話を始めた人だけだよ。")
            return
        await reset_talk_memory(channel.id)
    except Exception:
        logger.exception("Could not clear conversation history in thread %s", channel.id)
        await interaction.followup.send("会話履歴を消せなかったよ。少し待ってから試してね。")
        return

    await interaction.followup.send("ここまでの会話は忘れたよ。また最初から話そう。")
