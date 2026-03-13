"""MCP tool definitions for Open Brain."""

from fastmcp.server.dependencies import CurrentHeaders

from openbrain.auth.dev_auth import get_current_user
from openbrain.services import document_service
from openbrain.utils.errors import (
    AuthenticationError,
    CosmosDBError,
    DocumentNotFoundError,
    EmbeddingError,
    ValidationError,
)
from openbrain.utils.telemetry import log_tool_call


def _error(msg: str, details: list[str] | None = None) -> dict:
    result = {"error": msg}
    if details:
        result["details"] = details
    return result


def register_tools(mcp):
    """Register the Open Brain MCP tools."""

    @mcp.tool()
    @log_tool_call
    def write(document: dict, headers: dict[str, str] = CurrentHeaders()) -> dict:
        """Store a new document in Open Brain.

        Supported doc types:
        - `memory`: factual/reference recall with optional `hypotheticalQueries`
        - `idea`: speculative thoughts with optional `goalId`
        - `task`: one-time or recurring work with optional `goalId`
        - `goal`: longer-running objectives
        - `misc`: ambiguous captures awaiting later classification
        - `userSettings`: per-user config such as tag taxonomy
        """
        try:
            user_id = get_current_user(headers)
            return document_service.write_document(user_id, document)
        except AuthenticationError as exc:
            return _error(str(exc))
        except ValidationError as exc:
            return _error("Validation error", [str(exc)])
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def read(id: str, headers: dict[str, str] = CurrentHeaders()) -> dict:
        """Get a document by ID. Returns sanitized fields only."""
        try:
            user_id = get_current_user(headers)
            return document_service.read_document(user_id, id)
        except AuthenticationError as exc:
            return _error(str(exc))
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def query(
        docType: str | None = None,
        filters: dict | None = None,
        sortBy: str = "createdAt",
        sortDesc: bool = True,
        limit: int = 50,
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        """Query documents with structured filters.

        This is the primary tool for operational views such as open tasks,
        active goals, misc backlog, user settings, and whole-life snapshots.
        """
        try:
            user_id = get_current_user(headers)
            return document_service.query_documents(user_id, docType, filters, sortBy, sortDesc, limit)
        except AuthenticationError as exc:
            return _error(str(exc))
        except ValidationError as exc:
            return _error("Validation error", [str(exc)])
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def search(
        query: str,
        docType: str | None = None,
        topK: int = 5,
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        """Semantic search over embedded document types.

        Search is intentionally limited to `memory` and `idea`.
        """
        try:
            user_id = get_current_user(headers)
            return document_service.search_documents(user_id, query, docType, topK)
        except AuthenticationError as exc:
            return _error(str(exc))
        except ValidationError as exc:
            return _error("Validation error", [str(exc)])
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def update(id: str, updates: dict, headers: dict[str, str] = CurrentHeaders()) -> dict:
        """Update fields on an existing document using dot-path merge."""
        try:
            user_id = get_current_user(headers)
            return document_service.update_document(user_id, id, updates)
        except AuthenticationError as exc:
            return _error(str(exc))
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except ValidationError as exc:
            return _error("Validation error", [str(exc)])
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def delete(id: str, headers: dict[str, str] = CurrentHeaders()) -> dict:
        """Delete a document by ID."""
        try:
            user_id = get_current_user(headers)
            return document_service.delete_document(user_id, id)
        except AuthenticationError as exc:
            return _error(str(exc))
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")

    @mcp.tool()
    @log_tool_call
    def raw_query(
        sql: str,
        parameters: list[dict] | None = None,
        headers: dict[str, str] = CurrentHeaders(),
    ) -> dict:
        """Run a read-only Cosmos SQL query with partition enforcement."""
        try:
            user_id = get_current_user(headers)
            return document_service.raw_query_documents(user_id, sql, parameters)
        except AuthenticationError as exc:
            return _error(str(exc))
        except ValidationError as exc:
            return _error("Validation error", [str(exc)])
        except CosmosDBError as exc:
            return _error(f"Database error: {exc}")
