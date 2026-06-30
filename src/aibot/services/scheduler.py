"""A Discord-independent scheduler that fires callbacks at a given time."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from src.aibot.logger import logger

FireCallback = Callable[[int], Awaitable[None]]


class Scheduler:
    """Schedules `on_fire(reminder_id)` calls. Knows nothing about Discord."""

    def __init__(self, on_fire: FireCallback) -> None:
        self._on_fire = on_fire
        self._tasks: dict[int, asyncio.Task[None]] = {}

    def schedule(self, reminder_id: int, when: datetime) -> None:
        """Fire `on_fire(reminder_id)` at `when` (an aware UTC datetime)."""
        existing = self._tasks.get(reminder_id)
        if existing is not None:
            existing.cancel()
        self._tasks[reminder_id] = asyncio.create_task(
            self._wait_and_fire(reminder_id, when),
        )

    def cancel(self, reminder_id: int) -> None:
        """Cancel a scheduled reminder if one is pending."""
        task = self._tasks.pop(reminder_id, None)
        if task is not None:
            task.cancel()

    async def _wait_and_fire(self, reminder_id: int, when: datetime) -> None:
        delay = (when - datetime.now(UTC)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)
        try:
            await self._on_fire(reminder_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Failed to fire reminder %s", reminder_id)
        finally:
            self._tasks.pop(reminder_id, None)
