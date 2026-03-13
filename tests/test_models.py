"""Tests for Pydantic document models."""

import pytest
from pydantic import ValidationError

from openbrain.models import (
    AiMetadata,
    GoalDocument,
    GoalState,
    IdeaDocument,
    MemoryDocument,
    MiscDocument,
    TaskDocument,
    TaskState,
    UserSettingsDocument,
)


class TestAiMetadata:
    def test_defaults(self):
        meta = AiMetadata()
        assert meta.urgency is None
        assert meta.inferredEntities == []

    def test_extra_fields_allowed(self):
        meta = AiMetadata(urgency="high", customField="hello")
        assert meta.customField == "hello"

    def test_invalid_urgency(self):
        with pytest.raises(ValidationError):
            AiMetadata(urgency="critical")


class TestMemoryDocument:
    def test_valid_memory(self):
        doc = MemoryDocument(narrative="The garage router password is admin/123")
        assert doc.docType == "memory"
        assert doc.hypotheticalQueries == []

    def test_hyde_queries_optional(self):
        doc = MemoryDocument(
            narrative="The VPN lives at vpn.example.com",
            hypotheticalQueries=[
                "What is the VPN hostname?",
                "How do I connect to the office VPN?",
                "Where is the VPN endpoint?",
            ],
        )
        assert len(doc.hypotheticalQueries) == 3


class TestIdeaDocument:
    def test_valid_idea(self):
        doc = IdeaDocument(narrative="Build an internal agent dashboard")
        assert doc.docType == "idea"
        assert doc.goalId is None

    def test_idea_can_link_to_goal(self):
        doc = IdeaDocument(narrative="Launch a new Soligence offering", goalId="goal:123")
        assert doc.goalId == "goal:123"


class TestTaskDocument:
    def test_valid_one_time_task(self):
        doc = TaskDocument(narrative="Pay the urology bill", taskType="oneTimeTask")
        assert doc.docType == "task"
        assert doc.state.status == "open"

    def test_valid_recurring_task(self):
        doc = TaskDocument(
            narrative="Deep clean the shower",
            taskType="recurringTask",
            goalId="goal:house",
            state=TaskState(isRecurring=True, recurrenceDays=30),
        )
        assert doc.goalId == "goal:house"
        assert doc.state.recurrenceDays == 30

    def test_invalid_task_type(self):
        with pytest.raises(ValidationError):
            TaskDocument(narrative="Test", taskType="goal")


class TestGoalDocument:
    def test_valid_goal(self):
        doc = GoalDocument(
            narrative="Get better at Spanish",
            state=GoalState(status="active", progressNotes=["Started Duolingo"]),
        )
        assert doc.docType == "goal"
        assert doc.state.progressNotes == ["Started Duolingo"]

    def test_invalid_goal_status(self):
        with pytest.raises(ValidationError):
            GoalDocument(narrative="Bad goal", state=GoalState(status="open"))


class TestMiscDocument:
    def test_valid_misc(self):
        doc = MiscDocument(
            narrative="Something about a cleaning service maybe",
            suggestedDocType="task",
        )
        assert doc.docType == "misc"
        assert doc.suggestedDocType == "task"

    def test_invalid_suggested_doc_type(self):
        with pytest.raises(ValidationError):
            MiscDocument(narrative="Test", suggestedDocType="review")


class TestUserSettingsDocument:
    def test_valid_user_settings(self):
        doc = UserSettingsDocument(tagTaxonomy=["personal", "soligence", "microsoft"])
        assert doc.docType == "userSettings"
        assert doc.tagTaxonomy == ["personal", "soligence", "microsoft"]


class TestExtraFields:
    def test_content_document_extra_fields_allowed(self):
        doc = MemoryDocument(narrative="Test", customField="extra data")
        assert doc.customField == "extra data"

    def test_ai_metadata_extra_fields_allowed(self):
        doc = TaskDocument(
            narrative="Test",
            taskType="oneTimeTask",
            aiMetadata=AiMetadata(urgency="high", relatedPeople=["John"]),
        )
        assert doc.aiMetadata.relatedPeople == ["John"]
