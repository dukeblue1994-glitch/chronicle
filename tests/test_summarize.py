"""Tests for summarization functionality."""
import pytest
from chronicle.timeline.summarize import summarize


class TestSummarization:
    """Tests for text summarization."""
    
    def test_summarize_basic(self, sample_docs):
        """Test basic summarization."""
        result = summarize(sample_docs, max_sentences=2)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_summarize_single_doc(self):
        """Test summarization with single document."""
        docs = [{"text": "This is a test sentence.", "title": "Test"}]
        result = summarize(docs, max_sentences=1)
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_summarize_max_sentences(self):
        """Test that max_sentences is respected."""
        docs = [
            {"text": "First sentence. Second sentence. Third sentence. Fourth sentence.", "title": "Test"}
        ]
        result = summarize(docs, max_sentences=2)
        # Should contain at most 2 sentences
        sentence_count = result.count('.') 
        assert sentence_count <= 2
    
    def test_summarize_empty_docs(self):
        """Test summarization with empty documents."""
        docs = []
        result = summarize(docs, max_sentences=3)
        assert result == ""
    
    def test_summarize_no_text(self):
        """Test summarization with docs that have no text."""
        docs = [{"title": "Just a title", "text": ""}]
        result = summarize(docs, max_sentences=1)
        assert isinstance(result, str)
    
    def test_summarize_uses_title_fallback(self):
        """Test that titles are used when text is missing."""
        docs = [{"title": "Important title here", "text": None}]
        result = summarize(docs, max_sentences=1)
        assert "Important" in result or "title" in result.lower()
