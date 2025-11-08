"""Tests for clustering and deduplication algorithms."""
import pytest
import numpy as np
from chronicle.cluster.algos import deduplicate, cluster_embeddings, minhash_signature, _shingles


class TestShingles:
    """Tests for shingling function."""
    
    def test_shingles_basic(self):
        """Test basic shingling."""
        text = "hello world test"
        shingles = _shingles(text, k=2)
        assert len(shingles) == 2
        assert "hello world" in shingles
        assert "world test" in shingles
    
    def test_shingles_short_text(self):
        """Test shingling with text shorter than k."""
        text = "hi"
        shingles = _shingles(text, k=4)
        assert len(shingles) == 1


class TestMinHash:
    """Tests for MinHash signature generation."""
    
    def test_minhash_consistency(self):
        """Test that same text produces same signature."""
        text = "this is a test document"
        sig1 = minhash_signature(text)
        sig2 = minhash_signature(text)
        assert sig1.jaccard(sig2) == 1.0
    
    def test_minhash_similarity(self):
        """Test that similar texts have high similarity."""
        text1 = "machine learning and artificial intelligence"
        text2 = "artificial intelligence and machine learning"
        sig1 = minhash_signature(text1)
        sig2 = minhash_signature(text2)
        similarity = sig1.jaccard(sig2)
        assert similarity > 0.5


class TestDeduplication:
    """Tests for deduplication algorithm."""
    
    def test_deduplicate_exact_duplicates(self):
        """Test deduplication of exact duplicates."""
        texts = ["hello world", "hello world", "goodbye world"]
        reps = deduplicate(texts, threshold=0.9)
        # First two should map to same representative
        assert reps[0] == reps[1]
        # Third should be different
        assert reps[2] != reps[0]
    
    def test_deduplicate_near_duplicates(self):
        """Test deduplication of near-duplicates."""
        texts = [
            "AI breakthrough in machine learning",
            "Machine learning breakthrough in AI",
            "Space exploration news"
        ]
        reps = deduplicate(texts, threshold=0.7)
        # First two should be considered duplicates
        assert reps[0] == reps[1]
        # Third should be unique
        assert reps[2] != reps[0]
    
    def test_deduplicate_all_unique(self):
        """Test deduplication with all unique texts."""
        texts = ["apple", "banana", "cherry"]
        reps = deduplicate(texts, threshold=0.9)
        # All should be their own representatives
        assert reps[0] == 0
        assert reps[1] == 1
        assert reps[2] == 2


class TestClustering:
    """Tests for clustering algorithm."""
    
    def test_cluster_embeddings_basic(self):
        """Test basic clustering."""
        # Create simple 2D embeddings with two clear clusters
        X = np.array([
            [0.0, 0.0],
            [0.1, 0.1],
            [0.0, 0.1],
            [10.0, 10.0],
            [10.1, 10.0],
            [10.0, 10.1]
        ])
        labels, probs = cluster_embeddings(X, min_cluster_size=2)
        
        assert len(labels) == 6
        assert len(probs) == 6
        
        # Should find at least 1 cluster (may mark some as noise with -1)
        unique_clusters = set(labels) - {-1}
        assert len(unique_clusters) >= 1
    
    def test_cluster_embeddings_single_cluster(self):
        """Test clustering with all similar points."""
        X = np.random.randn(5, 10) * 0.1  # Very similar points
        labels, probs = cluster_embeddings(X, min_cluster_size=3)
        
        assert len(labels) == 5
        assert len(probs) == 5
    
    def test_cluster_embeddings_dimensions(self):
        """Test clustering with high-dimensional data."""
        X = np.random.randn(20, 384)  # Typical embedding dimension
        labels, probs = cluster_embeddings(X, min_cluster_size=3)
        
        assert len(labels) == 20
        assert len(probs) == 20
        assert all(isinstance(label, (int, np.integer)) for label in labels)
