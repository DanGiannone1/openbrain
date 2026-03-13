"""Miscellaneous intake document model."""

from typing import Literal

from openbrain.models.common import ContentDocument


class MiscDocument(ContentDocument):
    """Catch-all for ambiguous or under-specified captures."""

    docType: Literal["misc"] = "misc"
    triageNotes: str | None = None
    suggestedDocType: Literal["memory", "idea", "task", "goal"] | None = None
