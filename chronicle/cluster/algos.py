from __future__ import annotations

import logging
from typing import List, Tuple, cast

import numpy as np
from datasketch import MinHash, MinHashLSH

logger = logging.getLogger(__name__)


def _shingles(s: str, k: int = 4) -> List[str]:
    tokens = s.lower().split()
    return [" ".join(tokens[i : i + k]) for i in range(max(1, len(tokens) - k + 1))]


def minhash_signature(s: str, num_perm: int = 128) -> MinHash:
    mh = MinHash(num_perm=num_perm)
    for token in sorted(set(s.lower().split()) or {""}):
        mh.update(token.encode("utf8"))
    return mh


def deduplicate(
    titles: List[str], threshold: float = 0.85, num_perm: int = 128
) -> List[int]:
    """Find representative titles using LSH candidates and exact token overlap."""
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be greater than zero and at most one")
    if num_perm < 16:
        raise ValueError("num_perm must be at least 16")
    try:
        lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    except ValueError:
        # Very high thresholds and short signatures can select only one band.
        # Use two bands for candidate retrieval; exact overlap still decides matches.
        lsh = MinHashLSH(num_perm=num_perm, params=(2, num_perm // 2))
    tokens = [set(title.lower().split()) for title in titles]
    representatives: List[int] = []
    for i, title in enumerate(titles):
        if not tokens[i]:
            representatives.append(i)
            continue
        sig = minhash_signature(title, num_perm)
        candidates = sorted(int(candidate) for candidate in lsh.query(sig))
        matches = [
            j
            for j in candidates
            if len(tokens[i] & tokens[j]) / len(tokens[i] | tokens[j]) >= threshold
        ]
        representatives.append(matches[0] if matches else i)
        if not matches:
            lsh.insert(str(i), sig)
    return representatives


def _agglomerative(X: np.ndarray) -> np.ndarray:
    from sklearn.cluster import AgglomerativeClustering
    from sklearn.metrics.pairwise import cosine_distances

    return cast(
        np.ndarray,
        AgglomerativeClustering(
            metric="precomputed",
            linkage="average",
            distance_threshold=0.6,
            n_clusters=None,
        ).fit_predict(cosine_distances(X)),
    )


def cluster_embeddings(
    X: np.ndarray, min_cluster_size: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    """Cluster finite vectors, enforcing the same size rules on both backends."""
    X = np.asarray(X)
    if X.ndim != 2 or not np.isfinite(X).all():
        raise ValueError("Embeddings must be a finite two-dimensional matrix")
    if min_cluster_size < 1:
        raise ValueError("min_cluster_size must be positive")
    labels = np.full(len(X), -1, dtype=np.int32)
    probabilities = np.zeros(len(X), dtype=np.float32)
    valid = np.flatnonzero(np.linalg.norm(X, axis=1) > 0)
    if len(valid) < min_cluster_size or not len(valid):
        return labels, probabilities
    if len(valid) == 1:
        labels[valid] = 0
        probabilities[valid] = 1
        return labels, probabilities
    vectors = X[valid].astype(np.float64)
    try:
        if min_cluster_size == 1:
            found = _agglomerative(vectors)
            scores = np.ones(len(found))
        else:
            import hdbscan

            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size, metric="euclidean"
            )
            found = clusterer.fit_predict(vectors)
            scores = clusterer.probabilities_
    except (ImportError, TypeError) as exc:
        logger.warning("HDBSCAN unavailable; using agglomerative clustering: %s", exc)
        found = _agglomerative(vectors)
        scores = np.ones(len(found))
    for label in set(found) - {-1}:
        members = np.flatnonzero(found == label)
        if len(members) >= min_cluster_size:
            labels[valid[members]] = label
            probabilities[valid[members]] = scores[members]
    return labels, probabilities
