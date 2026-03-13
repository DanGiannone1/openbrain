"""Scenario-oriented service tests using an in-memory fake Cosmos backend."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from openbrain.services.document_service import (
    query_documents,
    raw_query_documents,
    read_document,
    search_documents,
    update_document,
    write_document,
)


class FakeCosmosBackend:
    def __init__(self):
        self.items: dict[tuple[str, str], dict] = {}

    def create_item(self, item: dict) -> dict:
        self.items[(item["id"], item["userId"])] = deepcopy(item)
        return deepcopy(item)

    def read_item(self, item_id: str, partition_key: str) -> dict:
        return deepcopy(self.items[(item_id, partition_key)])

    def upsert_item(self, item: dict) -> dict:
        self.items[(item["id"], item["userId"])] = deepcopy(item)
        return deepcopy(item)

    def delete_item(self, item_id: str, partition_key: str) -> None:
        self.items.pop((item_id, partition_key), None)

    def query_items(self, _sql: str, parameters: list[dict] | None = None, partition_key: str | None = None, max_item_count: int = 100) -> list[dict]:
        params = {param["name"]: param["value"] for param in (parameters or [])}
        results = []
        for (_, user_id), item in self.items.items():
            if partition_key and user_id != partition_key:
                continue
            if "@docType" in params and item.get("docType") != params["@docType"]:
                continue
            goal_id = params.get("@p0")
            if goal_id is not None and item.get("goalId") != goal_id:
                continue
            results.append(deepcopy(item))
        return results[:max_item_count]

    def vector_search(self, _query_vector: list[float], user_id: str, doc_type: str | None = None, top_k: int = 5) -> list[dict]:
        results = []
        for (_, partition), item in self.items.items():
            if partition != user_id:
                continue
            if item.get("docType") not in {"memory", "idea"}:
                continue
            if doc_type and item.get("docType") != doc_type:
                continue
            doc = deepcopy(item)
            doc["score"] = 0.97
            results.append(doc)
        return results[:top_k]


@patch("openbrain.services.document_service.generate_embedding", return_value=[0.1, 0.2, 0.3])
@patch("openbrain.embedding.embed_text", return_value=[0.1, 0.2, 0.3])
def test_goal_and_task_lifecycle_scenario(_mock_query_embed, _mock_generate_embedding):
    backend = FakeCosmosBackend()

    with patch("openbrain.services.document_service.cosmos_client", backend):
        goal = write_document(
            "dev-user",
            {
                "docType": "goal",
                "narrative": "Get better at Spanish",
                "contextTags": ["personal"],
            },
        )
        task = write_document(
            "dev-user",
            {
                "docType": "task",
                "taskType": "oneTimeTask",
                "narrative": "Book first Spanish tutoring session",
                "goalId": goal["id"],
                "contextTags": ["personal"],
            },
        )

        linked_tasks = query_documents("dev-user", "task", {"goalId": goal["id"]})
        assert linked_tasks["total"] == 1
        assert linked_tasks["results"][0]["goalId"] == goal["id"]

        update_document("dev-user", task["id"], {"state.status": "done"})
        updated = read_document("dev-user", task["id"])
        assert updated["state"]["status"] == "done"


@patch("openbrain.services.document_service.generate_embedding", return_value=[0.7, 0.8, 0.9])
@patch("openbrain.embedding.embed_text", return_value=[0.7, 0.8, 0.9])
def test_memory_search_and_user_settings_scenario(_mock_query_embed, _mock_generate_embedding):
    backend = FakeCosmosBackend()

    with patch("openbrain.services.document_service.cosmos_client", backend):
        settings = write_document(
            "dev-user",
            {
                "docType": "userSettings",
                "tagTaxonomy": ["personal", "soligence", "microsoft"],
            },
        )
        memory = write_document(
            "dev-user",
            {
                "docType": "memory",
                "narrative": "The garage router password is admin/Netgear2024.",
                "rawText": "garage router password is admin slash netgear 2024",
                "contextTags": ["PERSONAL", "home", "network"],
                "hypotheticalQueries": [
                    "What is the garage router password?",
                    "How do I log into the garage router?",
                    "What are the home router credentials?",
                ],
            },
        )

        settings_doc = read_document("dev-user", settings["id"])
        assert settings_doc["tagTaxonomy"] == ["personal", "soligence", "microsoft"]

        search_results = search_documents("dev-user", "garage router password", "memory", 5)
        assert search_results["total"] == 1
        assert search_results["results"][0]["id"] == memory["id"]
        assert search_results["results"][0]["contextTags"] == ["personal", "home", "network"]


@patch("openbrain.services.document_service.generate_embedding", return_value=[0.2, 0.3, 0.4])
@patch("openbrain.embedding.embed_text", return_value=[0.2, 0.3, 0.4])
def test_multi_user_partition_isolation_scenario(_mock_query_embed, _mock_generate_embedding):
    backend = FakeCosmosBackend()

    with patch("openbrain.services.document_service.cosmos_client", backend):
        first = write_document(
            "user-a@example.com",
            {
                "docType": "memory",
                "narrative": "User A garage code is 1234",
                "contextTags": ["personal"],
            },
        )
        second = write_document(
            "user-b@example.com",
            {
                "docType": "memory",
                "narrative": "User B mailbox is slot 44",
                "contextTags": ["personal"],
            },
        )

        user_a_query = query_documents("user-a@example.com", "memory", limit=10)
        user_b_query = query_documents("user-b@example.com", "memory", limit=10)
        user_a_search = search_documents("user-a@example.com", "garage code", "memory", 5)
        user_b_search = search_documents("user-b@example.com", "mailbox slot", "memory", 5)

        assert user_a_query["total"] == 1
        assert user_a_query["results"][0]["id"] == first["id"]
        assert user_b_query["total"] == 1
        assert user_b_query["results"][0]["id"] == second["id"]
        assert user_a_search["results"][0]["id"] == first["id"]
        assert user_b_search["results"][0]["id"] == second["id"]


@patch("openbrain.services.document_service.generate_embedding", return_value=[])
def test_recurring_task_completion_scenario(_mock_generate_embedding):
    backend = FakeCosmosBackend()

    with patch("openbrain.services.document_service.cosmos_client", backend):
        created = write_document(
            "dev-user",
            {
                "docType": "task",
                "taskType": "recurringTask",
                "narrative": "Replace HVAC filter",
                "contextTags": ["personal", "home"],
                "state": {
                    "status": "open",
                    "isRecurring": True,
                    "recurrenceDays": 30,
                    "dueDate": "2026-03-15T00:00:00+00:00",
                    "progressNotes": [],
                },
            },
        )

        update_document("dev-user", created["id"], {"state.status": "done"})
        updated = read_document("dev-user", created["id"])

        assert updated["state"]["status"] == "open"
        assert updated["state"]["completionCount"] == 1
        assert updated["state"]["lastCompletedAt"] is not None
        assert updated["state"]["dueDate"] is not None
        assert updated["state"]["progressNotes"]


@patch("openbrain.services.document_service.generate_embedding", return_value=[0.5, 0.6, 0.7])
def test_raw_query_and_search_sanitization_scenario(_mock_generate_embedding):
    backend = FakeCosmosBackend()

    with patch("openbrain.services.document_service.cosmos_client", backend):
        write_document(
            "dev-user",
            {
                "docType": "memory",
                "narrative": "The breaker panel is in the basement utility room.",
                "rawText": "breaker panel basement utility room",
                "contextTags": ["personal", "home"],
                "hypotheticalQueries": ["Where is the breaker panel?"],
            },
        )

        raw_results = raw_query_documents("dev-user", "SELECT * FROM c WHERE c.userId = @userId")
        memory = raw_results["results"][0]

        assert raw_results["total"] == 1
        assert memory["docType"] == "memory"
        assert "rawText" not in memory
        assert "embedding" not in memory
