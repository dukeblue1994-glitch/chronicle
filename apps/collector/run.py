from __future__ import annotations
import asyncio, time
import httpx
from bs4 import BeautifulSoup
from readability import Document
from chronicle.storage import db

HN_TOP = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"

async def fetch_json(client, url):
    r = await client.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def extract_text(html: str) -> str:
    try:
        doc = Document(html)
        content = doc.summary()
        soup = BeautifulSoup(content, "lxml")
        return soup.get_text(" ", strip=True)
    except Exception:
        try:
            soup = BeautifulSoup(html, "lxml")
            return soup.get_text(" ", strip=True)
        except Exception:
            return ""

async def fetch_article_text(client, url: str) -> str:
    try:
        r = await client.get(url, timeout=20)
        r.raise_for_status()
        return extract_text(r.text)
    except Exception:
        return ""

async def loop_collect(interval: int = 60):
    conn = db.connect()
    async with httpx.AsyncClient() as client:
        while True:
            try:
                top = await fetch_json(client, HN_TOP)
                for item_id in top[:60]:
                    item = await fetch_json(client, HN_ITEM.format(id=item_id))
                    if not item or item.get("type") != "story":
                        continue
                    title = item.get("title","")
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
                    try:
                        db.insert_doc(conn, doc)
                    except Exception:
                        pass
                await asyncio.sleep(interval)
            except Exception:
                await asyncio.sleep(interval)

def main():
    """Entry point for the collector CLI."""
    asyncio.run(loop_collect())

if __name__ == "__main__":
    main()
