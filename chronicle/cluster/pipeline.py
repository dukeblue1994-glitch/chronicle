from __future__ import annotations
from chronicle.storage import db
from chronicle.nlp.embedding import encode
from chronicle.cluster.algos import cluster_embeddings, deduplicate
import numpy as np
import hashlib

def _cluster_id(vec: np.ndarray) -> str:
    h = hashlib.sha1(vec.tobytes()).hexdigest()[:16]
    return f"ev-{h}"

def run_batch():
    conn = db.connect()
    docs = db.get_recent_docs(conn, limit=400)
    if not docs:
        return 0
    titles = [d["title"] or "" for d in docs]
    rep = deduplicate(titles, threshold=0.85)
    keep_idx = {r for i, r in enumerate(rep) if i == r}
    filtered = [docs[i] for i in range(len(docs)) if i in keep_idx]
    if not filtered:
        return 0
    texts = [(d["title"] or "") + " " + (d["text"] or "") for d in filtered]
    X = encode(texts)
    labels, probs = cluster_embeddings(X, min_cluster_size=3)
    clusters = {}
    for i, lbl in enumerate(labels):
        if lbl == -1:
            continue
        clusters.setdefault(lbl, []).append(i)
    for lbl, idxs in clusters.items():
        centroid = X[idxs].mean(axis=0)
        cid = _cluster_id(centroid)
        for j in idxs:
            doc_id = filtered[j]["id"]
            score = float(probs[j])
            db.upsert_cluster(conn, doc_id, cid, score)
    return len(clusters)

def main():
    """Entry point for the clustering CLI."""
    n = run_batch()
    print(f"clustered: {n}")

if __name__ == "__main__":
    main()
