from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from chronicle import __version__
from chronicle.config import settings
from chronicle.logging import ErrorCategory, get_logger, log_exception
from chronicle.storage import db
from chronicle.timeline.summarize import summarize

logger = get_logger(__name__)


class EndpointMap(BaseModel):
    health: str
    events: str
    event_detail: str
    stats: str = "/stats"
    readiness: str = "/ready"


class RootResponse(BaseModel):
    name: str
    version: str
    description: str
    docs: str
    endpoints: EndpointMap


class HealthResponse(BaseModel):
    ok: bool
    version: str


class EventSample(BaseModel):
    title: str | None
    url: str | None


class EventSummary(BaseModel):
    cluster_id: str
    n_docs: int
    score: float
    summary: str
    sample: list[EventSample]
    first_seen: int
    last_seen: int
    sources: list[str]


class EventDoc(BaseModel):
    source: str | None = None
    id: int
    title: str | None
    url: str | None
    text: str | None
    ts: int
    score: float


class EventDetail(BaseModel):
    cluster_id: str
    summary: str
    docs: list[EventDoc]


app = FastAPI(
    title=f"{settings.app_name} API",
    version=__version__,
    description="Real-time event clustering and timeline builder API",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    log_exception(
        logger,
        ErrorCategory.API,
        "Unhandled API exception",
        exc,
        path=str(request.url.path),
        method=request.method,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/", tags=["System"], response_model=RootResponse)
def root() -> RootResponse:
    """Root endpoint with API information."""
    return RootResponse(
        name=f"{settings.app_name} API",
        version=__version__,
        description="Real-time event clustering and timeline builder",
        docs="/docs",
        endpoints=EndpointMap(
            health="/health",
            events="/events",
            event_detail="/events/{cluster_id}",
        ),
    )


@app.get("/health", tags=["System"], response_model=HealthResponse)
def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(ok=True, version=__version__)


class CorpusStats(BaseModel):
    documents: int
    events: int
    clustered_documents: int
    first_seen: int | None
    last_seen: int | None
    sources: dict[str, int]
    schema_version: int


@app.get("/ready", tags=["System"], response_model=HealthResponse)
def ready() -> HealthResponse:
    """Check that the local database is available and its schema is usable."""
    try:
        conn = db.connect()
        try:
            conn.execute("SELECT id FROM docs LIMIT 1").fetchall()
        finally:
            conn.close()
    except Exception as exc:
        log_exception(logger, ErrorCategory.DATABASE, "Readiness check failed", exc)
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return HealthResponse(ok=True, version=__version__)


@app.get("/stats", tags=["System"], response_model=CorpusStats)
def stats() -> CorpusStats:
    conn = db.connect()
    try:
        return CorpusStats(**db.get_stats(conn))
    finally:
        conn.close()


@app.get("/events", tags=["Events"], response_model=list[EventSummary])
def events(
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of events to return",
    ),
    min_docs: int = Query(2, ge=1, description="Minimum documents per cluster"),
    sort_by: Literal["size", "score", "latest"] = Query("size"),
    offset: int = Query(0, ge=0, description="Skip this many matching events"),
    q: str | None = Query(
        None, max_length=200, description="Search event titles and text"
    ),
    source: str | None = Query(None, max_length=100),
    since: int | None = Query(None, ge=0, description="Earliest publication timestamp"),
    until: int | None = Query(None, ge=0, description="Latest publication timestamp"),
) -> list[EventSummary]:
    """Filter events by matching documents; summaries retain the full event context."""
    if since is not None and until is not None and since > until:
        raise HTTPException(status_code=422, detail="since must be at most until")
    try:
        conn = db.connect()
        try:
            clusters = db.get_clusters(conn)
        finally:
            conn.close()

        out: list[dict[str, Any]] = []
        for cid, payload in clusters.items():
            docs = payload["docs"]
            if len(docs) < min_docs:
                continue

            matching = [
                doc
                for doc in docs
                if (source is None or doc.get("source") == source)
                and (since is None or doc["ts"] >= since)
                and (until is None or doc["ts"] <= until)
                and (
                    q is None
                    or q.casefold()
                    in f"{doc.get('title') or ''} {doc.get('text') or ''}".casefold()
                )
            ]
            if not matching:
                continue
            summary = summarize(docs, max_sentences=settings.summary_max_sentences)
            out.append(
                {
                    "cluster_id": cid,
                    "n_docs": len(docs),
                    "score": float(payload["score"]),
                    "first_seen": min(doc["ts"] for doc in docs),
                    "last_seen": max(doc["ts"] for doc in docs),
                    "sources": sorted({doc.get("source") or "unknown" for doc in docs}),
                    "summary": summary,
                    "sample": [
                        {"title": d.get("title"), "url": d.get("url")} for d in docs[:3]
                    ],
                }
            )

        if sort_by == "size":
            out.sort(key=lambda x: (-x["n_docs"], -x["score"], x["cluster_id"]))
        elif sort_by == "score":
            out.sort(key=lambda x: (-x["score"], -x["n_docs"], x["cluster_id"]))
        else:
            out.sort(key=lambda x: (-x["last_seen"], x["cluster_id"]))

        out = out[offset : offset + limit]
        logger.info("Returned %s events", len(out))
        return [EventSummary(**event) for event in out]

    except Exception as exc:
        log_exception(logger, ErrorCategory.API, "Failed to get events", exc)
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@app.get("/events/{cluster_id}", tags=["Events"], response_model=EventDetail)
def event(cluster_id: str) -> EventDetail:
    """Get detailed information about a specific event cluster."""
    try:
        conn = db.connect()
        try:
            docs = db.get_cluster_docs(conn, cluster_id)
        finally:
            conn.close()

        if not docs:
            raise HTTPException(status_code=404, detail="Cluster not found")

        summary = summarize(docs, max_sentences=settings.summary_detail_sentences)
        logger.info("Returned cluster %s with %s docs", cluster_id, len(docs))

        normalized_docs = [EventDoc(**doc) for doc in docs]
        return EventDetail(cluster_id=cluster_id, summary=summary, docs=normalized_docs)

    except HTTPException:
        raise
    except Exception as exc:
        log_exception(
            logger,
            ErrorCategory.API,
            "Failed to get cluster",
            exc,
            cluster_id=cluster_id,
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve cluster")


@app.get("/events/{cluster_id}/timeline", tags=["Events"], response_model=EventDetail)
def timeline(cluster_id: str) -> EventDetail:
    """Return source-linked event documents in publication order."""
    result = event(cluster_id)
    result.docs.sort(key=lambda doc: (doc.ts, doc.id))
    return result


def main():
    """Entry point for the API CLI."""
    import uvicorn

    logger.info("Starting API server on %s:%s", settings.api_host, settings.api_port)
    uvicorn.run(
        "apps.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
