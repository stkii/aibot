from discord import (
    AllowedMentions,
    Colour,
    Embed,
    Interaction,
    Member,
    TextChannel,
    TextStyle,
    app_commands,
    ui,
)

from src.aibot.discord.client import BotClient
from src.aibot.discord.conversation import has_tokens_left, start_conversation
from src.aibot.discord.decorators import has_daily_tokens_left
from src.aibot.logger import logger

client = BotClient.get_instance()
_TEXT_CHANNEL_ONLY = "サーバーのテキストチャンネルで使ってね。会話スレッド内ではそのまま話せるよ。"


class TalkModal(ui.Modal, title="会話をはじめる"):
    def __init__(self) -> None:
        super().__init__(timeout=300)
        self.question = ui.TextInput(style=TextStyle.long, max_length=2000, required=True)
        self.add_item(ui.Label(text="質問・メッセージ", component=self.question))

    async def on_submit(self, interaction: Interaction) -> None:
        channel = interaction.channel
        user = interaction.user
        if not isinstance(channel, TextChannel) or not isinstance(user, Member):
            await interaction.response.send_message(_TEXT_CHANNEL_ONLY, ephemeral=True)
            return
        content = self.question.value.strip()
        if not content:
            await interaction.response.send_message("質問を入力してね。", ephemeral=True)
            return

        await interaction.response.defer(thinking=True)
        if not await has_tokens_left(user):
            await interaction.edit_original_response(content="今日のトークン上限に達したよ。")
            return
        embed = Embed(description=content, colour=Colour.blurple())
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        origin = await interaction.edit_original_response(
            embed=embed,
            allowed_mentions=AllowedMentions.none(),
        )
        try:
            thread = await origin.create_thread(
                name=" ".join(content.split())[:30],
                auto_archive_duration=1440,
            )
        except Exception:
            logger.exception("Could not create talk thread")
            await interaction.followup.send(
                "スレッドを作れなかったよ。botの公開スレッド作成権限を確認してね。",
                ephemeral=True,
            )
            return
        await start_conversation(thread, user, content)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        logger.error(
            "Could not start conversation", exc_info=(type(error), error, error.__traceback__)
        )
        text = "会話を開始できなかったよ。少し待ってから試してね。"
        if interaction.response.is_done():
            await interaction.followup.send(text, ephemeral=True)
        else:
            await interaction.response.send_message(text, ephemeral=True)


@client.tree.command(name="talk", description="質問を入力して会話用スレッドを作成します")
@app_commands.guild_only()
@has_daily_tokens_left()
async def talk(interaction: Interaction) -> None:
    if not isinstance(interaction.channel, TextChannel):
        await interaction.response.send_message(_TEXT_CHANNEL_ONLY, ephemeral=True)
        return
    await interaction.response.send_modal(TalkModal())


@talk.error
async def talk_error(interaction: Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.CheckFailure):
        text = str(error)
    else:
        logger.error("Talk command failed", exc_info=(type(error), error, error.__traceback__))
        text = "会話を開始できなかったよ。少し待ってから試してね。"
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)
