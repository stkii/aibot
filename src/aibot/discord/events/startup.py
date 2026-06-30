"""Startup event handling: restore persisted reminders."""

from typing import TYPE_CHECKING

from src.aibot.db.engine import get_session
from src.aibot.logger import logger
from src.aibot.services import reminder as reminder_service

if TYPE_CHECKING:
    from src.aibot.discord.client import BotClient


async def restore_reminders(client: "BotClient") -> None:
    """Re-schedule every reminder still stored in the database.

    Reminders whose time has already passed (e.g. the bot was offline) are
    scheduled with a non-positive delay, so they fire as soon as possible.
    """
    async with get_session() as session:
        reminders = await reminder_service.get_pending_reminders(session)
    for reminder in reminders:
        client.scheduler.schedule(reminder.id, reminder_service.remind_at_aware(reminder))
    logger.info("Restored %d reminder(s)", len(reminders))
