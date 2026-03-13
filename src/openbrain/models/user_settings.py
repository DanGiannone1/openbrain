"""Per-user configuration document model."""

from typing import Literal

from pydantic import Field

from openbrain.models.common import BaseStoredDocument


class UserSettingsDocument(BaseStoredDocument):
    """Non-searchable per-user configuration stored in Cosmos."""

    docType: Literal["userSettings"] = "userSettings"
    tagTaxonomy: list[str] = Field(default_factory=list)
