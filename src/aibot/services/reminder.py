"""Reminder business logic: parsing, validation, and persistence."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.aibot.db.models.reminder import Reminder

JST = ZoneInfo("Asia/Tokyo")

_DATE_DIGITS = 8
_TIME_DIGITS = 4


class ReminderError(ValueError):
    """Raised when the user-supplied reminder input is invalid."""


def parse_remind_at(date: str, time: str) -> datetime:
    """Parse a 'YYYYMMDD' date and 'HHMM' time (JST) into an aware UTC datetime.

    Raises ReminderError when the format is wrong, the values are out of range,
    or the resulting datetime is in the past.
    """
    if not (date.isdigit() and len(date) == _DATE_DIGITS):
        msg = "日付は8桁の数字で指定してね（例: 20260701）"
        raise ReminderError(msg)
    if not (time.isdigit() and len(time) == _TIME_DIGITS):
        msg = "時刻は4桁の数字で指定してね（例: 0900）"
        raise ReminderError(msg)

    try:
        local = datetime(
            year=int(date[0:4]),
            month=int(date[4:6]),
            day=int(date[6:8]),
            hour=int(time[0:2]),
            minute=int(time[2:4]),
            tzinfo=JST,
        )
    except ValueError as exc:
        msg = "日付か時刻の値が正しくないよ（例: date=20260701 time=0900）"
        raise ReminderError(msg) from exc

    remind_at = local.astimezone(UTC)
    if remind_at <= datetime.now(UTC):
        msg = "過去の日時は指定できないよ"
        raise ReminderError(msg)
    return remind_at


def format_jst(remind_at: datetime) -> str:
    """Format an aware UTC datetime as a JST string for display."""
    return remind_at.astimezone(JST).strftime("%Y-%m-%d %H:%M")


def remind_at_aware(reminder: Reminder) -> datetime:
    """Return a stored reminder's fire time as an aware UTC datetime."""
    return reminder.remind_at.replace(tzinfo=UTC)


async def create_reminder(  # noqa: PLR0913
    session: AsyncSession,
    *,
    guild_id: int,
    channel_id: int,
    author_id: int,
    author_name: str,
    target_id: int,
    message: str,
    remind_at: datetime,
) -> Reminder:
    """Persist a new reminder and return it with its id assigned."""
    reminder = Reminder(
        guild_id=guild_id,
        channel_id=channel_id,
        author_id=author_id,
        author_name=author_name,
        target_id=target_id,
        message=message,
        remind_at=remind_at.astimezone(UTC).replace(tzinfo=None),
    )
    session.add(reminder)
    await session.flush()
    return reminder


async def get_reminder(session: AsyncSession, reminder_id: int) -> Reminder | None:
    """Fetch a reminder by id."""
    return await session.get(Reminder, reminder_id)


async def get_pending_reminders(session: AsyncSession) -> list[Reminder]:
    """Return all stored reminders ordered by fire time."""
    result = await session.scalars(select(Reminder).order_by(Reminder.remind_at))
    return list(result.all())


async def delete_reminder(session: AsyncSession, reminder_id: int) -> None:
    """Delete a reminder by id if it exists."""
    reminder = await session.get(Reminder, reminder_id)
    if reminder is not None:
        await session.delete(reminder)
