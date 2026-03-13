"""Authentication helpers for Open Brain."""

from __future__ import annotations

from openbrain.config import Config
from openbrain.utils.errors import AuthenticationError


def get_current_user(headers: dict[str, str] | None = None) -> str:
    """Resolve the current user for the request.

    Dev mode bypasses auth and returns the configured default user.
    Hosted mode requires `Authorization: Bearer <OPENBRAIN_API_TOKEN>`.
    """

    if Config.is_dev_mode():
        return Config.DEFAULT_USER_ID

    auth_header = (headers or {}).get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing Authorization bearer token.")

    token = auth_header.removeprefix("Bearer ").strip()
    if not token or token != Config.OPENBRAIN_API_TOKEN:
        raise AuthenticationError("Invalid bearer token.")

    return Config.DEFAULT_USER_ID
