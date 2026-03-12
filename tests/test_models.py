"""Tests for Pydantic document models."""

import pytest
from pydantic import ValidationError

from openbrain.models.common import AiMetadata, BaseDocument
from openbrain.models.memory import MemoryDocument
from openbrain.models.task import TaskDocument, TaskState
from openbrain.models.review import ReviewDocument


class TestAiMetadata:
    def test_defaults(self):
        meta = AiMetadata()
        assert meta.urgency is None
        assert meta.inferredEntities == []

    def test_extra_fields_allowed(self):
        meta = AiMetadata(urgency="high", customField="hello")
        assert meta.urgency == "high"
        assert meta.customField == "hello"

    def test_urgency_enum(self):
        with pytest.raises(ValidationError):
            AiMetadata(urgency="critical")


class TestMemoryDocument:
    def test_valid_fact(self):
        doc = MemoryDocument(
            narrative="The garage router password is admin/123",
            memoryType="fact",
        )
        assert doc.docType == "memory"
        assert doc.memoryType == "fact"
        assert doc.hypotheticalQueries == []
        assert doc.supersededBy is None

    def test_valid_idea_with_hyde(self):
        doc = MemoryDocument(
            narrative="Idea for a new app",
            memoryType="idea",
            hypotheticalQueries=["What app ideas do I have?", "Any brainstorms?", "New projects?"],
        )
        assert len(doc.hypotheticalQueries) == 3

    def test_invalid_memory_type(self):
        with pytest.raises(ValidationError):
            MemoryDocument(narrative="test", memoryType="note")

    def test_missing_narrative(self):
        with pytest.raises(ValidationError):
            MemoryDocument(memoryType="fact")

    def test_missing_memory_type(self):
        with pytest.raises(ValidationError):
            MemoryDocument(narrative="test")


class TestTaskDocument:
    def test_valid_one_time_task(self):
        doc = TaskDocument(
            narrative="Pay the urology bill",
            taskType="oneTimeTask",
        )
        assert doc.docType == "task"
        assert doc.state.status == "open"
        assert doc.state.isRecurring is False

    def test_valid_recurring_task(self):
        doc = TaskDocument(
            narrative="Clean the shower",
            taskType="recurringTask",
            state=TaskState(
                status="open",
                isRecurring=True,
                recurrenceDays=30,
            ),
        )
        assert doc.state.recurrenceDays == 30
        assert doc.state.completionCount == 0

    def test_valid_goal(self):
        doc = TaskDocument(
            narrative="Learn Spanish",
            taskType="goal",
            state=TaskState(status="inProgress", progressNotes=["Started Duolingo"]),
        )
        assert doc.state.progressNotes == ["Started Duolingo"]

    def test_invalid_task_type(self):
        with pytest.raises(ValidationError):
            TaskDocument(narrative="test", taskType="chore")

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            TaskDocument(
                narrative="test",
                taskType="oneTimeTask",
                state=TaskState(status="pending"),
            )


class TestReviewDocument:
    def test_valid_review(self):
        doc = ReviewDocument(
            narrative="Something about John and taxes",
            triageAttempt={"reason": "Ambiguous"},
        )
        assert doc.docType == "review"
        assert doc.resolvedAt is None
        assert doc.resolution is None

    def test_valid_resolution(self):
        doc = ReviewDocument(
            narrative="test",
            resolution="reIngested",
            resolvedAt="2026-03-11T14:30:00Z",
        )
        assert doc.resolution == "reIngested"

    def test_invalid_resolution(self):
        with pytest.raises(ValidationError):
            ReviewDocument(narrative="test", resolution="deleted")


class TestExtraFields:
    def test_base_document_extra_allowed(self):
        doc = MemoryDocument(
            narrative="test",
            memoryType="fact",
            customField="extra data",
        )
        assert doc.customField == "extra data"

    def test_ai_metadata_extra_allowed(self):
        doc = TaskDocument(
            narrative="test",
            taskType="oneTimeTask",
            aiMetadata=AiMetadata(urgency="high", relatedPeople=["John"]),
        )
        assert doc.aiMetadata.relatedPeople == ["John"]
