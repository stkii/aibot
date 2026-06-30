"""Token-usage decorators: daily-limit gating and post-run accounting."""

import os
from collections.abc import Awaitable, Callable, Mapping
from functools import wraps
from typing import Any, TypeVar, cast

from src.aibot.db.engine import get_session
from src.aibot.discord import Interaction, app_commands
from src.aibot.logger import logger
from src.aibot.services import usage as usage_service

T = TypeVar("T")
# Avoid using "token" in this constant name; ruff S105 treats it as a possible secret.
LLM_USAGE_EXTRA_KEY = "llm_usage"


def _admin_user_ids() -> list[int]:
    return [int(i) for i in os.environ["ADMIN_USER_IDS"].split(",")]


def _normalize_token_usage(value: object) -> dict[str, int] | None:
    if not isinstance(value, Mapping):
        return None

    usage = cast("Mapping[str, object]", value)
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")
    if not isinstance(input_tokens, int):
        input_tokens = 0
    if not isinstance(output_tokens, int):
        output_tokens = 0
    if not isinstance(total_tokens, int):
        total_tokens = input_tokens + output_tokens

    if total_tokens <= 0:
        return None

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def has_daily_tokens_left() -> Callable[[T], T]:
    """Gate a command on the invoking user's remaining daily token quota.

    Admin users (listed in `ADMIN_USER_IDS`) always pass.

    Returns
    -------
    Callable[[T], T]
        A decorator that blocks the command once the daily limit is reached.

    """

    async def predicate(interaction: Interaction) -> bool:
        # Admin users bypass usage limits
        if interaction.user.id in _admin_user_ids():
            return True

        # Check usage limits for regular users
        async with get_session() as session:
            current_usage = await usage_service.get_user_daily_token_usage(
                session,
                interaction.user.id,
            )
            user_limit = await usage_service.get_daily_token_limit(
                session,
                interaction.user.id,
            )

        return current_usage["total_tokens"] < user_limit

    return app_commands.check(predicate)


def track_token_usage(usage_key: str = LLM_USAGE_EXTRA_KEY) -> Callable[[T], T]:
    """Automatically track token usage after successful command execution.

    This decorator should be applied to Discord app commands that consume
    token quota. The decorated command must set `interaction.extras[usage_key]`
    to token usage metadata when it has completed successfully.

    Returns
    -------
    Callable[[T], T]
        A decorator that tracks token usage after command execution.

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

            # Reset token usage for each invocation. Commands not decorated with
            # this function are not counted.
            interaction.extras[usage_key] = None

            # Execute the original command
            result = await func(*args, **kwargs)

            # Track token usage only when the command explicitly records it.
            token_usage = _normalize_token_usage(interaction.extras.get(usage_key))
            if token_usage is not None:
                async with get_session() as session:
                    await usage_service.add_daily_token_usage(
                        session,
                        interaction.user.id,
                        input_tokens=token_usage["input_tokens"],
                        output_tokens=token_usage["output_tokens"],
                        total_tokens=token_usage["total_tokens"],
                    )
                logger.debug(
                    "Token usage tracked for user %s: %s",
                    interaction.user.id,
                    token_usage,
                )

            return result

        return wrapper

    return decorator
