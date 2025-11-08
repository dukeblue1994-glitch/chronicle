"""Tests for embedding functionality."""
import pytest
import numpy as np
from chronicle.nlp.embedding import encode


class TestEmbedding:
    """Tests for text embedding."""
    
    def test_encode_single_text(self, sample_texts):
        """Test encoding a single text."""
        result = encode([sample_texts[0]])
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 1
        assert result.shape[1] > 0  # Should have some dimensions
    
    def test_encode_multiple_texts(self, sample_texts):
        """Test encoding multiple texts."""
        result = encode(sample_texts)
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == len(sample_texts)
        assert result.shape[1] > 0
    
    def test_encode_empty_list(self):
        """Test encoding empty list."""
        result = encode([])
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == 0
    
    def test_encode_normalization(self, sample_texts):
        """Test that embeddings are normalized."""
        result = encode(sample_texts)
        # Check L2 normalization (norms should be close to 1)
        norms = np.linalg.norm(result, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)
    
    def test_encode_consistency(self, sample_texts):
        """Test that same text produces same embedding."""
        text = sample_texts[0]
        result1 = encode([text])
        result2 = encode([text])
        assert np.allclose(result1, result2)
    
    def test_encode_similarity(self):
        """Test that similar texts have similar embeddings."""
        similar_texts = [
            "machine learning is great",
            "machine learning is awesome"
        ]
        different_text = ["space exploration news"]
        
        embeddings = encode(similar_texts + different_text)
        
        # Cosine similarity between similar texts
        sim_similar = np.dot(embeddings[0], embeddings[1])
        # Cosine similarity with different text
        sim_different = np.dot(embeddings[0], embeddings[2])
        
        # Similar texts should have higher similarity
        assert sim_similar > sim_different
