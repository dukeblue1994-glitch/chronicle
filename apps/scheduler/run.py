"""Scheduled clustering job runner."""

from __future__ import annotations

import time

from chronicle.cluster.pipeline import run_batch
from chronicle.config import settings
from chronicle.logging import ErrorCategory, get_logger, log_exception, log_metric

logger = get_logger(__name__)


def run_scheduler() -> None:
    """Run clustering on a schedule."""
    if settings.cluster_schedule <= 0:
        logger.info("Scheduling disabled (CHRONICLE_CLUSTER_SCHEDULE=0)")
        logger.info("Run clustering manually with: chronicle-cluster")
        return

    logger.info(
        "Starting scheduled clustering (interval=%ss)", settings.cluster_schedule
    )

    iteration = 0
    while True:
        iteration += 1
        try:
            logger.info("Running clustering iteration %s", iteration)
            n_clusters = run_batch()
            log_metric(
                logger,
                "scheduler.clusters_created",
                n_clusters,
                iteration=iteration,
            )
            logger.info("Iteration %s complete: %s clusters", iteration, n_clusters)
        except Exception as exc:
            log_exception(
                logger,
                ErrorCategory.CLUSTERING,
                "Clustering iteration failed",
                exc,
                iteration=iteration,
            )

        time.sleep(settings.cluster_schedule)


def main() -> None:
    """Entry point for scheduled clustering."""
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as exc:
        log_exception(logger, ErrorCategory.SYSTEM, "Scheduler crashed", exc)
        raise


if __name__ == "__main__":
    main()
