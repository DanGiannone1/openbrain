"""Shared model types for Open Brain documents."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocType = Literal["memory", "idea", "task", "goal", "misc", "userSettings"]


class AiMetadata(BaseModel):
    """Flexible AI-generated metadata stored alongside documents."""

    model_config = ConfigDict(extra="allow")

    urgency: Literal["high", "medium", "low"] | None = None
    inferredEntities: list[str] = Field(default_factory=list)


class BaseStoredDocument(BaseModel):
    """Server-managed fields shared by all persisted documents."""

    model_config = ConfigDict(extra="allow")

    id: str = ""
    userId: str = ""
    docType: DocType
    createdAt: str = ""
    updatedAt: str = ""


class ContentDocument(BaseStoredDocument):
    """Shared fields for user-authored content documents."""

    narrative: str
    rawText: str | None = None
    contextTags: list[str] = Field(default_factory=list)
    embedding: list[float] = Field(default_factory=list)
    aiMetadata: AiMetadata = Field(default_factory=AiMetadata)
