from discord import (
    Interaction,
    TextStyle,
)
from discord.ui import Modal, TextInput

from src.aibot.discord.client import BotClient
from src.aibot.discord.decorator.usage import track_usage
from src.aibot.infrastructure.api.factory import ResponseFactory
from src.aibot.model.message import ChatMessage
from src.aibot.service.instruction import InstructionService
from src.aibot.service.llm_resolver import LlmResolver

client = BotClient.get_instance()


class CodeModal(Modal):
    """Modal for entering code to fix."""

    code_input: TextInput

    def __init__(self, selected_model: str | None = None) -> None:
        super().__init__(title="コード修正")

        self.selected_model = selected_model

        self.code_input = TextInput(
            label="コード",
            style=TextStyle.long,
            placeholder="修正したいコードを入力してください",
            required=True,
        )
        self.add_item(self.code_input)

    async def on_submit(self, interaction: Interaction) -> None:
        """Handle the modal submission.

        Parameters
        ----------
        interaction : Interaction
            The interaction instance.

        """
        try:
            await interaction.response.defer(thinking=True)

            code = self.code_input.value
            if not code.strip():
                await interaction.followup.send(
                    "**ERROR** - コードが入力されていません",
                    ephemeral=True,
                )
                return

            instruction_service = InstructionService.get_instance()
            instruction = instruction_service.load_static_instruction("fixme")

            message = ChatMessage(role="user", content=code)

            # Resolve model and generate response
            resolver = LlmResolver.get_instance()
            factory = ResponseFactory.get_instance()
            llm_config = resolver.resolve_llm_model_for_command("fixme", self.selected_model)

            response = await factory.generate_llm_response(
                messages=message,
                instruction=instruction,
                llm_config=llm_config,
            )

            await interaction.followup.send(
                response.content,
                ephemeral=False,
            )
        except Exception as e:
            await interaction.followup.send(
                f"**ERROR** - レスポンスの生成に失敗しました: {e!s}",
                ephemeral=True,
            )


@client.tree.command(name="fixme", description="コードのバグを特定し修正します")
@track_usage()
async def fixme_command(interaction: Interaction) -> None:
    """Detect and fix bugs in code.

    Parameters
    ----------
    interaction : Interaction
        The interaction instance.

    """
    try:
        modal = CodeModal(selected_model=None)
        await interaction.response.send_modal(modal)

    except Exception as e:
        await interaction.response.send_message(
            f"**ERROR** - `/fixme`コマンドの実行中にエラーが発生しました: {e!s}",
            ephemeral=True,
        )
