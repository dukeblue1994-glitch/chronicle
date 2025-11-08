from __future__ import annotations
import logging
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from chronicle.storage import db
from chronicle.timeline.summarize import summarize
from chronicle.config import settings

# Set up logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Chronicle API",
    version="0.1.0",
    description="Real-time event clustering and timeline builder API",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


@app.get("/health", tags=["System"])
def health():
    """Health check endpoint."""
    return {"ok": True, "version": "0.1.0"}


@app.get("/events", tags=["Events"])
def events(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    min_docs: int = Query(2, ge=1, description="Minimum documents per cluster"),
    sort_by: str = Query("size", regex="^(size|score)$", description="Sort by size or score")
):
    """
    Get all event clusters with summaries.
    
    Returns a list of event clusters ranked by size and confidence,
    with extractive summaries and sample documents.
    """
    try:
        conn = db.connect()
        clusters = db.get_clusters(conn)
        conn.close()
        
        out = []
        for cid, payload in clusters.items():
            docs = payload["docs"]
            
            # Filter by minimum docs
            if len(docs) < min_docs:
                continue
            
            summary = summarize(docs, max_sentences=settings.summary_max_sentences)
            out.append({
                "cluster_id": cid,
                "n_docs": len(docs),
                "score": payload["score"],
                "summary": summary,
                "sample": [{"title": d["title"], "url": d["url"]} for d in docs[:3]]
            })
        
        # Sort
        if sort_by == "size":
            out.sort(key=lambda x: (x["n_docs"], x["score"]), reverse=True)
        else:
            out.sort(key=lambda x: x["score"], reverse=True)
        
        # Limit
        out = out[:limit]
        
        logger.info(f"Returned {len(out)} events")
        return out
        
    except Exception as e:
        logger.error(f"Failed to get events: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve events")


@app.get("/events/{cluster_id}", tags=["Events"])
def event(cluster_id: str):
    """
    Get detailed information about a specific event cluster.
    
    Returns the cluster with all associated documents and a detailed summary.
    """
    try:
        conn = db.connect()
        docs = db.get_cluster_docs(conn, cluster_id)
        conn.close()
        
        if not docs:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        summary = summarize(docs, max_sentences=settings.summary_detail_sentences)
        
        logger.info(f"Returned cluster {cluster_id} with {len(docs)} docs")
        return {"cluster_id": cluster_id, "summary": summary, "docs": docs}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cluster {cluster_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cluster")


def main():
    """Entry point for the API CLI."""
    import uvicorn
    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.api_reload
    )
