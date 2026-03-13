"""Goal document model."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from openbrain.models.common import ContentDocument


class GoalState(BaseModel):
    """Structured state for long-running goals."""

    model_config = ConfigDict(extra="allow")

    status: Literal["active", "paused", "completed", "abandoned"] = "active"
    targetDate: str | None = None
    lastProgressAt: str | None = None
    progressNotes: list[str] = Field(default_factory=list)


class GoalDocument(ContentDocument):
    """Long-running objectives that can spawn tasks."""

    docType: Literal["goal"] = "goal"
    state: GoalState = Field(default_factory=GoalState)
