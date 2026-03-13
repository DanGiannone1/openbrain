"""Memory document model."""

from typing import Literal

from pydantic import Field

from openbrain.models.common import ContentDocument


class MemoryDocument(ContentDocument):
    """Reference and factual recall documents."""

    docType: Literal["memory"] = "memory"
    hypotheticalQueries: list[str] = Field(default_factory=list)
