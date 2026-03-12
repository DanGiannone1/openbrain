"""Document service — all CRUD, query, search, and update operations."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError as PydanticValidationError

from openbrain import cosmos_client
from openbrain.models.memory import MemoryDocument
from openbrain.models.task import TaskDocument
from openbrain.models.review import ReviewDocument
from openbrain.services.embedding_service import generate_embedding
from openbrain.utils.errors import DocumentNotFoundError, ValidationError, EmbeddingError

logger = logging.getLogger("openbrain")

DOC_TYPE_MODELS = {
    "memory": MemoryDocument,
    "task": TaskDocument,
    "review": ReviewDocument,
}

IMMUTABLE_FIELDS = {"id", "userId", "docType", "createdAt", "embedding"}
STRIP_FIELDS = {"embedding", "rawText", "_rid", "_self", "_etag", "_attachments", "_ts"}
SEARCH_STRIP_FIELDS = STRIP_FIELDS | {"hypotheticalQueries"}


def _strip(doc: dict, extra_strip: set[str] | None = None) -> dict:
    """Remove internal/sensitive fields from a document before returning to client."""
    keys_to_strip = STRIP_FIELDS | (extra_strip or set())
    return {k: v for k, v in doc.items() if k not in keys_to_strip}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_document(user_id: str, document: dict) -> dict:
    """Validate, generate ID/embedding/timestamps, write to Cosmos."""
    doc_type = document.get("docType")
    if not doc_type or doc_type not in DOC_TYPE_MODELS:
        raise ValidationError("docType must be 'memory', 'task', or 'review'")
    if not document.get("narrative"):
        raise ValidationError("narrative is required")

    # Validate against Pydantic model
    model_cls = DOC_TYPE_MODELS[doc_type]
    try:
        validated = model_cls.model_validate(document)
    except PydanticValidationError as e:
        details = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        raise ValidationError(f"Validation error: {'; '.join(details)}")

    # Server-generated fields
    doc = validated.model_dump()
    doc["id"] = f"{doc_type}:{uuid.uuid4()}"
    doc["userId"] = user_id
    now = _now_iso()
    doc["createdAt"] = now
    doc["updatedAt"] = now

    # Generate embedding
    doc["embedding"] = generate_embedding(doc)

    cosmos_client.create_item(doc)
    return {"status": "created", "id": doc["id"], "docType": doc_type}


def read_document(user_id: str, doc_id: str) -> dict:
    """Read a document by ID."""
    doc = cosmos_client.read_item(doc_id, user_id)
    return _strip(doc)


def query_documents(
    user_id: str,
    doc_type: str | None = None,
    filters: dict | None = None,
    sort_by: str = "createdAt",
    sort_desc: bool = True,
    limit: int = 50,
) -> dict:
    """Query documents with structured filters."""
    limit = max(1, min(limit, 100))

    conditions = ["c.userId = @userId"]
    params: list[dict] = [{"name": "@userId", "value": user_id}]
    param_idx = 0

    if doc_type:
        conditions.append("c.docType = @docType")
        params.append({"name": "@docType", "value": doc_type})

    if filters:
        for key, value in filters.items():
            if value is None:
                conditions.append(f"(NOT IS_DEFINED(c.{key}) OR IS_NULL(c.{key}))")
            else:
                param_name = f"@p{param_idx}"
                conditions.append(f"c.{key} = {param_name}")
                params.append({"name": param_name, "value": value})
                param_idx += 1

    where = " AND ".join(conditions)
    direction = "DESC" if sort_desc else "ASC"
    sql = f"SELECT * FROM c WHERE {where} ORDER BY c.{sort_by} {direction}"

    results = cosmos_client.query_items(sql, params, partition_key=user_id, max_item_count=limit)
    stripped = [_strip(doc) for doc in results]
    return {"results": stripped, "total": len(stripped)}


def search_documents(
    user_id: str,
    query_text: str,
    doc_type: str | None = None,
    top_k: int = 5,
) -> dict:
    """Vector similarity search."""
    from openbrain.embedding import embed_text

    top_k = max(1, min(top_k, 20))
    query_vector = embed_text(query_text)

    results = cosmos_client.vector_search(query_vector, user_id, doc_type, top_k)

    # Pass through Cosmos VectorDistance score and log hypotheticalQueries for search quality
    processed = []
    for doc in results:
        score = doc.pop("score", 0)

        hyp_queries = doc.get("hypotheticalQueries", [])
        if hyp_queries:
            logger.debug(
                f"Search match: query='{query_text[:50]}', hypotheticalQueries={hyp_queries}"
            )

        stripped = _strip(doc, extra_strip={"hypotheticalQueries"})
        stripped["score"] = round(score, 4)
        processed.append(stripped)

    return {"results": processed, "query": query_text, "total": len(processed)}


def update_document(user_id: str, doc_id: str, updates: dict) -> dict:
    """Update fields on an existing document using dot-path deep merge."""
    doc = cosmos_client.read_item(doc_id, user_id)

    # Strip immutable fields from updates
    clean_updates = {k: v for k, v in updates.items() if k not in IMMUTABLE_FIELDS}

    # Check for recurring task completion
    is_completing_recurring = (
        clean_updates.get("state.status") == "done"
        and doc.get("state", {}).get("isRecurring")
        and doc.get("state", {}).get("recurrenceDays")
        and doc.get("state", {}).get("status") != "done"  # not already done
    )

    # Apply dot-path updates
    for key, value in clean_updates.items():
        parts = key.split(".")
        target = doc
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    # Handle recurring task completion
    if is_completing_recurring:
        state = doc.get("state", {})
        now = datetime.now(timezone.utc)
        recurrence_days = state.get("recurrenceDays", 0)

        state["completionCount"] = state.get("completionCount", 0) + 1
        state["lastCompletedAt"] = now.isoformat()
        state["dueDate"] = (now + timedelta(days=recurrence_days)).isoformat()
        state["status"] = "open"
        state["progressNotes"] = state.get("progressNotes", []) + [
            f"Completed on {now.strftime('%Y-%m-%d')}"
        ]
        doc["state"] = state

    # Re-embed if narrative or hypotheticalQueries changed
    needs_reembed = any(
        k == "narrative" or k == "hypotheticalQueries" or k.startswith("hypotheticalQueries.")
        for k in clean_updates
    )
    if needs_reembed:
        doc["embedding"] = generate_embedding(doc)

    doc["updatedAt"] = _now_iso()
    cosmos_client.upsert_item(doc)
    return {"id": doc_id, "status": "updated", "updatedAt": doc["updatedAt"]}


def delete_document(user_id: str, doc_id: str) -> dict:
    """Hard delete a document."""
    cosmos_client.delete_item(doc_id, user_id)
    return {"id": doc_id, "status": "deleted"}


def raw_query_documents(user_id: str, sql: str, parameters: list[dict] | None = None) -> dict:
    """Execute raw Cosmos SQL with injected userId."""
    params = list(parameters or [])
    params.append({"name": "@userId", "value": user_id})

    results = cosmos_client.query_items(sql, params, partition_key=user_id, max_item_count=100)
    stripped = [_strip(doc) for doc in results]
    return {"results": stripped, "total": len(stripped)}
