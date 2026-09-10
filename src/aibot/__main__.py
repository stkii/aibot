import os

from dotenv import load_dotenv

from src.aibot.discord.client import BotClient


def main() -> None:
    load_dotenv()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        msg = "DISCORD_TOKEN is not available."
        raise SystemExit(msg)
    BotClient.get_instance().run(token)


if __name__ == "__main__":
    main()
