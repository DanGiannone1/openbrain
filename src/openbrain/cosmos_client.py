"""Cosmos DB client helpers for Open Brain."""

from __future__ import annotations

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from openbrain.config import Config
from openbrain.utils.errors import CosmosDBError, DocumentNotFoundError

_cosmos_client: CosmosClient | None = None
_database: DatabaseProxy | None = None
_container: ContainerProxy | None = None

VECTOR_SEARCH_FIELDS = (
    "c.id, c.userId, c.docType, c.narrative, c.rawText, c.contextTags, c.aiMetadata, "
    "c.createdAt, c.updatedAt, c.goalId, c.taskType, c.state, c.hypotheticalQueries"
)


def get_cosmos_client() -> CosmosClient:
    """Return a singleton Cosmos client."""

    global _cosmos_client
    if _cosmos_client is None:
        try:
            _cosmos_client = CosmosClient(url=Config.COSMOS_HOST, credential=Config.COSMOS_KEY)
        except Exception as exc:
            raise CosmosDBError(f"Failed to initialize Cosmos client: {exc}") from exc
    return _cosmos_client


def get_database() -> DatabaseProxy:
    """Return the configured database client."""

    global _database
    if _database is None:
        try:
            _database = get_cosmos_client().get_database_client(Config.COSMOS_DATABASE)
        except Exception as exc:
            raise CosmosDBError(f"Failed to access database '{Config.COSMOS_DATABASE}': {exc}") from exc
    return _database


def get_container() -> ContainerProxy:
    """Return the configured container client."""

    global _container
    if _container is None:
        try:
            _container = get_database().get_container_client(Config.COSMOS_CONTAINER)
        except Exception as exc:
            raise CosmosDBError(f"Failed to access container '{Config.COSMOS_CONTAINER}': {exc}") from exc
    return _container


def create_item(item: dict) -> dict:
    """Create a new item in Cosmos."""

    try:
        return get_container().create_item(body=item)
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Failed to create item: {exc.message} (status {exc.status_code})") from exc


def read_item(item_id: str, partition_key: str) -> dict:
    """Read a single item by ID and partition key."""

    try:
        return get_container().read_item(item=item_id, partition_key=partition_key)
    except CosmosResourceNotFoundError as exc:
        raise DocumentNotFoundError(f"Document '{item_id}' not found") from exc
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Failed to read item: {exc.message} (status {exc.status_code})") from exc


def upsert_item(item: dict) -> dict:
    """Upsert an item in Cosmos."""

    try:
        return get_container().upsert_item(body=item)
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Failed to upsert item: {exc.message} (status {exc.status_code})") from exc


def delete_item(item_id: str, partition_key: str) -> None:
    """Delete an item by ID and partition key."""

    try:
        get_container().delete_item(item=item_id, partition_key=partition_key)
    except CosmosResourceNotFoundError as exc:
        raise DocumentNotFoundError(f"Document '{item_id}' not found") from exc
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Failed to delete item: {exc.message} (status {exc.status_code})") from exc


def query_items(
    query: str,
    parameters: list[dict] | None = None,
    partition_key: str | None = None,
    max_item_count: int = 100,
) -> list[dict]:
    """Execute a Cosmos SQL query and materialize the results."""

    try:
        query_kwargs: dict = {
            "query": query,
            "enable_cross_partition_query": partition_key is None,
            "max_item_count": max_item_count,
        }
        if parameters:
            query_kwargs["parameters"] = parameters
        if partition_key:
            query_kwargs["partition_key"] = partition_key
        return list(get_container().query_items(**query_kwargs))
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Query failed: {exc.message} (status {exc.status_code})") from exc


def vector_search(query_vector: list[float], user_id: str, doc_type: str | None = None, top_k: int = 5) -> list[dict]:
    """Execute vector similarity search over embedded document types."""

    sql = (
        f"SELECT TOP @topK {VECTOR_SEARCH_FIELDS}, "
        "VectorDistance(c.embedding, @queryVector) AS score "
        "FROM c WHERE c.userId = @userId "
    )
    params = [
        {"name": "@topK", "value": top_k},
        {"name": "@queryVector", "value": query_vector},
        {"name": "@userId", "value": user_id},
    ]

    if doc_type:
        sql += "AND c.docType = @docType "
        params.append({"name": "@docType", "value": doc_type})
    else:
        sql += "AND (c.docType = 'memory' OR c.docType = 'idea') "

    sql += "ORDER BY VectorDistance(c.embedding, @queryVector) DESC"

    try:
        return list(
            get_container().query_items(
                query=sql,
                parameters=params,
                partition_key=user_id,
                max_item_count=top_k,
            )
        )
    except CosmosHttpResponseError as exc:
        raise CosmosDBError(f"Vector search failed: {exc.message} (status {exc.status_code})") from exc
