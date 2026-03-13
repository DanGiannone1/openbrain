"""Configuration module for the Open Brain MCP server."""

from __future__ import annotations

import os

from dotenv import load_dotenv

from openbrain.utils.errors import ConfigurationError

env = os.getenv("ENVIRONMENT", "dev")
env_file = f".env.{env}"

if os.path.exists(env_file):
    load_dotenv(env_file)
else:
    load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "dev")

    # Cosmos DB
    COSMOS_HOST: str = os.getenv("COSMOS_HOST", "")
    COSMOS_KEY: str = os.getenv("COSMOS_KEY", "")
    COSMOS_DATABASE: str = os.getenv("COSMOS_DATABASE", "openbrain")
    COSMOS_CONTAINER: str = os.getenv("COSMOS_CONTAINER", "openbrain-data")

    # Azure AI Foundry
    AI_FOUNDRY_ENDPOINT: str = os.getenv("AI_FOUNDRY_ENDPOINT", "")
    AI_FOUNDRY_API_KEY: str = os.getenv("AI_FOUNDRY_API_KEY", "")
    AI_FOUNDRY_EMBEDDING_DEPLOYMENT: str = os.getenv(
        "AI_FOUNDRY_EMBEDDING_DEPLOYMENT", "text-embedding-3-large"
    )

    # Auth
    DISABLE_AUTH: bool = os.getenv("DISABLE_AUTH", "false").lower() == "true"
    DEFAULT_USER_ID: str = os.getenv("DEFAULT_USER_ID", "dev-user")
    OPENBRAIN_API_TOKEN: str = os.getenv("OPENBRAIN_API_TOKEN", "")

    # Server
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration at import time."""

        required = {
            "COSMOS_HOST": cls.COSMOS_HOST,
            "COSMOS_KEY": cls.COSMOS_KEY,
            "AI_FOUNDRY_ENDPOINT": cls.AI_FOUNDRY_ENDPOINT,
            "AI_FOUNDRY_API_KEY": cls.AI_FOUNDRY_API_KEY,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigurationError(f"Missing required environment variables: {', '.join(missing)}")

        if not cls.DISABLE_AUTH and not cls.OPENBRAIN_API_TOKEN:
            raise ConfigurationError(
                "OPENBRAIN_API_TOKEN is required when DISABLE_AUTH is false."
            )

    @classmethod
    def is_dev_mode(cls) -> bool:
        """Return True when auth bypass is enabled."""

        return cls.DISABLE_AUTH


Config.validate()
