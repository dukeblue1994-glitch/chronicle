from __future__ import annotations
import logging
from chronicle.storage import db
from chronicle.nlp.embedding import encode
from chronicle.cluster.algos import cluster_embeddings, deduplicate
from chronicle.config import settings
import numpy as np
import hashlib

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _cluster_id(vec: np.ndarray) -> str:
    h = hashlib.sha1(vec.tobytes()).hexdigest()[:16]
    return f"ev-{h}"


def run_batch():
    """Run clustering on recent documents."""
    logger.info("Starting clustering batch")
    conn = db.connect()
    
    docs = db.get_recent_docs(conn, limit=settings.cluster_batch_size)
    if not docs:
        logger.info("No documents to cluster")
        return 0
    
    logger.info(f"Processing {len(docs)} documents")
    
    # Deduplication
    titles = [d["title"] or "" for d in docs]
    rep = deduplicate(titles, threshold=settings.dedup_threshold)
    keep_idx = {r for i, r in enumerate(rep) if i == r}
    filtered = [docs[i] for i in range(len(docs)) if i in keep_idx]
    
    duplicates_removed = len(docs) - len(filtered)
    if duplicates_removed > 0:
        logger.info(f"Removed {duplicates_removed} near-duplicates")
    
    if not filtered:
        logger.info("No documents remaining after deduplication")
        return 0
    
    # Embedding
    logger.info(f"Generating embeddings for {len(filtered)} documents")
    texts = [(d["title"] or "") + " " + (d["text"] or "") for d in filtered]
    X = encode(texts)
    
    # Clustering
    logger.info(f"Clustering with min_size={settings.cluster_min_size}")
    labels, probs = cluster_embeddings(X, min_cluster_size=settings.cluster_min_size)
    
    clusters = {}
    for i, lbl in enumerate(labels):
        if lbl == -1:
            continue
        clusters.setdefault(lbl, []).append(i)
    
    logger.info(f"Found {len(clusters)} clusters")
    
    # Store cluster assignments
    for lbl, idxs in clusters.items():
        centroid = X[idxs].mean(axis=0)
        cid = _cluster_id(centroid)
        for j in idxs:
            doc_id = filtered[j]["id"]
            score = float(probs[j])
            db.upsert_cluster(conn, doc_id, cid, score)
    
    conn.close()
    logger.info(f"Clustering complete: {len(clusters)} clusters created")
    return len(clusters)

def main():
    """Entry point for the clustering CLI."""
    n = run_batch()
    print(f"clustered: {n}")

if __name__ == "__main__":
    main()
