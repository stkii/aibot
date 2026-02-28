import os
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar, cast

from discord import Interaction, app_commands

from src.aibot.infrastructure.dao.usage import UsageDAO
from src.aibot.logger import logger

T = TypeVar("T")


def has_daily_usage_left() -> Callable[[T], T]:
    """Check if the user has not reached their daily usage limit.

    Returns
    -------
    Callable[[T], T]
        A decorator that checks whether the user has not reached
        their daily limit of command calls.

    """

    async def predicate(interaction: Interaction) -> bool:
        # Admin users bypass usage limits
        if interaction.user.id in [int(i) for i in os.environ["ADMIN_USER_IDS"].split(",")]:
            return True

        # Check usage limits for regular users
        dao = UsageDAO()
        current_usage = await dao.get_user_daily_usage(interaction.user.id)
        user_limit = await dao.get_daily_usage_limit(interaction.user.id)

        return cast("bool", current_usage < user_limit)

    return app_commands.check(predicate)


def track_usage(flag_key: str = "count_usage") -> Callable[[T], T]:
    """Automatically track API usage after successful command execution.

    This decorator should be applied to Discord app commands that consume
    API quota. The decorated command must set `interaction.extras[flag_key]`
    to True when it has completed successfully.

    Returns
    -------
    Callable[[T], T]
        A decorator that tracks usage after command execution.

    """

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> object:
            # Find the interaction parameter by iterating through all arguments
            # Decorator can't assume the order or structure of function parameters
            interaction = None
            for arg in args:
                if isinstance(arg, Interaction):
                    interaction = arg
                    break

            if interaction is None:
                logger.error("No Interaction found in command arguments for usage tracking")
                return await func(*args, **kwargs)

            # Reset the success flag for each invocation.
            interaction.extras[flag_key] = False

            # Execute the original command
            result = await func(*args, **kwargs)

            # Track usage only when the command explicitly marks success.
            if interaction.extras.get(flag_key) is True:
                usage_dao = UsageDAO()
                await usage_dao.increment_daily_usage_count(interaction.user.id)
                logger.debug("Usage tracked for user %s", interaction.user.id)

            return result

        return wrapper

    return decorator
