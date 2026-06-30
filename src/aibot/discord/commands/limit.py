"""/limit and /set-limit slash commands: daily token usage and limits."""

import os

from src.aibot.db.engine import get_session
from src.aibot.discord import Colour, Embed, Interaction
from src.aibot.discord.client import BotClient
from src.aibot.discord.decorators.access import is_admin_user
from src.aibot.logger import logger
from src.aibot.services import usage as usage_service

client = BotClient.get_instance()


@client.tree.command(
    name="set-limit",
    description="1日あたりのトークン上限を設定します",
)
@is_admin_user()
async def set_limit_command(interaction: Interaction, limit: int) -> None:
    """Set the default daily token limit for each user (admin only)."""
    try:
        if limit < 1:
            await interaction.response.send_message(
                "**limit**は1以上の整数を指定してください",
                ephemeral=True,
            )
            return

        async with get_session() as session:
            await usage_service.set_daily_token_limit(session, limit)

        await interaction.response.send_message(
            f"トークン上限を{limit}/dayに設定しました",
            ephemeral=True,
        )
        logger.info(
            "%s set default daily token limit to %d",
            interaction.user,
            limit,
        )
    except Exception:
        await interaction.response.send_message(
            "[ERROR] `/set-limit` コマンドでエラーが発生しました",
            ephemeral=True,
        )
        logger.exception("An error occurred in the set-limit command")


@client.tree.command(
    name="limit",
    description="現在の利用状況を確認します",
)
async def limit_command(interaction: Interaction) -> None:
    """Check the user's limit and current usage."""
    try:
        user = interaction.user
        admin_ids: list[int] = [int(id_str) for id_str in os.environ["ADMIN_USER_IDS"].split(",")]

        async with get_session() as session:
            user_limit = await usage_service.get_daily_token_limit(session, user.id)
            current_usage = await usage_service.get_user_daily_token_usage(session, user.id)
        total_tokens = current_usage["total_tokens"]

        embed = Embed(
            description=f"<@{user.id}> の利用状況",
            color=Colour.blue(),
        )

        # Admin user is unlimited
        if user.id in admin_ids:
            embed.add_field(name="使用トークン", value=f"{total_tokens} / ∞", inline=True)
            embed.add_field(name="残りトークン", value="∞", inline=True)
        else:
            embed.add_field(
                name="使用トークン",
                value=f"{total_tokens} / {user_limit}",
                inline=True,
            )
            embed.add_field(
                name="残りトークン",
                value=max(0, user_limit - total_tokens),
                inline=True,
            )
        embed.add_field(
            name="リクエスト数",
            value=current_usage["request_count"],
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception:
        await interaction.response.send_message(
            "[ERROR] 使用状況の取得に失敗しました",
            ephemeral=True,
        )
        logger.exception("An error occurred in the limit command")
