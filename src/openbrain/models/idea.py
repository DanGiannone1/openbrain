"""Idea document model."""

from typing import Literal

from openbrain.models.common import ContentDocument


class IdeaDocument(ContentDocument):
    """Speculative or exploratory user ideas."""

    docType: Literal["idea"] = "idea"
    goalId: str | None = None
