"""Development mode authentication bypass."""

from openbrain.config import Config
from openbrain.utils.errors import AuthenticationError


def get_current_user() -> str:
    """Get the current authenticated user ID.

    In dev mode (DISABLE_AUTH=true), returns DEFAULT_USER_ID.
    """
    if Config.is_dev_mode():
        return Config.DEFAULT_USER_ID

    raise AuthenticationError(
        "Authentication not configured. Set DISABLE_AUTH=true for development mode."
    )
