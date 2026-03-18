"""Document service: CRUD, query, search, and update operations."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import ValidationError as PydanticValidationError

from openbrain import cosmos_client
from openbrain.models.goal import GoalDocument
from openbrain.models.idea import IdeaDocument
from openbrain.models.memory import MemoryDocument
from openbrain.models.misc import MiscDocument
from openbrain.models.task import TaskDocument
from openbrain.models.user_settings import UserSettingsDocument
from openbrain.services.embedding_service import document_requires_embedding, generate_embedding
from openbrain.utils.errors import DocumentNotFoundError, ValidationError

logger = logging.getLogger("openbrain")

DOC_TYPE_MODELS = {
    "memory": MemoryDocument,
    "idea": IdeaDocument,
    "task": TaskDocument,
    "goal": GoalDocument,
    "misc": MiscDocument,
    "userSettings": UserSettingsDocument,
}
QUERY_ONLY_DOC_TYPES = {"task", "goal", "misc", "userSettings"}
SEARCHABLE_DOC_TYPES = {"memory", "idea"}
IMMUTABLE_FIELDS = {"id", "userId", "docType", "createdAt", "embedding"}
STRIP_FIELDS = {"embedding", "rawText", "_rid", "_self", "_etag", "_attachments", "_ts"}
SEARCH_STRIP_FIELDS = STRIP_FIELDS | {"hypotheticalQueries"}
WRITE_REQUIRES_NARRATIVE = {"memory", "idea", "task", "goal", "misc"}
READ_ONLY_SQL_PATTERN = re.compile(r"\b(insert|update|delete|replace|upsert|create|drop|alter)\b", re.IGNORECASE)


def _strip(doc: dict, extra_strip: set[str] | None = None) -> dict:
    """Remove internal and sensitive fields from a document."""

    return {k: v for k, v in doc.items() if k not in (STRIP_FIELDS | (extra_strip or set()))}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_doc_type(doc_type: str | None) -> str:
    if not doc_type or doc_type not in DOC_TYPE_MODELS:
        supported = ", ".join(sorted(DOC_TYPE_MODELS))
        raise ValidationError(f"docType must be one of: {supported}")
    return doc_type


def _normalize_tags(document: dict) -> None:
    if "contextTags" not in document or document["contextTags"] is None:
        return

    tags: list[str] = []
    seen: set[str] = set()
    for tag in document["contextTags"]:
        cleaned = str(tag).strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered not in seen:
            seen.add(lowered)
            tags.append(lowered)
    document["contextTags"] = tags


def _model_validate(doc_type: str, payload: dict):
    model_cls = DOC_TYPE_MODELS[doc_type]
    try:
        return model_cls.model_validate(payload)
    except PydanticValidationError as exc:
        details = []
        for err in exc.errors():
            loc = ".".join(str(part) for part in err["loc"])
            details.append(f"{loc}: {err['msg']}")
        raise ValidationError("; ".join(details)) from exc


def _build_document_id(doc_type: str, user_id: str) -> str:
    if doc_type == "userSettings":
        return f"userSettings:{user_id}"
    return f"{doc_type}:{uuid.uuid4()}"


def write_document(user_id: str, document: dict) -> dict:
    """Validate, generate server fields, and persist a new document."""

    doc_type = _validate_doc_type(document.get("docType"))
    if doc_type in WRITE_REQUIRES_NARRATIVE and not str(document.get("narrative", "")).strip():
        raise ValidationError("narrative is required")

    payload = dict(document)
    _normalize_tags(payload)

    validated = _model_validate(doc_type, payload)
    doc = validated.model_dump()
    now = _now_iso()
    doc["id"] = _build_document_id(doc_type, user_id)
    doc["userId"] = user_id
    doc["createdAt"] = now
    doc["updatedAt"] = now
    if document_requires_embedding(doc):
        doc["embedding"] = generate_embedding(doc)

    if doc_type == "userSettings":
        cosmos_client.upsert_item(doc)
    else:
        cosmos_client.create_item(doc)
    return {"status": "created", "id": doc["id"], "docType": doc_type}


def read_document(user_id: str, doc_id: str) -> dict:
    """Read a single document and sanitize it for clients."""

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
    """Query documents with structured filters and dot-path support."""

    limit = max(1, min(limit, 100))

    conditions = ["c.userId = @userId"]
    params: list[dict] = [{"name": "@userId", "value": user_id}]
    param_idx = 0

    if doc_type:
        _validate_doc_type(doc_type)
        conditions.append("c.docType = @docType")
        params.append({"name": "@docType", "value": doc_type})

    for key, value in (filters or {}).items():
        if value is None:
            conditions.append(f"(NOT IS_DEFINED(c.{key}) OR IS_NULL(c.{key}))")
            continue
        param_name = f"@p{param_idx}"
        conditions.append(f"c.{key} = {param_name}")
        params.append({"name": param_name, "value": value})
        param_idx += 1

    where_clause = " AND ".join(conditions)
    direction = "DESC" if sort_desc else "ASC"
    sql = f"SELECT TOP @limit * FROM c WHERE {where_clause} ORDER BY c.{sort_by} {direction}"
    params.append({"name": "@limit", "value": limit})

    results = cosmos_client.query_items(sql, params, partition_key=user_id, max_item_count=limit)
    stripped = [_strip(doc) for doc in results]
    return {"results": stripped, "total": len(stripped)}


def search_documents(user_id: str, query_text: str, doc_type: str | None = None, top_k: int = 5) -> dict:
    """Execute semantic search over embedded documents."""

    from openbrain.embedding import embed_text

    query_text = query_text.strip()
    if not query_text:
        raise ValidationError("query is required")

    if doc_type:
        _validate_doc_type(doc_type)
        if doc_type not in SEARCHABLE_DOC_TYPES:
            raise ValidationError("search only supports embedded document types: memory, idea")

    top_k = max(1, min(top_k, 20))
    query_vector = embed_text(query_text)
    results = cosmos_client.vector_search(query_vector, user_id, doc_type, top_k)

    processed = []
    for doc in results:
        score = doc.pop("score", None)
        hyp_queries = doc.get("hypotheticalQueries", [])
        if hyp_queries:
            logger.debug("Search match hypotheticalQueries=%s", hyp_queries)
        stripped = _strip(doc, extra_strip={"hypotheticalQueries"})
        stripped["score"] = score
        processed.append(stripped)

    return {"results": processed, "query": query_text, "total": len(processed)}


def _apply_dot_path_updates(document: dict, updates: dict) -> None:
    for key, value in updates.items():
        target = document
        parts = key.split(".")
        for part in parts[:-1]:
            if part not in target or not isinstance(target[part], dict):
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value


def _should_apply_recurring_task_completion(document: dict, updates: dict) -> bool:
    if document.get("docType") != "task":
        return False
    if updates.get("state.status") != "done":
        return False

    state = document.get("state", {})
    return (
        document.get("taskType") == "recurringTask"
        and state.get("isRecurring")
        and state.get("recurrenceDays")
        and state.get("status") != "done"
    )


def _apply_recurring_task_completion(document: dict) -> None:
    state = document.get("state", {})

    now = datetime.now(timezone.utc)
    recurrence_days = state["recurrenceDays"]
    state["completionCount"] = state.get("completionCount", 0) + 1
    state["lastCompletedAt"] = now.isoformat()
    state["dueDate"] = (now + timedelta(days=recurrence_days)).isoformat()
    state["status"] = "open"
    state["progressNotes"] = list(state.get("progressNotes", [])) + [
        f"Completed on {now.strftime('%Y-%m-%d')}"
    ]
    document["state"] = state


def update_document(user_id: str, doc_id: str, updates: dict) -> dict:
    """Update a document and revalidate it before persistence."""

    doc = cosmos_client.read_item(doc_id, user_id)
    clean_updates = {k: v for k, v in updates.items() if k not in IMMUTABLE_FIELDS}

    if not clean_updates:
        return {"id": doc_id, "status": "updated", "updatedAt": doc.get("updatedAt", _now_iso())}

    should_complete_recurring = _should_apply_recurring_task_completion(doc, clean_updates)
    _apply_dot_path_updates(doc, clean_updates)
    if should_complete_recurring:
        _apply_recurring_task_completion(doc)
    _normalize_tags(doc)

    if document_requires_embedding(doc) and any(
        key == "narrative" or key == "hypotheticalQueries" or key.startswith("hypotheticalQueries.")
        for key in clean_updates
    ):
        doc["embedding"] = generate_embedding(doc)

    doc["updatedAt"] = _now_iso()
    validated = _model_validate(doc["docType"], doc)
    upsert_doc = validated.model_dump()
    if "embedding" in doc:
        upsert_doc["embedding"] = doc.get("embedding", [])

    cosmos_client.upsert_item(upsert_doc)
    return {"id": doc_id, "status": "updated", "updatedAt": upsert_doc["updatedAt"]}


def delete_document(user_id: str, doc_id: str) -> dict:
    """Delete a document by ID and partition key."""

    cosmos_client.delete_item(doc_id, user_id)
    return {"id": doc_id, "status": "deleted"}


def raw_query_documents(user_id: str, sql: str, parameters: list[dict] | None = None) -> dict:
    """Execute a read-only raw Cosmos query with user partition enforcement."""

    if READ_ONLY_SQL_PATTERN.search(sql):
        raise ValidationError("raw_query only supports read-only Cosmos SQL")
    if "c.userId = @userId" not in sql and "c.userid = @userid" not in sql.lower():
        raise ValidationError("raw_query SQL must include c.userId = @userId in the WHERE clause")

    params = list(parameters or [])
    if any(param.get("name") == "@userId" for param in params):
        raise ValidationError("raw_query parameters must not include @userId; the server injects it")
    params.append({"name": "@userId", "value": user_id})

    results = cosmos_client.query_items(sql, params, partition_key=user_id, max_item_count=100)
    stripped = [_strip(doc) for doc in results[:100]]
    return {"results": stripped, "total": len(stripped)}
