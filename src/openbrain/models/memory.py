"""Memory document model."""

from typing import Literal
from openbrain.models.common import BaseDocument


class MemoryDocument(BaseDocument):
    docType: Literal["memory"] = "memory"
    memoryType: Literal["fact", "idea"]
    hypotheticalQueries: list[str] = []
    supersededBy: str | None = None
