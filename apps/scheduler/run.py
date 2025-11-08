"""Scheduled clustering job runner."""
from __future__ import annotations
import logging
import time
from chronicle.cluster.pipeline import run_batch
from chronicle.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_scheduler():
    """Run clustering on a schedule."""
    if settings.cluster_schedule <= 0:
        logger.info("Scheduling disabled (CHRONICLE_CLUSTER_SCHEDULE=0)")
        logger.info("Run clustering manually with: chronicle-cluster")
        return
    
    logger.info(f"Starting scheduled clustering (interval={settings.cluster_schedule}s)")
    
    iteration = 0
    while True:
        iteration += 1
        try:
            logger.info(f"Running clustering iteration {iteration}")
            n_clusters = run_batch()
            logger.info(f"Iteration {iteration} complete: {n_clusters} clusters")
        except Exception as e:
            logger.error(f"Clustering iteration {iteration} failed: {e}", exc_info=True)
        
        logger.debug(f"Sleeping for {settings.cluster_schedule}s")
        time.sleep(settings.cluster_schedule)


def main():
    """Entry point for scheduled clustering."""
    try:
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
    except Exception as e:
        logger.error(f"Scheduler crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
