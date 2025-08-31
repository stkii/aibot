from discord import Client, Intents, app_commands

from src.aibot.logger import logger

intents = Intents.default()
intents.message_content = True
intents.members = True


class BotClient(Client):
    """A singleton bot client class."""

    _instance: "BotClient"
    tree: app_commands.CommandTree

    def __init__(self) -> None:
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    @classmethod
    def get_instance(cls) -> "BotClient":
        """Get the singleton instance of the bot client."""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    async def setup_hook(self) -> None:
        """The hook called once before websocket connection."""
        logger.debug(
            "Registered slash commands: %s",
            [cmd.name for cmd in self.tree.get_commands()],
        )
        # Syncs the application commands to Discord
        await self.tree.sync()

    async def on_ready(self) -> None:
        """Event handler called when the bot is ready."""
        logger.info(f"Logged in as {self.user}")
        logger.info(
            "Available slash commands: %s",
            [cmd.name for cmd in self.tree.get_commands()],
        )
