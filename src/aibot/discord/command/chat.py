from discord import Interaction, app_commands

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorator.usage import has_daily_usage_left, track_usage
from src.aibot.infrastructure.api.factory import ResponseFactory
from src.aibot.logger import logger
from src.aibot.model.message import ChatMessage
from src.aibot.service.instruction import InstructionService
from src.aibot.service.llm_resolver import LlmResolver
from src.aibot.service.provider import ProviderManager

api_factory = ResponseFactory()
client = BotClient().get_instance()
instruction_service = InstructionService.get_instance()
model_resolver = LlmResolver.get_instance()
provider_manager = ProviderManager.get_instance()


@client.tree.command(name="chat", description="AIとシングルターンのチャットを行います")
@has_daily_usage_left()
@track_usage()
@app_commands.rename(user_msg="message")
async def chat_command(interaction: Interaction, user_msg: str) -> None:
    """Single-turn chat with the bot.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.

    user_msg : str
        The message to send to the bot.

    """
    try:
        user = interaction.user
        logger.info("User ( %s ) is executing chat command", user)

        await interaction.response.defer()

        message = ChatMessage(role="user", content=user_msg)

        # Get static instruction only (no custom instructions for chat command)
        system_instruction = instruction_service.load_static_instruction("chat")
        if system_instruction is None:
            logger.warning("No static instruction found for chat command")
            await interaction.followup.send(
                "システム指示が設定されていません。管理者に問い合わせてください。",
                ephemeral=True,
            )
            return

        # Get model config and generate response
        model_config = model_resolver.resolve_llm_model_for_command("chat")

        response = await api_factory.generate_llm_response(
            messages=[message],
            instruction=system_instruction,
            llm_config=model_config,
        )

        await interaction.followup.send(f"{response.content}")
    except Exception as err:
        msg = f"Error in chat command: {err!s}"
        logger.exception(msg)
        await interaction.followup.send(
            "`/chat` コマンドの実行中にエラーが発生しました。",
            ephemeral=True,
        )
