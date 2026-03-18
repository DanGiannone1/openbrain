"""Tests for the MCP tool layer (tools.py).

These tests verify that each tool function correctly delegates to
document_service, handles errors, and formats responses.
"""

from __future__ import annotations

import sys
from copy import deepcopy
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# Patch CurrentHeaders before importing tools.py since the installed
# fastmcp version may not export it.
_deps_mod = sys.modules.get("fastmcp.server.dependencies")
if _deps_mod is None:
    _deps_mod = ModuleType("fastmcp.server.dependencies")
    sys.modules["fastmcp.server.dependencies"] = _deps_mod
if not hasattr(_deps_mod, "CurrentHeaders"):
    _deps_mod.CurrentHeaders = MagicMock  # type: ignore[attr-defined]

from openbrain.tools.tools import _error, register_tools  # noqa: E402
from openbrain.utils.errors import (  # noqa: E402
    AuthenticationError,
    CosmosDBError,
    DocumentNotFoundError,
    EmbeddingError,
    ValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeMCP:
    """Minimal stand-in for the FastMCP server object used by register_tools."""

    def __init__(self):
        self.tools: dict[str, callable] = {}

    def tool(self):
        def decorator(fn):
            self.tools[fn.__name__] = fn
            return fn
        return decorator


def _make_mcp() -> FakeMCP:
    """Register tools and return the fake MCP with tools dict populated."""
    mcp = FakeMCP()
    with patch("openbrain.tools.tools.log_tool_call", lambda fn: fn):
        register_tools(mcp)
    return mcp


DEV_USER = "dev-user"
AUTH_HEADERS = {"authorization": "Bearer test-token"}


class FakeCosmosBackend:
    """In-memory Cosmos backend reused from test_scenarios."""

    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}

    def create_item(self, item: dict) -> dict:
        self.items[(item["id"], item["userId"])] = deepcopy(item)
        return deepcopy(item)

    def read_item(self, item_id: str, partition_key: str) -> dict:
        key = (item_id, partition_key)
        if key not in self.items:
            raise DocumentNotFoundError(f"Document '{item_id}' not found")
        return deepcopy(self.items[key])

    def upsert_item(self, item: dict) -> dict:
        self.items[(item["id"], item["userId"])] = deepcopy(item)
        return deepcopy(item)

    def delete_item(self, item_id: str, partition_key: str) -> None:
        key = (item_id, partition_key)
        if key not in self.items:
            raise DocumentNotFoundError(f"Document '{item_id}' not found")
        self.items.pop(key)

    def query_items(self, _sql, parameters=None, partition_key=None, max_item_count=100):
        params = {p["name"]: p["value"] for p in (parameters or [])}
        results = []
        for (_, uid), item in self.items.items():
            if partition_key and uid != partition_key:
                continue
            if "@docType" in params and item.get("docType") != params["@docType"]:
                continue
            results.append(deepcopy(item))
        return results[:max_item_count]

    def vector_search(self, _qv, user_id, doc_type=None, top_k=5):
        results = []
        for (_, uid), item in self.items.items():
            if uid != user_id:
                continue
            if item.get("docType") not in {"memory", "idea"}:
                continue
            if doc_type and item.get("docType") != doc_type:
                continue
            doc = deepcopy(item)
            doc["score"] = 0.95
            results.append(doc)
        return results[:top_k]


@pytest.fixture()
def mcp():
    return _make_mcp()


# ---------------------------------------------------------------------------
# _error helper
# ---------------------------------------------------------------------------

class TestErrorHelper:
    def test_error_message_only(self):
        result = _error("Something went wrong")
        assert result == {"error": "Something went wrong"}

    def test_error_with_details(self):
        result = _error("Validation error", ["field: required"])
        assert result == {"error": "Validation error", "details": ["field: required"]}

    def test_error_without_details_omits_key(self):
        result = _error("Oops", None)
        assert "details" not in result

    def test_error_empty_details_omits_key(self):
        result = _error("Oops", [])
        assert "details" not in result


# ---------------------------------------------------------------------------
# write tool
# ---------------------------------------------------------------------------

