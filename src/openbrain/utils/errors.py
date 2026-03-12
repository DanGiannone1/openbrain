"""Custom exception classes for the Open Brain MCP server."""


class OpenBrainError(Exception):
    """Base exception for all Open Brain errors."""
    pass


class CosmosDBError(OpenBrainError):
    """Error during Cosmos DB operations."""
    pass


class EmbeddingError(OpenBrainError):
    """Error during embedding generation."""
    pass


class DocumentNotFoundError(OpenBrainError):
    """Requested document does not exist."""
    pass


class ValidationError(OpenBrainError):
    """Document data validation failed."""
    pass


class AuthenticationError(OpenBrainError):
    """Authentication failed."""
    pass


class ConfigurationError(OpenBrainError):
    """Invalid configuration."""
    pass
