"""Embedding orchestration service with HyDE support."""

from openbrain.embedding import embed_text, embed_batch


def generate_embedding(document: dict) -> list[float]:
    """Generate embedding for a document.

    For memories with hypotheticalQueries: HyDE averaging (narrative + queries).
    For everything else: embed narrative directly.
    """
    narrative = document.get("narrative", "")
    hypothetical_queries = document.get("hypotheticalQueries", [])

    if document.get("docType") == "memory" and hypothetical_queries:
        texts = [narrative] + hypothetical_queries
        embeddings = embed_batch(texts)
        avg = [sum(col) / len(col) for col in zip(*embeddings)]
        return avg

    return embed_text(narrative)
