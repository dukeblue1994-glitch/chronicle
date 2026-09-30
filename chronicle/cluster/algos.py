from __future__ import annotations

from typing import Dict, List, Tuple

import numpy as np
from datasketch import MinHash, MinHashLSH


def _shingles(s: str, k: int = 4) -> List[str]:
    tokens = s.lower().split()
    return [" ".join(tokens[i : i + k]) for i in range(max(1, len(tokens) - k + 1))]


def minhash_signature(s: str, num_perm: int = 128) -> MinHash:
    mh = MinHash(num_perm=num_perm)
    tokens = {token for token in s.lower().split() if token}
    if not tokens:
        tokens = {""}

    for token in tokens:
        mh.update(token.encode("utf8"))
    return mh


def deduplicate(
    titles: List[str], threshold: float = 0.85, num_perm: int = 128
) -> List[int]:
    lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)
    sigs = [minhash_signature(t, num_perm=num_perm) for t in titles]
    reps: Dict[int, int] = {}

    for i, sig in enumerate(sigs):
        near = lsh.query(sig)
        if near:
            reps[i] = int(near[0]) if near[0].isdigit() else i
        else:
            lsh.insert(str(i), sig)
            reps[i] = i

    rep_map: Dict[int, int] = {}
    for i, r in reps.items():
        while reps.get(r, r) != r:
            r = reps[r]
        rep_map[i] = r

    return [rep_map[i] for i in range(len(titles))]


def cluster_embeddings(
    X: np.ndarray, min_cluster_size: int = 3
) -> Tuple[np.ndarray, np.ndarray]:
    if len(X) == 0:
        return np.array([], dtype=np.int32), np.array([], dtype=np.float32)

    if len(X) == 1:
        return np.array([0], dtype=np.int32), np.array([1.0], dtype=np.float32)

    try:
        import hdbscan

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric="euclidean",
        )
        labels = clusterer.fit_predict(X)
        probs = getattr(clusterer, "probabilities_", np.ones(len(labels)))
        return labels, probs
    except Exception:
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics.pairwise import cosine_distances

        D = cosine_distances(X)

        try:
            clusterer = AgglomerativeClustering(
                metric="precomputed",
                linkage="average",
                distance_threshold=0.6,
                n_clusters=None,
            )
        except TypeError:
            # Backward compatibility for older scikit-learn releases.
            clusterer = AgglomerativeClustering(
                affinity="precomputed",
                linkage="average",
                distance_threshold=0.6,
                n_clusters=None,
            )

        labels = clusterer.fit_predict(D)
        probs = np.ones(len(labels))
        return labels, probs
