from __future__ import annotations
from fastapi import FastAPI, HTTPException
from chronicle.storage import db
from chronicle.timeline.summarize import summarize

app = FastAPI(title="Chronicle API", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/events")
def events():
    conn = db.connect()
    clusters = db.get_clusters(conn)
    out = []
    for cid, payload in clusters.items():
        docs = payload["docs"]
        summary = summarize(docs, max_sentences=3)
        out.append({
            "cluster_id": cid,
            "n_docs": len(docs),
            "score": payload["score"],
            "summary": summary,
            "sample": [{"title": d["title"], "url": d["url"]} for d in docs[:3]]
        })
    out.sort(key=lambda x: (x["n_docs"], x["score"]), reverse=True)
    return out

@app.get("/events/{cluster_id}")
def event(cluster_id: str):
    conn = db.connect()
    docs = db.get_cluster_docs(conn, cluster_id)
    if not docs:
        raise HTTPException(status_code=404, detail="cluster not found")
    summary = summarize(docs, max_sentences=5)
    return {"cluster_id": cluster_id, "summary": summary, "docs": docs}

def main():
    """Entry point for the API CLI."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
