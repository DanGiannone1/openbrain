"""Tests for document service — dot-path merge and recurring task logic."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from openbrain.services.document_service import update_document, _strip, write_document


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
        assert "id" in result
        assert "narrative" in result
        assert "embedding" not in result
        assert "rawText" not in result
        assert "_rid" not in result
        assert "_etag" not in result


class TestDotPathMerge:
    @patch("openbrain.services.document_service.cosmos_client")
    def test_dot_path_update_preserves_sibling_fields(self, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "task:123",
            "userId": "dev-user",
            "docType": "task",
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
        mock_cosmos.upsert_item.return_value = {}

        result = update_document("dev-user", "task:123", {"state.status": "done"})

        assert result["status"] == "updated"
        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert upserted["state"]["status"] == "done"
        assert upserted["state"]["dueDate"] == "2026-03-14T00:00:00Z"  # preserved


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
        mock_cosmos.upsert_item.return_value = {}

        result = update_document("dev-user", "task:456", {"state.status": "done"})

        upserted = mock_cosmos.upsert_item.call_args[0][0]
        state = upserted["state"]

        assert state["status"] == "open"  # reset
        assert state["completionCount"] == 1
        assert state["lastCompletedAt"] is not None
        assert state["dueDate"] is not None
        assert len(state["progressNotes"]) == 1
        assert "Completed on" in state["progressNotes"][0]

    @patch("openbrain.services.document_service.cosmos_client")
    def test_already_done_recurring_is_noop(self, mock_cosmos):
        mock_cosmos.read_item.return_value = {
            "id": "task:789",
            "userId": "dev-user",
            "docType": "task",
            "narrative": "Test",
            "state": {
                "status": "done",
                "isRecurring": True,
                "recurrenceDays": 30,
            },
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
        mock_cosmos.upsert_item.return_value = {}

        result = update_document("dev-user", "task:789", {"state.status": "done"})

        upserted = mock_cosmos.upsert_item.call_args[0][0]
        # Should NOT trigger recurrence (already done)
        assert upserted["state"]["status"] == "done"


class TestImmutableFields:
    @patch("openbrain.services.document_service.generate_embedding", return_value=[0.1, 0.2])
    @patch("openbrain.services.document_service.cosmos_client")
    def test_immutable_fields_ignored(self, mock_cosmos, mock_embed):
        mock_cosmos.read_item.return_value = {
            "id": "memory:123",
            "userId": "dev-user",
            "docType": "memory",
            "narrative": "Original",
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-01-01T00:00:00Z",
        }
        mock_cosmos.upsert_item.return_value = {}

        update_document("dev-user", "memory:123", {
            "id": "memory:hacked",
            "userId": "other-user",
            "docType": "task",
            "createdAt": "1999-01-01T00:00:00Z",
            "narrative": "Updated narrative",
        })

        upserted = mock_cosmos.upsert_item.call_args[0][0]
        assert upserted["id"] == "memory:123"
        assert upserted["userId"] == "dev-user"
        assert upserted["docType"] == "memory"
        assert upserted["createdAt"] == "2026-01-01T00:00:00Z"
        assert upserted["narrative"] == "Updated narrative"
