"""Pytest configuration and fixtures."""
import os
import tempfile
import pytest
import sqlite3
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Set environment variable
    os.environ['CHRONICLE_DB'] = db_path
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_docs():
    """Sample documents for testing."""
    return [
        {
            "source": "test",
            "external_id": "1",
            "title": "AI breakthrough announced",
            "url": "https://example.com/1",
            "text": "Scientists announce major AI breakthrough in machine learning",
            "ts": 1000000000
        },
        {
            "source": "test",
            "external_id": "2",
            "title": "New AI model released",
            "url": "https://example.com/2",
            "text": "Tech company releases new artificial intelligence model",
            "ts": 1000000001
        },
        {
            "source": "test",
            "external_id": "3",
            "title": "Space mission success",
            "url": "https://example.com/3",
            "text": "NASA announces successful Mars mission completion",
            "ts": 1000000002
        }
    ]


@pytest.fixture
def sample_texts():
    """Sample texts for NLP testing."""
    return [
        "This is a document about machine learning and AI",
        "Another article discussing artificial intelligence",
        "Something completely different about space exploration",
        "Yet another AI and machine learning discussion"
    ]
