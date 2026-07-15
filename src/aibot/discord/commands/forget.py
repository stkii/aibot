"""/forget slash command: reset the conversation memory of a /talk thread."""

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, Thread
from src.aibot.discord.client import BotClient
from src.aibot.discord.conversation import reset_talk_memory
from src.aibot.logger import logger
from src.aibot.services import talk_threads as talk_threads_service

client = BotClient.get_instance()

_NOT_TALK_THREAD_MESSAGE = "このコマンドは /talk で作った会話スレッドの中でだけ使えるよ"
_NOT_OWNER_MESSAGE = "このスレッドの会話をリセットできるのは、スレッドを始めた人だけなんだ"
_DONE_MESSAGE = "ここまでの会話は忘れたよ。また最初からよろしくね"
_FAILED_MESSAGE = "ごめん、会話のリセットに失敗しちゃった。もう一回試してみて。"


@client.tree.command(
    name="forget",
    description="このスレッドでのAIちゃんとの会話を忘れて、まっさらな状態に戻すよ",
)
async def forget(interaction: Interaction) -> None:
    """Erase this talk thread's conversation memory (thread owner only)."""
    channel = interaction.channel
    if interaction.guild_id is None or not isinstance(channel, Thread):
        await interaction.response.send_message(_NOT_TALK_THREAD_MESSAGE, ephemeral=True)
        return

    async with get_session() as session:
        record = await talk_threads_service.get_thread(session, channel.id)
    if record is None:
        await interaction.response.send_message(_NOT_TALK_THREAD_MESSAGE, ephemeral=True)
        return
    if record.owner_id != interaction.user.id:
        await interaction.response.send_message(_NOT_OWNER_MESSAGE, ephemeral=True)
        return

    # Clearing waits for any in-flight turn to release the thread lock, which
    # can outlast the 3-second interaction window, so defer first.
    await interaction.response.defer()
    try:
        await reset_talk_memory(channel.id)
    except Exception:
        logger.exception("Failed to reset talk memory for thread %s", channel.id)
        await interaction.followup.send(_FAILED_MESSAGE)
        return
    await interaction.followup.send(_DONE_MESSAGE)
