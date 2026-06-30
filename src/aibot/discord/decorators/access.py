"""Access-control decorators for slash commands."""

import os
from collections.abc import Callable
from typing import TypeVar

from src.aibot.discord import Interaction, app_commands

T = TypeVar("T")


def is_admin_user() -> Callable[[T], T]:
    """Check whether the invoking user is listed in `ADMIN_USER_IDS`.

    Returns
    -------
    Callable[[T], T]
        A decorator that restricts the command to admin users.

    """

    def predicate(interaction: Interaction) -> bool:
        return interaction.user.id in [int(i) for i in os.environ["ADMIN_USER_IDS"].split(",")]

    return app_commands.check(predicate)