class TestWriteTool:
    @patch("openbrain.services.document_service.generate_embedding", return_value=[0.1])
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_write_success(self, _auth, mock_cosmos, _embed, mcp):
        result = mcp.tools["write"](
            document={"docType": "memory", "narrative": "Test note"},
            headers=AUTH_HEADERS,
        )
        assert result["status"] == "created"
        assert result["docType"] == "memory"

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("bad token"))
    def test_write_auth_error(self, _auth, mcp):
        result = mcp.tools["write"](document={"docType": "memory"}, headers={})
        assert result["error"] == "bad token"

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_write_validation_error(self, _auth, mcp):
        result = mcp.tools["write"](
            document={"docType": "invalid_type", "narrative": "x"},
            headers=AUTH_HEADERS,
        )
        assert result["error"] == "Validation error"
        assert "details" in result

    @patch("openbrain.services.document_service.generate_embedding", side_effect=EmbeddingError("down"))
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_write_embedding_error(self, _auth, _embed, mcp):
        result = mcp.tools["write"](
            document={"docType": "memory", "narrative": "Test"},
            headers=AUTH_HEADERS,
        )
        assert result["error"] == "Embedding service unavailable"

    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.services.document_service.generate_embedding", return_value=[])
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_write_cosmos_error(self, _auth, _embed, mock_cosmos, mcp):
        mock_cosmos.create_item.side_effect = CosmosDBError("connection lost")
        result = mcp.tools["write"](
            document={"docType": "misc", "narrative": "Test"},
            headers=AUTH_HEADERS,
        )
        assert "Database error" in result["error"]


# ---------------------------------------------------------------------------
# read tool
# ---------------------------------------------------------------------------

class TestReadTool:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_read_success(self, _auth, mock_cosmos, mcp):
        mock_cosmos.read_item.return_value = {
            "id": "memory:1",
            "userId": DEV_USER,
            "docType": "memory",
            "narrative": "Test",
            "embedding": [0.1],
            "rawText": "test",
        }
        result = mcp.tools["read"](id="memory:1", headers=AUTH_HEADERS)
        assert result["id"] == "memory:1"
        assert "embedding" not in result
        assert "rawText" not in result

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    @patch(
        "openbrain.services.document_service.cosmos_client.read_item",
        side_effect=DocumentNotFoundError("not found"),
    )
    def test_read_not_found(self, _cosmos, _auth, mcp):
        result = mcp.tools["read"](id="memory:999", headers=AUTH_HEADERS)
        assert "not found" in result["error"]

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("denied"))
    def test_read_auth_error(self, _auth, mcp):
        result = mcp.tools["read"](id="memory:1", headers={})
        assert result["error"] == "denied"


# ---------------------------------------------------------------------------
# query tool
# ---------------------------------------------------------------------------

class TestQueryTool:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_query_success(self, _auth, mock_cosmos, mcp):
        mock_cosmos.query_items.return_value = [
            {"id": "task:1", "userId": DEV_USER, "docType": "task", "narrative": "Do it"}
        ]
        result = mcp.tools["query"](docType="task", headers=AUTH_HEADERS)
        assert result["total"] == 1
        assert result["results"][0]["id"] == "task:1"

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_query_invalid_doc_type(self, _auth, mcp):
        result = mcp.tools["query"](docType="badtype", headers=AUTH_HEADERS)
        assert result["error"] == "Validation error"

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("nope"))
    def test_query_auth_error(self, _auth, mcp):
        result = mcp.tools["query"](headers={})
        assert result["error"] == "nope"


# ---------------------------------------------------------------------------
# search tool
# ---------------------------------------------------------------------------

class TestSearchTool:
    @patch("openbrain.embedding.embed_text", return_value=[0.1, 0.2])
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_search_success(self, _auth, mock_cosmos, _embed, mcp):
        mock_cosmos.vector_search.return_value = [
            {"id": "memory:1", "docType": "memory", "narrative": "Router pw", "score": 0.9}
        ]
        result = mcp.tools["search"](query="router", headers=AUTH_HEADERS)
        assert result["total"] == 1
        assert result["results"][0]["score"] == 0.9

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_search_query_only_doc_type(self, _auth, mcp):
        result = mcp.tools["search"](query="find tasks", docType="task", headers=AUTH_HEADERS)
        assert result["error"] == "Validation error"

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("bad"))
    def test_search_auth_error(self, _auth, mcp):
        result = mcp.tools["search"](query="test", headers={})
        assert result["error"] == "bad"

    @patch("openbrain.embedding.embed_text", side_effect=EmbeddingError("down"))
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_search_embedding_error(self, _auth, _embed, mcp):
        result = mcp.tools["search"](query="test", docType="memory", headers=AUTH_HEADERS)
        assert result["error"] == "Embedding service unavailable"


# ---------------------------------------------------------------------------
# update tool
# ---------------------------------------------------------------------------

class TestUpdateTool:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_update_success(self, _auth, mock_cosmos, mcp):
        mock_cosmos.read_item.return_value = {
            "id": "misc:1",
            "userId": DEV_USER,
            "docType": "misc",
            "narrative": "Old",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
        result = mcp.tools["update"](
            id="misc:1", updates={"narrative": "New"}, headers=AUTH_HEADERS
        )
        assert result["status"] == "updated"

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    @patch(
        "openbrain.services.document_service.cosmos_client.read_item",
        side_effect=DocumentNotFoundError("gone"),
    )
    def test_update_not_found(self, _cosmos, _auth, mcp):
        result = mcp.tools["update"](
            id="misc:999", updates={"narrative": "x"}, headers=AUTH_HEADERS
        )
        assert "not found" in result["error"]

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("no"))
    def test_update_auth_error(self, _auth, mcp):
        result = mcp.tools["update"](id="misc:1", updates={}, headers={})
        assert result["error"] == "no"


