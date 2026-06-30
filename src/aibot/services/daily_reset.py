"""Background loop that clears stale daily token usage at JST midnight."""

import asyncio
from datetime import datetime, time, timedelta

from src.aibot.db.engine import get_session
from src.aibot.logger import logger
from src.aibot.services import usage as usage_service
from src.aibot.services.usage import JST

_RESET_TIME = time(0, 0, 0)


def _seconds_until(target: time) -> float:
    """Seconds from now until the next occurrence of `target` in JST."""
    now = datetime.now(JST)
    next_run = datetime.combine(now.date(), target, tzinfo=JST)
    if now.time() >= target:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


async def run_daily_reset_loop() -> None:
    """Run forever, deleting old usage records once per day at JST midnight."""
    logger.info("Daily usage reset loop started")
    while True:
        await asyncio.sleep(_seconds_until(_RESET_TIME))
        try:
            async with get_session() as session:
                removed = await usage_service.reset_old_usage(session)
            logger.info("Daily usage reset: removed %d old record(s)", removed)
        except Exception:
            logger.exception("Failed to reset daily usage")
