"""Configuration module for Open Brain MCP server."""

import os
from dotenv import load_dotenv

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

    # Server
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def validate(cls) -> None:
        """Validate required configuration."""
        if not cls.COSMOS_HOST:
            raise ValueError("COSMOS_HOST environment variable is required")
        if not cls.COSMOS_KEY:
            raise ValueError("COSMOS_KEY environment variable is required")
        if not cls.AI_FOUNDRY_ENDPOINT:
            raise ValueError("AI_FOUNDRY_ENDPOINT environment variable is required")
        if not cls.AI_FOUNDRY_API_KEY:
            raise ValueError("AI_FOUNDRY_API_KEY environment variable is required")

    @classmethod
    def is_dev_mode(cls) -> bool:
        return cls.DISABLE_AUTH


Config.validate()
