"""Tests for embedding service."""

from unittest.mock import patch

from openbrain.services.embedding_service import generate_embedding


class TestGenerateEmbedding:
    @patch("openbrain.services.embedding_service.embed_text")
    def test_task_embeds_narrative_only(self, mock_embed):
        mock_embed.return_value = [0.1, 0.2, 0.3]
        doc = {"docType": "task", "narrative": "Pay bill"}
        result = generate_embedding(doc)
        mock_embed.assert_called_once_with("Pay bill")
        assert result == [0.1, 0.2, 0.3]

    @patch("openbrain.services.embedding_service.embed_batch")
    def test_memory_with_hyde(self, mock_batch):
        mock_batch.return_value = [
            [1.0, 2.0, 3.0],  # narrative
            [2.0, 3.0, 4.0],  # q1
            [3.0, 4.0, 5.0],  # q2
            [4.0, 5.0, 6.0],  # q3
        ]
        doc = {
            "docType": "memory",
            "narrative": "Router password is admin",
            "hypotheticalQueries": ["Q1?", "Q2?", "Q3?"],
        }
        result = generate_embedding(doc)
        # Average: [(1+2+3+4)/4, (2+3+4+5)/4, (3+4+5+6)/4] = [2.5, 3.5, 4.5]
        assert result == [2.5, 3.5, 4.5]

    @patch("openbrain.services.embedding_service.embed_text")
    def test_memory_without_hyde(self, mock_embed):
        mock_embed.return_value = [0.5, 0.6]
        doc = {"docType": "memory", "narrative": "A fact", "hypotheticalQueries": []}
        result = generate_embedding(doc)
        mock_embed.assert_called_once_with("A fact")
        assert result == [0.5, 0.6]

    @patch("openbrain.services.embedding_service.embed_text")
    def test_review_embeds_narrative(self, mock_embed):
        mock_embed.return_value = [0.9]
        doc = {"docType": "review", "narrative": "Ambiguous item"}
        result = generate_embedding(doc)
        mock_embed.assert_called_once_with("Ambiguous item")
