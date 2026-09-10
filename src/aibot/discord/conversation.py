import asyncio
from weakref import WeakValueDictionary

from discord import AllowedMentions, Member, Message, Thread

from src.aibot.infrastructure.agents.agents import (
    clear_conversation_session,
    generate_agents_response,
)
from src.aibot.infrastructure.db.dao.talk_thread_dao import TalkThreadDao
from src.aibot.infrastructure.db.dao.token_limit_dao import DailyTokenUsageDao, UserTokenLimitDao
from src.aibot.logger import logger

_thread_locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()
_user_locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()


def _lock_for(locks: WeakValueDictionary[int, asyncio.Lock], key: int) -> asyncio.Lock:
    lock = locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks[key] = lock
    return lock


async def run_talk_turn(message: Message) -> None:
    """Check the token limit, generate a reply, record usage, and send it.

    Parameters
    ----------
    message : Message
        Message from the owner of a registered talk thread. Other messages are ignored.

    Notes
    -----
    Turns are serialized per thread and user. Administrators bypass the limit
    check, but their usage is still recorded.

    """
    channel = message.channel
    user = message.author
    if not isinstance(channel, Thread) or not isinstance(user, Member):
        return
    if user.bot or not message.content.strip():
        return

    async with _lock_for(_thread_locks, channel.id):
        owner_id = await TalkThreadDao().get_owner_id(channel.id)
        if owner_id != user.id:
            return
        await _reply(channel, user, message.content)


async def start_conversation(channel: Thread, user: Member, content: str) -> None:
    """Register the thread and finish the opening turn before accepting follow-ups."""
    async with _lock_for(_thread_locks, channel.id):
        await TalkThreadDao().register_thread(
            thread_id=channel.id,
            guild_id=channel.guild.id,
            channel_id=channel.parent_id,
            owner_id=user.id,
        )
        await _reply(channel, user, content)


async def reset_talk_memory(thread_id: int) -> None:
    """Clear history after any earlier turns in the thread have finished."""
    async with _lock_for(_thread_locks, thread_id):
        await clear_conversation_session(f"talk:{thread_id}")


async def has_tokens_left(user: Member) -> bool:
    if user.guild_permissions.administrator:
        return True
    usage = await DailyTokenUsageDao().get_daily_token_usage(user.id)
    limit = await UserTokenLimitDao().get_daily_token_limit(user.id)
    return usage["total_tokens"] < limit


async def _reply(channel: Thread, user: Member, content: str) -> None:
    async with _lock_for(_user_locks, user.id):
        try:
            usage_dao = DailyTokenUsageDao()
            if not await has_tokens_left(user):
                await channel.send("今日のトークン上限に達したよ。また明日話そう。")
                return

            async with channel.typing():
                result = await generate_agents_response(
                    content,
                    session_id=f"talk:{channel.id}",
                )
                usage = result["meta"].get("usage")
                if usage is not None:
                    await usage_dao.insert_daily_token_usage(
                        user.id,
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                        total_tokens=usage["total_tokens"],
                    )
                text = result["text"] or "応答が空だったよ。もう一度話しかけてみて。"
                for start in range(0, len(text), 2000):
                    await channel.send(
                        text[start : start + 2000],
                        allowed_mentions=AllowedMentions.none(),
                    )
        except Exception:
            logger.exception("Conversation failed in thread %s", channel.id)
            await channel.send("返答の処理中にエラーが起きたよ。少し待ってから試してね。")
