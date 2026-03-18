"""Tests for document service behavior."""

from unittest.mock import patch

import pytest

from openbrain.services.document_service import (
    _strip,
    query_documents,
    raw_query_documents,
    search_documents,
    update_document,
    write_document,
)
from openbrain.utils.errors import ValidationError


class TestStripFields:
    def test_strips_internal_fields(self):
        doc = {
            "id": "memory:123",
            "narrative": "test",
            "embedding": [0.1, 0.2],
            "rawText": "original text",
            "_rid": "abc",
            "_self": "def",
            "_etag": "ghi",
            "_attachments": "jkl",
            "_ts": 123456,
        }
        result = _strip(doc)
        assert result["id"] == "memory:123"
        assert "embedding" not in result
        assert "rawText" not in result


class TestWriteDocument:
    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.services.document_service.generate_embedding", return_value=[0.1, 0.2])
    def test_embedded_doc_gets_embedding(self, _mock_embed, mock_cosmos):
        result = write_document("dev-user", {"docType": "memory", "narrative": "Router password"})
        created = mock_cosmos.create_item.call_args[0][0]
        assert result["status"] == "created"
        assert created["embedding"] == [0.1, 0.2]
        assert created["userId"] == "dev-user"

    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.services.document_service.generate_embedding", return_value=[])
    def test_user_settings_get_stable_id(self, _mock_embed, mock_cosmos):
        result = write_document(
            "dev-user",
            {"docType": "userSettings", "tagTaxonomy": ["personal", "soligence", "microsoft"]},
        )
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert result["id"] == "userSettings:dev-user"
        assert upserted["id"] == "userSettings:dev-user"
        assert upserted["tagTaxonomy"] == ["personal", "soligence", "microsoft"]

    def test_unknown_doc_type_fails(self):
        with pytest.raises(ValidationError):
            write_document("dev-user", {"docType": "review", "narrative": "old type"})


class TestDotPathMerge:
    @patch("openbrain.services.document_service.cosmos_client")
    def test_dot_path_update_preserves_sibling_fields(self, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "task:123",
            "userId": "dev-user",
            "docType": "task",
            "taskType": "oneTimeTask",
            "narrative": "Pay bill",
            "state": {
                "status": "open",
                "dueDate": "2026-03-14T00:00:00Z",
                "isRecurring": False,
                "recurrenceDays": None,
                "completionCount": 0,
            },
            "createdAt": "2026-03-11T00:00:00Z",
            "updatedAt": "2026-03-11T00:00:00Z",
        }
        result = update_document("dev-user", "task:123", {"state.status": "done"})
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert result["status"] == "updated"
        assert upserted["state"]["status"] == "done"
        assert upserted["state"]["dueDate"] == "2026-03-14T00:00:00Z"


class TestRecurringTaskCompletion:
    @patch("openbrain.services.document_service.cosmos_client")
    def test_recurring_task_resets_on_done(self, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "task:456",
            "userId": "dev-user",
            "docType": "task",
            "taskType": "recurringTask",
            "narrative": "Clean shower",
            "state": {
                "status": "open",
                "isRecurring": True,
                "recurrenceDays": 30,
                "dueDate": "2026-03-11T00:00:00Z",
                "lastCompletedAt": None,
                "completionCount": 0,
                "progressNotes": [],
            },
            "createdAt": "2026-02-09T00:00:00Z",
            "updatedAt": "2026-02-09T00:00:00Z",
        }

        update_document("dev-user", "task:456", {"state.status": "done"})
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        state = upserted["state"]
        assert state["status"] == "open"
        assert state["completionCount"] == 1
        assert state["lastCompletedAt"] is not None
        assert len(state["progressNotes"]) == 1


class TestQueryAndSearchBehavior:
    @patch("openbrain.services.document_service.cosmos_client")
    def test_query_supports_null_filters(self, mock_cosmos):
        mock_cosmos.query_items.return_value = [
            {"id": "misc:1", "docType": "misc", "narrative": "Ambiguous thing"}
        ]
        result = query_documents("dev-user", "misc", {"suggestedDocType": None})
        assert result["total"] == 1
        sql = mock_cosmos.query_items.call_args[0][0]
        assert "NOT IS_DEFINED(c.suggestedDocType)" in sql

    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.services.document_service.generate_embedding", return_value=[0.3, 0.4])
    def test_update_reembeds_embedded_docs_only(self, _mock_embed, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "idea:1",
            "userId": "dev-user",
            "docType": "idea",
            "narrative": "Old idea",
            "goalId": None,
            "createdAt": "2026-03-11T00:00:00Z",
            "updatedAt": "2026-03-11T00:00:00Z",
            "embedding": [0.1],
        }
        update_document("dev-user", "idea:1", {"narrative": "New idea"})
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert upserted["embedding"] == [0.3, 0.4]

    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.services.document_service.generate_embedding", return_value=[])
    def test_update_does_not_embed_misc(self, _mock_embed, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "misc:1",
            "userId": "dev-user",
            "docType": "misc",
            "narrative": "Old misc",
            "createdAt": "2026-03-11T00:00:00Z",
            "updatedAt": "2026-03-11T00:00:00Z",
        }
        update_document("dev-user", "misc:1", {"narrative": "New misc"})
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert "embedding" not in upserted or upserted["embedding"] == []

    @patch("openbrain.services.document_service.cosmos_client")
    @patch("openbrain.embedding.embed_text", return_value=[0.1, 0.2, 0.3])
    def test_search_strips_hypothetical_queries_and_preserves_score(self, _mock_embed, mock_cosmos):
        mock_cosmos.vector_search.return_value = [
            {
                "id": "memory:123",
                "docType": "memory",
                "narrative": "Router password",
                "hypotheticalQueries": ["What is the router password?"],
                "rawText": "router password",
                "score": 0.94,
            }
        ]
        result = search_documents("dev-user", "router password", "memory", 5)
        assert result["results"][0]["score"] == 0.94
        assert "hypotheticalQueries" not in result["results"][0]

    def test_search_rejects_query_only_doc_types(self):
        with pytest.raises(ValidationError):
            search_documents("dev-user", "find open tasks", "task", 5)


class TestRawQuery:
    @patch("openbrain.services.document_service.cosmos_client")
    def test_raw_query_injects_user_id(self, mock_cosmos):
        mock_cosmos.query_items.return_value = []
        raw_query_documents("dev-user", "SELECT * FROM c WHERE c.userId = @userId", [])
        params = mock_cosmos.query_items.call_args[0][1]
        assert {"name": "@userId", "value": "dev-user"} in params

    def test_raw_query_rejects_mutation(self):
        with pytest.raises(ValidationError):
            raw_query_documents("dev-user", "DELETE FROM c WHERE c.userId = @userId")
