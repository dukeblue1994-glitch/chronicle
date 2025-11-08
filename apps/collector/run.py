from __future__ import annotations
import asyncio
import time
import logging
import httpx
from bs4 import BeautifulSoup
from readability import Document
from chronicle.storage import db
from chronicle.config import settings
from chronicle.utils import retry_with_backoff

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


@retry_with_backoff(max_retries=3, exceptions=(httpx.HTTPError,))
async def fetch_json(client: httpx.AsyncClient, url: str):
    """Fetch JSON from URL with retry logic."""
    r = await client.get(url, timeout=settings.collector_timeout)
    r.raise_for_status()
    return r.json()


def extract_text(html: str) -> str:
    """Extract readable text from HTML."""
    try:
        doc = Document(html)
        content = doc.summary()
        soup = BeautifulSoup(content, "lxml")
        return soup.get_text(" ", strip=True)
    except Exception as e:
        logger.debug(f"Readability extraction failed: {e}")
        try:
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(" ", strip=True)
        except Exception as e:
            logger.debug(f"BeautifulSoup extraction failed: {e}")
            return ""


async def fetch_article_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch and extract article text with error handling."""
    try:
        r = await client.get(url, timeout=settings.collector_timeout, follow_redirects=True)
        r.raise_for_status()
        return extract_text(r.text)
    except Exception as e:
        logger.debug(f"Failed to fetch article from {url}: {e}")
        return ""


async def loop_collect(interval: int | None = None):
    """Main collection loop."""
    if interval is None:
        interval = settings.collector_interval
    
    logger.info(f"Starting collector (interval={interval}s, limit={settings.collector_story_limit})")
    conn = db.connect()
    
    async with httpx.AsyncClient() as client:
        iteration = 0
        while True:
            iteration += 1
            try:
                logger.info(f"Fetching top stories (iteration {iteration})")
                top = await fetch_json(client, HN_TOP)
                logger.info(f"Found {len(top)} stories, processing top {settings.collector_story_limit}")
                
                processed = 0
                errors = 0
                
                for item_id in top[:settings.collector_story_limit]:
                    try:
                        item = await fetch_json(client, HN_ITEM.format(id=item_id))
                        if not item or item.get("type") != "story":
                            continue
                        
                        title = item.get("title", "")
                        url = item.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                        text = await fetch_article_text(client, url)
                        
                        doc = {
                            "source": "hn",
                            "external_id": str(item_id),
                            "title": title,
                            "url": url,
                            "text": text or title,
                            "ts": int(item.get("time", time.time()))
                        }
                        
                        db.insert_doc(conn, doc)
                        processed += 1
                        logger.debug(f"Stored story {item_id}: {title[:50]}")
                        
                    except Exception as e:
                        errors += 1
                        logger.warning(f"Failed to process story {item_id}: {e}")
                
                logger.info(f"Iteration {iteration} complete: {processed} stored, {errors} errors")
                
            except Exception as e:
                logger.error(f"Collection iteration {iteration} failed: {e}", exc_info=True)
            
            logger.debug(f"Sleeping for {interval}s")
            await asyncio.sleep(interval)


def main():
    """Entry point for the collector CLI."""
    try:
        asyncio.run(loop_collect())
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    except Exception as e:
        logger.error(f"Collector crashed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
