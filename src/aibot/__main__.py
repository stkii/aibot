"""Entry point: run the bot with `python -m src.aibot`."""

import os

from dotenv import load_dotenv

from src.aibot.discord.client import BotClient


def main() -> None:
    """Start the Discord bot using the DISCORD_TOKEN environment variable."""
    load_dotenv()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        msg = "環境変数 DISCORD_TOKEN を設定してね（.env でも可）"
        raise SystemExit(msg)
    BotClient.get_instance().run(token)


if __name__ == "__main__":
    main()
