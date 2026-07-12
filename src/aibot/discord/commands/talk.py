"""/talk slash command: start a continuing conversation thread with the AI."""

from src.aibot.db.engine import get_session
from src.aibot.discord import (
    Colour,
    Embed,
    Interaction,
    TextChannel,
    TextStyle,
    ui,
)
from src.aibot.discord.client import BotClient
from src.aibot.discord.conversation import run_talk_turn
from src.aibot.discord.decorators.usage import has_daily_tokens_left
from src.aibot.discord.messaging import build_session_id
from src.aibot.logger import logger
from src.aibot.services import talk_threads as talk_threads_service

client = BotClient.get_instance()

_INPUT_MAX_CHARS = 2000
_THREAD_NAME_MAX_CHARS = 30
# A new message revives an archived thread, so 24 hours is just tidiness.
_THREAD_AUTO_ARCHIVE_MINUTES = 1440

_TEXT_CHANNEL_ONLY_MESSAGE = (
    "このコマンドはサーバーのテキストチャンネルでだけ使えるよ"
    "（会話スレッドの中では /talk なしでそのまま話しかけてね）"
)
_START_FAILED_MESSAGE = "スレッドを作れなかった…。botの権限（公開スレッドの作成）を確認してみて。"


def _thread_name(message: str) -> str:
    """Derive the thread name from the opening message."""
    collapsed = " ".join(message.split())
    return collapsed[:_THREAD_NAME_MAX_CHARS] or "AIちゃんとの会話"


class TalkModal(ui.Modal, title="AIちゃんと会話をはじめる"):
    """The opening-message form shown by /talk."""

    def __init__(self) -> None:
        super().__init__()
        self.message_input = ui.TextInput(
            style=TextStyle.long,
            placeholder="AIちゃんに話したいこと",
            max_length=_INPUT_MAX_CHARS,
        )
        self.add_item(ui.Label(text="メッセージ", component=self.message_input))

    async def on_submit(self, interaction: Interaction) -> None:
        """Post the opening embed, create the thread, and run the first turn."""
        guild_id = interaction.guild_id
        channel = interaction.channel
        if guild_id is None or not isinstance(channel, TextChannel):
            await interaction.response.send_message(
                _TEXT_CHANNEL_ONLY_MESSAGE,
                ephemeral=True,
            )
            return

        content = self.message_input.value

        embed = Embed(
            description=content,
            colour=Colour.blurple(),
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        try:
            await interaction.response.send_message(embed=embed)
            origin = await interaction.original_response()
            thread = await origin.create_thread(
                name=_thread_name(content),
                auto_archive_duration=_THREAD_AUTO_ARCHIVE_MINUTES,
            )
        except Exception:
            logger.exception("Could not create a talk thread")
            try:
                await interaction.followup.send(_START_FAILED_MESSAGE, ephemeral=True)
            except Exception:
                logger.debug("Failed to notify user about /talk startup error")
            return

        async with get_session() as session:
            await talk_threads_service.register_thread(
                session,
                thread_id=thread.id,
                guild_id=guild_id,
                channel_id=channel.id,
                owner_id=interaction.user.id,
            )

        await run_talk_turn(
            destination=thread,
            thread_id=thread.id,
            record_session_id=build_session_id(guild_id, thread),
            user_id=interaction.user.id,
            content=content,
        )


@client.tree.command(
    name="talk",
    description="AIちゃんとスレッドで継続的に会話します",
)
@has_daily_tokens_left()
async def talk(interaction: Interaction) -> None:
    """Open the talk form (server text channels only)."""
    if interaction.guild_id is None or not isinstance(interaction.channel, TextChannel):
        await interaction.response.send_message(_TEXT_CHANNEL_ONLY_MESSAGE, ephemeral=True)
        return
    await interaction.response.send_modal(TalkModal())
