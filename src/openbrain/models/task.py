"""Task document model."""

from pydantic import BaseModel
from typing import Literal
from openbrain.models.common import BaseDocument


class TaskState(BaseModel):
    status: Literal["open", "inProgress", "done", "cancelled", "deferred"] = "open"
    dueDate: str | None = None
    isRecurring: bool = False
    recurrenceDays: int | None = None
    lastCompletedAt: str | None = None
    completionCount: int = 0
    progressNotes: list[str] = []


class TaskDocument(BaseDocument):
    docType: Literal["task"] = "task"
    taskType: Literal["goal", "oneTimeTask", "recurringTask"]
    state: TaskState = TaskState()
