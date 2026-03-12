"""All 7 MCP tool definitions for Open Brain."""

from openbrain.auth.dev_auth import get_current_user
from openbrain.services import document_service
from openbrain.utils.telemetry import log_tool_call
from openbrain.utils.errors import (
    DocumentNotFoundError,
    ValidationError,
    EmbeddingError,
    CosmosDBError,
)


def _error(msg: str, details: list[str] | None = None) -> dict:
    result = {"error": msg}
    if details:
        result["details"] = details
    return result


def register_tools(mcp):
    """Register all 7 tools on the FastMCP server instance."""

    @mcp.tool()
    @log_tool_call
    def write(document: dict) -> dict:
        """Store a new document in Open Brain. Server generates ID, embedding, and timestamps.

        The document must include:
        - docType: "memory", "task", or "review"
        - narrative: clear, concise description of the item

        For memories: also include memoryType ("fact" or "idea") and optionally hypotheticalQueries (3 future questions this answers).
        For tasks: also include taskType ("goal", "oneTimeTask", or "recurringTask") and a state object.
        For reviews: also include triageAttempt (notes on why the item couldn't be categorized).
        """
        try:
            user_id = get_current_user()
            return document_service.write_document(user_id, document)
        except ValidationError as e:
            return _error("Validation error", [str(e)])
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def read(id: str) -> dict:
        """Get a document by ID. Returns all fields except embedding and rawText."""
        try:
            user_id = get_current_user()
            return document_service.read_document(user_id, id)
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def query(
        docType: str | None = None,
        filters: dict | None = None,
        sortBy: str = "createdAt",
        sortDesc: bool = True,
        limit: int = 50,
    ) -> dict:
        """Query documents with structured filters. This is the primary query tool.

        - docType: filter by "memory", "task", or "review"
        - filters: key-value equality filters using dot-path notation, e.g. {"state.status": "open", "taskType": "goal"}
        - sortBy: field to sort by (dot-path supported), default "createdAt"
        - sortDesc: sort descending (default true)
        - limit: max results 1-100 (default 50)

        Examples:
        - All open tasks: query(docType="task", filters={"state.status": "open"})
        - All memories: query(docType="memory")
        - Pending reviews: query(docType="review", filters={"resolvedAt": None})
        - Life state dump: query(limit=100)
        """
        try:
            user_id = get_current_user()
            return document_service.query_documents(user_id, docType, filters, sortBy, sortDesc, limit)
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def search(query: str, docType: str | None = None, topK: int = 5) -> dict:
        """Vector similarity search over Open Brain documents. Returns ranked results with similarity scores.

        - query: natural language search text
        - docType: optional filter by "memory", "task", or "review"
        - topK: max results 1-20 (default 5)

        The server embeds the query, runs vector search, and returns results ranked by cosine similarity (1 = identical).
        The server does not decide what's relevant — it returns results and you reason over them.
        """
        if not query or not query.strip():
            return _error("query is required")
        try:
            user_id = get_current_user()
            return document_service.search_documents(user_id, query, docType, topK)
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def update(id: str, updates: dict) -> dict:
        """Update fields on an existing document using dot-path deep merge.

        - id: document ID
        - updates: fields to update with dot-path notation, e.g. {"state.status": "done"}

        Dot-path deep merge: {"state.status": "done"} changes ONLY state.status, preserving all other state fields.

        Special behavior for recurring tasks: when setting state.status to "done" on a recurring task,
        the server automatically increments completionCount, sets lastCompletedAt, computes new dueDate
        (now + recurrenceDays), and resets status to "open".

        Immutable fields (ignored): id, userId, docType, createdAt, embedding.
        If narrative or hypotheticalQueries change, embedding is regenerated.
        """
        try:
            user_id = get_current_user()
            return document_service.update_document(user_id, id, updates)
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except EmbeddingError:
            return _error("Embedding service unavailable")
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def delete(id: str) -> dict:
        """Permanently delete a document by ID."""
        try:
            user_id = get_current_user()
            return document_service.delete_document(user_id, id)
        except DocumentNotFoundError:
            return _error(f"Document '{id}' not found")
        except CosmosDBError as e:
            return _error(f"Database error: {e}")

    @mcp.tool()
    @log_tool_call
    def raw_query(sql: str, parameters: list[dict] | None = None) -> dict:
        """Execute a raw Cosmos SQL query. Only use when the structured query tool cannot express what you need.

        - sql: Cosmos SQL query. MUST include c.userId = @userId in the WHERE clause.
        - parameters: additional query parameters, e.g. [{"name": "@status", "value": "open"}]

        The server injects @userId automatically. Results capped at 100. embedding and rawText stripped.
        Cosmos SQL is read-only (no DELETE/UPDATE/INSERT).
        """
        try:
            user_id = get_current_user()
            return document_service.raw_query_documents(user_id, sql, parameters)
        except CosmosDBError as e:
            return _error(f"Database error: {e}")
