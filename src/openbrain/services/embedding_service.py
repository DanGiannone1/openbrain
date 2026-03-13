"""Embedding orchestration service with HyDE support."""

from openbrain.embedding import embed_batch, embed_text

EMBEDDED_DOC_TYPES = {"memory", "idea"}


def document_requires_embedding(document: dict) -> bool:
    """Return True when a document participates in semantic search."""

    return document.get("docType") in EMBEDDED_DOC_TYPES


def generate_embedding(document: dict) -> list[float]:
    """Generate an embedding for embedded document types only.

    For memories with hypothetical queries, use HyDE averaging.
    For all other embedded docs, embed the narrative directly.
    Query-only documents return an empty vector.
    """

    if not document_requires_embedding(document):
        return []

    narrative = document.get("narrative", "")
    hypothetical_queries = document.get("hypotheticalQueries", [])

    if document.get("docType") == "memory" and hypothetical_queries:
        texts = [narrative] + hypothetical_queries
        embeddings = embed_batch(texts)
        return [sum(column) / len(column) for column in zip(*embeddings)]

    return embed_text(narrative)
