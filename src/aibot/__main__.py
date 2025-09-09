import asyncio
import os

import discord
from dotenv import load_dotenv

# Load environment variables here
# This must happen before importing modules that rely on env vars
load_dotenv()

from src.aibot.discord.client import BotClient  # noqa: E402
from src.aibot.discord.command import *  # noqa: E402, F403
from src.aibot.discord.event import *  # noqa: E402, F403
from src.aibot.infrastructure.dao.connection import ConnectionDAO  # noqa: E402
from src.aibot.infrastructure.dao.instruction import InstructionDAO  # noqa: E402
from src.aibot.infrastructure.dao.tts import TTSSessionDAO  # noqa: E402
from src.aibot.infrastructure.dao.usage import UsageDAO  # noqa: E402
from src.aibot.logger import logger  # noqa: E402
from src.aibot.service.scheduler import TaskScheduler  # noqa: E402


async def main() -> None:  # noqa: D103
    # Create database tables
    await ConnectionDAO().create_table()
    await InstructionDAO().create_table()
    await TTSSessionDAO().create_table()
    await UsageDAO().create_tables()

    DISCORD_BOT_TOKEN: str = os.environ["DISCORD_BOT_TOKEN"]  # noqa: N806

    client = BotClient.get_instance()

    # Load opus for voice functionality
    if not discord.opus.is_loaded():
        try:
            discord.opus.load_opus("/opt/homebrew/lib/libopus.dylib")
            logger.debug("Opus loaded successfully")
        except Exception as e:
            logger.warning(f"Failed to load Opus: {e}. Voice features may not work properly.")

    # Start all background schedulers
    TaskScheduler.start_all()

    try:
        await client.start(DISCORD_BOT_TOKEN)
    except Exception:
        logger.exception("Failed to start bot")
    finally:
        TaskScheduler.stop_all()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
