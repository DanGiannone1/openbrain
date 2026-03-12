"""Review document model."""

from typing import Literal
from openbrain.models.common import BaseDocument


class ReviewDocument(BaseDocument):
    docType: Literal["review"] = "review"
    triageAttempt: dict = {}
    resolvedAt: str | None = None
    resolution: Literal["reIngested", "discarded"] | None = None