# ---------------------------------------------------------------------------
# delete tool
# ---------------------------------------------------------------------------

class TestDeleteTool:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_delete_success(self, _auth, mock_cosmos, mcp):
        result = mcp.tools["delete"](id="misc:1", headers=AUTH_HEADERS)
        assert result["status"] == "deleted"
        assert result["id"] == "misc:1"

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    @patch(
        "openbrain.services.document_service.cosmos_client.delete_item",
        side_effect=DocumentNotFoundError("gone"),
    )
    def test_delete_not_found(self, _cosmos, _auth, mcp):
        result = mcp.tools["delete"](id="misc:999", headers=AUTH_HEADERS)
        assert "not found" in result["error"]

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("denied"))
    def test_delete_auth_error(self, _auth, mcp):
        result = mcp.tools["delete"](id="misc:1", headers={})
        assert result["error"] == "denied"

    @patch("openbrain.services.document_service.cosmos_client.delete_item", side_effect=CosmosDBError("timeout"))
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_delete_cosmos_error(self, _auth, _cosmos, mcp):
        result = mcp.tools["delete"](id="misc:1", headers=AUTH_HEADERS)
        assert "Database error" in result["error"]


# ---------------------------------------------------------------------------
# raw_query tool
# ---------------------------------------------------------------------------

class TestRawQueryTool:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_raw_query_success(self, _auth, mock_cosmos, mcp):
        mock_cosmos.query_items.return_value = [
            {"id": "memory:1", "userId": DEV_USER, "docType": "memory", "narrative": "Hi"}
        ]
        result = mcp.tools["raw_query"](
            sql="SELECT * FROM c WHERE c.userId = @userId",
            headers=AUTH_HEADERS,
        )
        assert result["total"] == 1

    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_raw_query_rejects_mutation(self, _auth, mcp):
        result = mcp.tools["raw_query"](
            sql="DELETE FROM c WHERE c.userId = @userId",
            headers=AUTH_HEADERS,
        )
        assert result["error"] == "Validation error"

    @patch("openbrain.tools.tools.get_current_user", side_effect=AuthenticationError("no"))
    def test_raw_query_auth_error(self, _auth, mcp):
        result = mcp.tools["raw_query"](sql="SELECT 1", headers={})
        assert result["error"] == "no"


# ---------------------------------------------------------------------------
# Integration: tool layer with FakeCosmosBackend
# ---------------------------------------------------------------------------

class TestToolIntegration:
    """End-to-end tests through the tool layer using the fake backend."""

    @patch("openbrain.services.document_service.generate_embedding", return_value=[0.1])
    @patch("openbrain.embedding.embed_text", return_value=[0.1])
    @patch("openbrain.tools.tools.get_current_user", return_value=DEV_USER)
    def test_write_read_update_delete_lifecycle(self, _auth, _search_embed, _gen_embed, mcp):
        backend = FakeCosmosBackend()
        with patch("openbrain.services.document_service.cosmos_client", backend):
            # Write
            created = mcp.tools["write"](
                document={"docType": "memory", "narrative": "My secret note"},
                headers=AUTH_HEADERS,
            )
            assert created["status"] == "created"
            doc_id = created["id"]

            # Read
            doc = mcp.tools["read"](id=doc_id, headers=AUTH_HEADERS)
            assert doc["narrative"] == "My secret note"
            assert "embedding" not in doc

            # Update
            updated = mcp.tools["update"](
                id=doc_id,
                updates={"narrative": "Updated note"},
                headers=AUTH_HEADERS,
            )
            assert updated["status"] == "updated"

            # Query
            queried = mcp.tools["query"](docType="memory", headers=AUTH_HEADERS)
            assert queried["total"] == 1

            # Search
            searched = mcp.tools["search"](query="secret", docType="memory", headers=AUTH_HEADERS)
            assert searched["total"] == 1

            # Raw query
            raw = mcp.tools["raw_query"](
                sql="SELECT * FROM c WHERE c.userId = @userId",
                headers=AUTH_HEADERS,
            )
            assert raw["total"] == 1

            # Delete
            deleted = mcp.tools["delete"](id=doc_id, headers=AUTH_HEADERS)
            assert deleted["status"] == "deleted"

            # Confirm deleted
            read_after = mcp.tools["read"](id=doc_id, headers=AUTH_HEADERS)
            assert "not found" in read_after["error"]
