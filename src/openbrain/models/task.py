"""Task document model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from openbrain.models.common import ContentDocument


class TaskState(BaseModel):
    """Structured state for actionable tasks."""

    model_config = ConfigDict(extra="allow")

    status: Literal["open", "inProgress", "done", "cancelled", "deferred"] = "open"
    dueDate: str | None = None
    isRecurring: bool = False
    recurrenceDays: int | None = None
    lastCompletedAt: str | None = None
    completionCount: int = 0
    progressNotes: list[str] = Field(default_factory=list)


class TaskDocument(ContentDocument):
    """One-time and recurring tasks."""

    docType: Literal["task"] = "task"
    taskType: Literal["oneTimeTask", "recurringTask"]
    goalId: str | None = None
    state: TaskState = Field(default_factory=TaskState)
