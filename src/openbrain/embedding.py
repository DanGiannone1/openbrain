"""Azure AI Foundry embedding client using OpenAI v1 API."""

from openai import OpenAI

from openbrain.config import Config
from openbrain.utils.errors import EmbeddingError

_client: OpenAI | None = None


def get_embedding_client() -> OpenAI:
    global _client
    if _client is None:
        base_url = Config.AI_FOUNDRY_ENDPOINT.rstrip("/")
        if not base_url.endswith("/openai/v1"):
            base_url = f"{base_url}/openai/v1/"
        _client = OpenAI(
            api_key=Config.AI_FOUNDRY_API_KEY,
            base_url=base_url,
        )
    return _client


def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    try:
        client = get_embedding_client()
        response = client.embeddings.create(
            model=Config.AI_FOUNDRY_EMBEDDING_DEPLOYMENT,
            input=[text],
            encoding_format="float",
        )
        return response.data[0].embedding
    except Exception as e:
        raise EmbeddingError(f"Embedding generation failed: {e}") from e


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple texts in a single API call."""
    if not texts:
        return []
    try:
        client = get_embedding_client()
        response = client.embeddings.create(
            model=Config.AI_FOUNDRY_EMBEDDING_DEPLOYMENT,
            input=texts,
            encoding_format="float",
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        raise EmbeddingError(f"Batch embedding failed: {e}") from e
