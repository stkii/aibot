from discord import Colour, Embed, Interaction, Member, app_commands

from src.aibot.discord.client import BotClient
from src.aibot.infrastructure.db.dao.token_limit_dao import DailyTokenUsageDao, UserTokenLimitDao
from src.aibot.logger import logger

client = BotClient.get_instance()


@client.tree.command(name="set-limit", description="1日あたりのトークン上限を設定します")
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def set_limit_command(
    interaction: Interaction,
    limit: app_commands.Range[int, 1],
    user: Member | None = None,
) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        await UserTokenLimitDao().set_daily_token_limit(
            daily_token_limit=limit,
            user_id=user.id if user is not None else None,
        )
        target = user.display_name if user is not None else "全体の既定値"
        await interaction.followup.send(f"{target}の1日のトークン上限を{limit}に設定したよ。")
    except Exception:
        logger.exception("Failed to set token limit")
        await interaction.followup.send("トークン上限の設定に失敗したよ。")


@set_limit_command.error
async def set_limit_error(interaction: Interaction, error: app_commands.AppCommandError) -> None:
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "この操作には管理者権限が必要だよ。", ephemeral=True
        )
        return
    logger.error("Set-limit command rejected: %s", error)
    await interaction.response.send_message("コマンドを実行できなかったよ。", ephemeral=True)


@client.tree.command(name="limit", description="現在のトークン使用量を確認します")
@app_commands.guild_only()
async def limit_command(interaction: Interaction) -> None:
    await interaction.response.defer(ephemeral=True)
    try:
        user = interaction.user
        is_admin = isinstance(user, Member) and user.guild_permissions.administrator
        user_limit = await UserTokenLimitDao().get_daily_token_limit(user.id)
        usage = await DailyTokenUsageDao().get_daily_token_usage(user.id)
        total = usage["total_tokens"]
        embed = Embed(description=f"<@{user.id}> のトークン使用量", color=Colour.green())
        embed.add_field(name="使用トークン", value=f"{total} / {'∞' if is_admin else user_limit}")
        embed.add_field(
            name="残りトークン", value="∞" if is_admin else str(max(0, user_limit - total))
        )
        embed.add_field(name="リクエスト数", value=str(usage["request_count"]))
        await interaction.followup.send(embed=embed)
    except Exception:
        logger.exception("Failed to get token usage")
        await interaction.followup.send("使用状況の取得に失敗したよ。")
