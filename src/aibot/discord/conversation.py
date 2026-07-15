"""One /talk conversation turn: generate, deliver, and record.

Used by both the /talk command (first turn) and the on_message handler
(every later turn), so the two paths behave identically.
"""

import asyncio
import time
import uuid

from src.aibot.db.engine import get_session
from src.aibot.discord import Messageable
from src.aibot.discord.messaging import send_chunked
from src.aibot.logger import logger
from src.aibot.services import agent_runs as agent_runs_service
from src.aibot.services import usage as usage_service
from src.aibot.services.agents import clear_conversation_session, generate_agents_response

_ERROR_MESSAGE = "ごめん、応答の生成中にエラーが出ちゃった。もう一回話しかけてみて。"

# Serializes turns per thread so rapid-fire messages cannot interleave the
# conversation memory. Keyed by thread id; the event loop is single-threaded,
# so plain dict access is safe.
_thread_locks: dict[int, asyncio.Lock] = {}


def _lock_for(thread_id: int) -> asyncio.Lock:
    lock = _thread_locks.get(thread_id)
    if lock is None:
        lock = asyncio.Lock()
        _thread_locks[thread_id] = lock
    return lock


def talk_session_id(thread_id: int) -> str:
    """The conversation-memory key for a talk thread."""
    return f"talk:{thread_id}"


async def reset_talk_memory(thread_id: int) -> None:
    """Erase a talk thread's conversation memory once any in-flight turn finishes."""
    async with _lock_for(thread_id):
        await clear_conversation_session(talk_session_id(thread_id))


async def run_talk_turn(
    *,
    destination: Messageable,
    thread_id: int,
    record_session_id: str,
    user_id: int,
    content: str,
) -> None:
    """Run one conversation turn in a talk thread and record its outcome."""
    async with _lock_for(thread_id):
        run_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        try:
            async with destination.typing():
                res = await generate_agents_response(
                    content,
                    session_id=talk_session_id(thread_id),
                )
            text = res.get("text", "") or "応答が空でした。"
            meta = res.get("meta", {})
            if not isinstance(meta, dict):
                meta = {}

            await send_chunked(destination, text)

            latency_ms = int((time.perf_counter() - t0) * 1000)
            usage_val = meta.get("usage")
            if not isinstance(usage_val, dict):
                usage_val = None

            async with get_session() as session:
                await agent_runs_service.record_success(
                    session,
                    run_id=run_id,
                    session_id=record_session_id,
                    intent="talk",
                    agent_key=meta.get("agent_key") or "unknown",
                    model=meta.get("model"),
                    usage=usage_val,
                    latency_ms=latency_ms,
                    tool_calls=meta.get("tool_calls"),
                    handoffs=meta.get("handoffs"),
                    output_preview=text,
                )
                token_usage = usage_service.normalize_token_usage(usage_val)
                if token_usage is not None:
                    await usage_service.add_daily_token_usage(
                        session,
                        user_id,
                        input_tokens=token_usage["input_tokens"],
                        output_tokens=token_usage["output_tokens"],
                        total_tokens=token_usage["total_tokens"],
                    )
        except Exception as e:
            logger.exception("Error in talk turn (thread %s)", thread_id)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            try:
                async with get_session() as session:
                    await agent_runs_service.record_error(
                        session,
                        run_id=run_id,
                        session_id=record_session_id,
                        intent="talk",
                        agent_key=None,
                        model=None,
                        latency_ms=latency_ms,
                        error=f"{type(e).__name__}: {e}",
                    )
            except Exception:
                logger.debug("Failed to record talk error to agent_runs")
            try:
                await destination.send(_ERROR_MESSAGE)
            except Exception:
                logger.debug("Failed to notify talk thread %s about the error", thread_id)
