from __future__ import annotations

import hashlib

from chronicle.cluster.algos import cluster_embeddings, deduplicate
from chronicle.config import settings
from chronicle.logging import (
    ErrorCategory,
    get_logger,
    log_exception,
    log_metric,
    log_with_context,
)
from chronicle.nlp.embedding import encode
from chronicle.storage import db

logger = get_logger(__name__)


def _cluster_id(doc_ids: list[int]) -> str:
    identity = ",".join(str(doc_id) for doc_id in sorted(doc_ids))
    h = hashlib.sha256(identity.encode()).hexdigest()[:16]
    return f"ev-{h}"


def run_batch() -> int:
    """Run clustering on recent documents."""
    logger.info("Starting clustering batch")
    conn = db.connect()

    try:
        docs = db.get_recent_docs(conn, limit=settings.cluster_batch_size)
        if not docs:
            logger.info("No documents to cluster")
            return 0

        log_metric(logger, "clustering.docs_input", len(docs))
        logger.info("Processing %s documents", len(docs))

        titles = [d["title"] or d["text"] or "" for d in docs]
        rep = deduplicate(
            titles,
            threshold=settings.dedup_threshold,
            num_perm=settings.dedup_num_perm,
        )
        keep_idx = {r for i, r in enumerate(rep) if i == r}
        filtered = [docs[i] for i in range(len(docs)) if i in keep_idx]

        duplicates_removed = len(docs) - len(filtered)
        if duplicates_removed > 0:
            log_with_context(
                logger,
                "INFO",
                "Removed near-duplicates",
                duplicates_removed=duplicates_removed,
            )

        if not filtered:
            logger.info("No documents remaining after deduplication")
            return 0

        logger.info("Generating embeddings for %s documents", len(filtered))
        texts = [(d["title"] or "") + " " + (d["text"] or "") for d in filtered]
        X = encode(texts)

        logger.info("Clustering with min_size=%s", settings.cluster_min_size)
        labels, probs = cluster_embeddings(
            X, min_cluster_size=settings.cluster_min_size
        )

        clusters: dict[int, list[int]] = {}
        for i, lbl in enumerate(labels):
            if lbl == -1:
                continue
            clusters.setdefault(int(lbl), []).append(i)

        logger.info("Found %s clusters", len(clusters))

        assignments: list[tuple[int, str, float]] = []
        for idxs in clusters.values():
            cid = _cluster_id([int(filtered[j]["id"]) for j in idxs])
            for j in idxs:
                doc_id = int(filtered[j]["id"])
                score = float(probs[j])
                assignments.append((doc_id, cid, score))

        db.replace_assignments(conn, [int(doc["id"]) for doc in docs], assignments)

        log_metric(logger, "clustering.clusters_created", len(clusters))
        logger.info("Clustering complete: %s clusters created", len(clusters))
        return len(clusters)

    except Exception as exc:
        log_exception(
            logger,
            ErrorCategory.CLUSTERING,
            "Clustering batch failed",
            exc,
        )
        raise
    finally:
        conn.close()


def main():
    """Entry point for the clustering CLI."""
    n = run_batch()
    print(f"clustered: {n}")


if __name__ == "__main__":
    main()
