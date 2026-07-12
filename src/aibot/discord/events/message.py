"""on_message handling that continues /talk conversations inside their threads."""

from src.aibot.db.engine import get_session
from src.aibot.discord import Message, Thread
from src.aibot.discord.conversation import run_talk_turn
from src.aibot.discord.guild_guard import is_guild_allowed
from src.aibot.discord.messaging import build_session_id
from src.aibot.logger import logger
from src.aibot.services import talk_threads as talk_threads_service
from src.aibot.services import usage as usage_service

_LIMIT_MESSAGE = "今日の分のトークンは使い切ったみたい。また明日話そうね。"


async def handle_talk_message(message: Message) -> None:
    """Reply inside a registered talk thread when its owner speaks."""
    # The bot's own replies (and any other bot) also fire on_message; bail out
    # first so a reply can never trigger another reply.
    if message.author.bot:
        return
    if message.guild is None or not is_guild_allowed(message.guild.id):
        return
    thread = message.channel
    if not isinstance(thread, Thread):
        return

    async with get_session() as session:
        record = await talk_threads_service.get_thread(session, thread.id)
    if record is None or record.owner_id != message.author.id:
        return

    content = message.content.strip()
    if not content:
        # Without the message_content intent every message body arrives empty.
        logger.warning(
            "Empty message content in talk thread %s; is the message_content intent enabled?",
            thread.id,
        )
        return

    async with get_session() as session:
        allowed = await usage_service.has_tokens_left(session, message.author.id)
    if not allowed:
        await thread.send(_LIMIT_MESSAGE)
        return

    await run_talk_turn(
        destination=thread,
        thread_id=thread.id,
        record_session_id=build_session_id(message.guild.id, thread),
        user_id=message.author.id,
        content=content,
    )
