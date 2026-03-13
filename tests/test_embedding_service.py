"""Tests for the embedding service."""

from unittest.mock import patch

from openbrain.services.embedding_service import document_requires_embedding, generate_embedding


class TestEmbeddingScope:
    def test_only_memory_and_idea_require_embeddings(self):
        assert document_requires_embedding({"docType": "memory"}) is True
        assert document_requires_embedding({"docType": "idea"}) is True
        assert document_requires_embedding({"docType": "task"}) is False
        assert document_requires_embedding({"docType": "goal"}) is False
        assert document_requires_embedding({"docType": "misc"}) is False
        assert document_requires_embedding({"docType": "userSettings"}) is False


class TestGenerateEmbedding:
    @patch("openbrain.services.embedding_service.embed_text")
    def test_idea_embeds_narrative_only(self, mock_embed):
        mock_embed.return_value = [0.1, 0.2, 0.3]
        result = generate_embedding({"docType": "idea", "narrative": "Build a dashboard"})
        mock_embed.assert_called_once_with("Build a dashboard")
        assert result == [0.1, 0.2, 0.3]

    @patch("openbrain.services.embedding_service.embed_batch")
    def test_memory_with_hyde(self, mock_batch):
        mock_batch.return_value = [
            [1.0, 2.0, 3.0],
            [2.0, 3.0, 4.0],
            [3.0, 4.0, 5.0],
            [4.0, 5.0, 6.0],
        ]
        doc = {
            "docType": "memory",
            "narrative": "Router password is admin",
            "hypotheticalQueries": ["Q1?", "Q2?", "Q3?"],
        }
        assert generate_embedding(doc) == [2.5, 3.5, 4.5]

    @patch("openbrain.services.embedding_service.embed_text")
    def test_memory_without_hyde(self, mock_embed):
        mock_embed.return_value = [0.5, 0.6]
        result = generate_embedding({"docType": "memory", "narrative": "A fact"})
        mock_embed.assert_called_once_with("A fact")
        assert result == [0.5, 0.6]

    def test_query_only_docs_return_empty_vector(self):
        assert generate_embedding({"docType": "misc", "narrative": "Unsure"}) == []
        assert generate_embedding({"docType": "userSettings", "tagTaxonomy": ["personal"]}) == []
