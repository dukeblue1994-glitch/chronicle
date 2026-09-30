"""Pytest configuration and fixtures."""

import os
import tempfile

import pytest


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False) as f:
        db_path = f.name

    previous_db_path = os.environ.get("CHRONICLE_DB_PATH")
    previous_legacy_db = os.environ.get("CHRONICLE_DB")

    os.environ["CHRONICLE_DB_PATH"] = db_path
    os.environ.pop("CHRONICLE_DB", None)

    yield db_path

    if previous_db_path is None:
        os.environ.pop("CHRONICLE_DB_PATH", None)
    else:
        os.environ["CHRONICLE_DB_PATH"] = previous_db_path

    if previous_legacy_db is None:
        os.environ.pop("CHRONICLE_DB", None)
    else:
        os.environ["CHRONICLE_DB"] = previous_legacy_db

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
            "ts": 1000000000,
        },
        {
            "source": "test",
            "external_id": "2",
            "title": "New AI model released",
            "url": "https://example.com/2",
            "text": "Tech company releases new artificial intelligence model",
            "ts": 1000000001,
        },
        {
            "source": "test",
            "external_id": "3",
            "title": "Space mission success",
            "url": "https://example.com/3",
            "text": "NASA announces successful Mars mission completion",
            "ts": 1000000002,
        },
    ]


@pytest.fixture
def sample_texts():
    """Sample texts for NLP testing."""
    return [
        "This is a document about machine learning and AI",
        "Another article discussing artificial intelligence",
        "Something completely different about space exploration",
        "Yet another AI and machine learning discussion",
    ]
