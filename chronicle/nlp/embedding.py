from __future__ import annotations

import logging
import threading
from typing import List, cast

import numpy as np

from chronicle.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_name: tuple[str, str] | None = None
_model_lock = threading.Lock()


def _ensure_sbert():
    global _model
    global _model_name

    if _model is not None and _model_name == (
        settings.embedding_model,
        settings.embedding_device,
    ):
        return _model

    with _model_lock:
        if _model is not None and _model_name == (
            settings.embedding_model,
            settings.embedding_device,
        ):
            return _model

        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer(
                settings.embedding_model, device=settings.embedding_device
            )
            _model_name = (settings.embedding_model, settings.embedding_device)
        except Exception as exc:
            if settings.embedding_backend == "semantic":
                raise RuntimeError(
                    "Semantic model unavailable. Install chronicle-events[embeddings] "
                    "and check model access, or select CHRONICLE_EMBEDDING_BACKEND=tfidf."
                ) from exc
            logger.warning(
                "Failed to load sentence-transformer '%s'; falling back to TF-IDF. "
                "Install optional embeddings with chronicle-events[embeddings]: %s",
                settings.embedding_model,
                exc,
            )
            _model = None
            _model_name = None

    return _model


def _encode_tfidf(texts: List[str]) -> np.ndarray:
    from sklearn.feature_extraction.text import TfidfVectorizer

    safe_texts = [(text or "").strip() for text in texts]
    vectorizer = TfidfVectorizer(
        max_features=4096, ngram_range=(1, 2), norm="l2", token_pattern=r"(?u)\b\w+\b"
    )
    try:
        X = (
            vectorizer.fit_transform(safe_texts)
            .toarray()
            .astype(np.float32, copy=False)
        )
    except ValueError as exc:
        if "empty vocabulary" not in str(exc):
            raise
        return np.zeros((len(texts), 1), dtype=np.float32)

    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return cast(np.ndarray, X / norms)


def encode(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, 0), dtype=np.float32)

    safe_texts = [(text or "").strip() for text in texts]

    model = None if settings.embedding_backend == "tfidf" else _ensure_sbert()
    if model is not None:
        vectors = model.encode(
            safe_texts,
            batch_size=settings.embedding_batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    return _encode_tfidf(safe_texts)
