from __future__ import annotations

import asyncio
import time

import httpx
from bs4 import BeautifulSoup
from readability import Document

from chronicle.config import settings
from chronicle.logging import (
    ErrorCategory,
    get_logger,
    log_exception,
    log_metric,
    log_with_context,
)
from chronicle.storage import db
from chronicle.utils import retry_with_backoff

logger = get_logger(__name__)

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


@retry_with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
async def fetch_json(client: httpx.AsyncClient, url: str):
    """Fetch JSON from URL with retry logic."""
    response = await client.get(url, timeout=settings.collector_timeout)
    response.raise_for_status()
    return response.json()


def extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    try:
        doc = Document(html)
        content = doc.summary()
        soup = BeautifulSoup(content, "lxml")
        return soup.get_text(" ", strip=True)
    except Exception as exc:
        log_with_context(
            logger,
            "DEBUG",
            "Readability extraction failed",
            error=str(exc),
        )
        try:
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(" ", strip=True)
        except Exception as fallback_exc:
            log_with_context(
                logger,
                "DEBUG",
                "BeautifulSoup extraction failed",
                error=str(fallback_exc),
            )
            return ""


async def fetch_article_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch and extract article text with error handling."""
    try:
        response = await client.get(
            url,
            timeout=settings.collector_timeout,
            follow_redirects=True,
        )
        response.raise_for_status()
        return extract_text(response.text)
    except Exception as exc:
        log_with_context(
            logger,
            "DEBUG",
            "Failed to fetch article",
            url=url,
            error=str(exc),
        )
        return ""


async def loop_collect(interval: int | None = None):
    """Main collection loop."""
    if interval is None:
        interval = settings.collector_interval

    logger.info(
        "Starting collector (interval=%ss, limit=%s)",
        interval,
        settings.collector_story_limit,
    )

    conn = db.connect()
    consecutive_failures = 0

    async with httpx.AsyncClient() as client:
        iteration = 0
        while True:
            iteration += 1
            processed = 0
            errors = 0

            try:
                logger.info("Fetching top stories (iteration %s)", iteration)
                top = await fetch_json(client, HN_TOP)
                logger.info(
                    "Found %s stories, processing top %s",
                    len(top),
                    settings.collector_story_limit,
                )

                for item_id in top[: settings.collector_story_limit]:
                    if errors >= settings.collector_max_story_errors:
                        logger.warning(
                            "Reached story failure budget (%s); ending cycle early",
                            settings.collector_max_story_errors,
                        )
                        break

                    try:
                        item = await fetch_json(client, HN_ITEM.format(id=item_id))
                        if not item or item.get("type") != "story":
                            continue

                        title = item.get("title", "")
                        url = (
                            item.get("url")
                            or f"https://news.ycombinator.com/item?id={item_id}"
                        )
                        text = await fetch_article_text(client, url)

                        doc = {
                            "source": "hn",
                            "external_id": str(item_id),
                            "title": title,
                            "url": url,
                            "text": text or title,
                            "ts": int(item.get("time", time.time())),
                        }

                        db.insert_doc(conn, doc)
                        processed += 1

                    except Exception as exc:
                        errors += 1
                        log_with_context(
                            logger,
                            "WARNING",
                            "Failed to process story",
                            item_id=item_id,
                            error=str(exc),
                        )

                consecutive_failures = 0
                log_metric(
                    logger,
                    "collector.docs_processed",
                    processed,
                    iteration=iteration,
                )
                log_metric(
                    logger,
                    "collector.story_errors",
                    errors,
                    iteration=iteration,
                )
                logger.info(
                    "Iteration %s complete: %s stored, %s errors",
                    iteration,
                    processed,
                    errors,
                )

            except Exception as exc:
                consecutive_failures += 1
                log_exception(
                    logger,
                    ErrorCategory.NETWORK,
                    "Collection iteration failed",
                    exc,
                    iteration=iteration,
                    consecutive_failures=consecutive_failures,
                )

                if consecutive_failures >= settings.collector_max_consecutive_failures:
                    logger.warning(
                        "Failure threshold reached (%s); cooling down for %ss",
                        settings.collector_max_consecutive_failures,
                        settings.collector_failure_cooldown,
                    )
                    await asyncio.sleep(settings.collector_failure_cooldown)

            await asyncio.sleep(interval)


def main():
    """Entry point for the collector CLI."""
    try:
        asyncio.run(loop_collect())
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    except Exception as exc:
        log_exception(logger, ErrorCategory.SYSTEM, "Collector crashed", exc)
        raise


if __name__ == "__main__":
    main()
