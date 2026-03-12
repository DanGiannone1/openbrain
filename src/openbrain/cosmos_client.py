"""Cosmos DB client singleton for Open Brain MCP server."""

from azure.cosmos import CosmosClient, ContainerProxy, DatabaseProxy, PartitionKey
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from openbrain.config import Config
from openbrain.utils.errors import CosmosDBError, DocumentNotFoundError

_cosmos_client: CosmosClient | None = None
_database: DatabaseProxy | None = None
_container: ContainerProxy | None = None


def get_cosmos_client() -> CosmosClient:
    global _cosmos_client
    if _cosmos_client is None:
        try:
            _cosmos_client = CosmosClient(url=Config.COSMOS_HOST, credential=Config.COSMOS_KEY)
        except Exception as e:
            raise CosmosDBError(f"Failed to initialize Cosmos client: {e}") from e
    return _cosmos_client


def get_database() -> DatabaseProxy:
    global _database
    if _database is None:
        try:
            _database = get_cosmos_client().get_database_client(Config.COSMOS_DATABASE)
        except Exception as e:
            raise CosmosDBError(f"Failed to access database '{Config.COSMOS_DATABASE}': {e}") from e
    return _database


def get_container() -> ContainerProxy:
    global _container
    if _container is None:
        try:
            _container = get_database().get_container_client(Config.COSMOS_CONTAINER)
        except Exception as e:
            raise CosmosDBError(f"Failed to access container '{Config.COSMOS_CONTAINER}': {e}") from e
    return _container


def create_item(item: dict) -> dict:
    try:
        container = get_container()
        return container.create_item(body=item)
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Failed to create item: {e.message} (status {e.status_code})") from e


def read_item(item_id: str, partition_key: str) -> dict:
    try:
        container = get_container()
        return container.read_item(item=item_id, partition_key=partition_key)
    except CosmosResourceNotFoundError:
        raise DocumentNotFoundError(f"Document '{item_id}' not found")
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Failed to read item: {e.message} (status {e.status_code})") from e


def upsert_item(item: dict) -> dict:
    try:
        container = get_container()
        return container.upsert_item(body=item)
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Failed to upsert item: {e.message} (status {e.status_code})") from e


def delete_item(item_id: str, partition_key: str) -> None:
    try:
        container = get_container()
        container.delete_item(item=item_id, partition_key=partition_key)
    except CosmosResourceNotFoundError:
        raise DocumentNotFoundError(f"Document '{item_id}' not found")
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Failed to delete item: {e.message} (status {e.status_code})") from e


def query_items(
    query: str,
    parameters: list[dict] | None = None,
    partition_key: str | None = None,
    max_item_count: int = 100,
) -> list[dict]:
    try:
        container = get_container()
        query_kwargs: dict = {
            "query": query,
            "enable_cross_partition_query": partition_key is None,
            "max_item_count": max_item_count,
        }
        if parameters:
            query_kwargs["parameters"] = parameters
        if partition_key:
            query_kwargs["partition_key"] = partition_key
        return list(container.query_items(**query_kwargs))
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Query failed: {e.message} (status {e.status_code})") from e


def vector_search(
    query_vector: list[float],
    user_id: str,
    doc_type: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """Execute vector similarity search using Cosmos DB VectorDistance."""
    fields = (
        "c.id, c.docType, c.narrative, c.contextTags, c.aiMetadata, c.createdAt, c.updatedAt, "
        "c.memoryType, c.taskType, c.state, c.supersededBy, c.triageAttempt, c.resolvedAt, c.resolution, "
        "c.hypotheticalQueries"
    )
    sql = (
        f"SELECT TOP @topK {fields}, "
        "VectorDistance(c.embedding, @queryVector) AS score "
        "FROM c WHERE c.userId = @userId"
    )
    params: list[dict] = [
        {"name": "@topK", "value": top_k},
        {"name": "@queryVector", "value": query_vector},
        {"name": "@userId", "value": user_id},
    ]
    if doc_type:
        sql += " AND c.docType = @docType"
        params.append({"name": "@docType", "value": doc_type})

    sql += " ORDER BY VectorDistance(c.embedding, @queryVector)"

    try:
        container = get_container()
        return list(container.query_items(
            query=sql,
            parameters=params,
            partition_key=user_id,
        ))
    except CosmosHttpResponseError as e:
        raise CosmosDBError(f"Vector search failed: {e.message} (status {e.status_code})") from e
