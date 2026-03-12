"""Shared model types for Open Brain documents."""

from pydantic import BaseModel, ConfigDict
from typing import Literal


class AiMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    urgency: Literal["high", "medium", "low"] | None = None
    inferredEntities: list[str] = []


class BaseDocument(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = ""
    userId: str = ""
    docType: Literal["memory", "task", "review"]
    narrative: str
    rawText: str | None = None
    contextTags: list[str] = []
    embedding: list[float] = []
    aiMetadata: AiMetadata = AiMetadata()
    createdAt: str = ""
    updatedAt: str = ""
