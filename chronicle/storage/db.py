from __future__ import annotations

import sqlite3
import time
from typing import Any, Dict, List

from chronicle.config import get_db_path
from chronicle.logging import ErrorCategory, get_logger, log_exception

logger = get_logger(__name__)
SCHEMA_VERSION = 2


def _ensure_base_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS docs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "source TEXT,"
        "external_id TEXT,"
        "title TEXT,"
        "url TEXT,"
        "text TEXT,"
        "ts INTEGER"
        ");"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS vectors ("
        "doc_id INTEGER PRIMARY KEY,"
        "dim INTEGER,"
        "vec BLOB,"
        "FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE"
        ");"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS clusters ("
        "doc_id INTEGER,"
        "cluster_id TEXT,"
        "score REAL,"
        "ts INTEGER,"
        "FOREIGN KEY(doc_id) REFERENCES docs(id) ON DELETE CASCADE"
        ");"
    )
    conn.commit()


def _migrate_to_v1(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_ts ON docs(ts DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_docs_source ON docs(source)")
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_clusters_cluster_id ON clusters(cluster_id)"
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clusters_ts ON clusters(ts DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_clusters_doc_id ON clusters(doc_id)")
    conn.commit()


def _migrate_to_v2(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    # Keep newest row per (source, external_id) pair for dedupe safety.
    cur.execute(
        "DELETE FROM docs "
        "WHERE external_id IS NOT NULL "
        "AND rowid NOT IN ("
        "  SELECT MAX(rowid) FROM docs "
        "  WHERE external_id IS NOT NULL "
        "  GROUP BY source, external_id"
        ")"
    )

    # Keep newest cluster mapping per document for one-to-one assignments.
    cur.execute(
        "DELETE FROM clusters "
        "WHERE rowid NOT IN ("
        "  SELECT MAX(rowid) FROM clusters GROUP BY doc_id"
        ")"
    )

    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_docs_source_external_id_unique "
        "ON docs(source, external_id)"
    )
    cur.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_clusters_doc_id_unique "
        "ON clusters(doc_id)"
    )
    conn.commit()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    _ensure_base_schema(conn)

    cur = conn.cursor()
    current_version = cur.execute("PRAGMA user_version").fetchone()[0]

    if current_version < 1:
        _migrate_to_v1(conn)
        cur.execute("PRAGMA user_version=1")
        conn.commit()

    if current_version < 2:
        _migrate_to_v2(conn)
        cur.execute("PRAGMA user_version=2")
        conn.commit()


def connect() -> sqlite3.Connection:
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        _ensure_schema(conn)
    except Exception as exc:
        log_exception(
            logger,
            ErrorCategory.DATABASE,
            "Failed to ensure database schema",
            exc,
            db_path=str(db_path),
        )
        raise

    return conn


def insert_doc(conn: sqlite3.Connection, doc: Dict[str, Any]) -> int:
    cur = conn.cursor()
    source = doc.get("source")
    external_id = doc.get("external_id")

    cur.execute(
        "INSERT INTO docs(source, external_id, title, url, text, ts) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(source, external_id) DO UPDATE SET "
        "title=excluded.title, "
        "url=excluded.url, "
        "text=excluded.text, "
        "ts=excluded.ts",
        (
            source,
            external_id,
            doc.get("title"),
            doc.get("url"),
            doc.get("text"),
            int(doc.get("ts", time.time())),
        ),
    )

    if source is not None and external_id is not None:
        row = conn.execute(
            "SELECT id FROM docs WHERE source=? AND external_id=?",
            (source, external_id),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to resolve upserted document id")
        doc_id = int(row["id"])
    else:
        if cur.lastrowid is None:
            raise RuntimeError("Failed to resolve inserted document id")
        doc_id = int(cur.lastrowid)

    conn.commit()
    return doc_id


def get_recent_docs(conn: sqlite3.Connection, limit: int = 500) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT id, source, external_id, title, url, text, ts "
        "FROM docs ORDER BY ts DESC LIMIT ?",
        (limit,),
    )
    return [dict(row) for row in cur.fetchall()]


def upsert_cluster(
    conn: sqlite3.Connection,
    doc_id: int,
    cluster_id: str,
    score: float,
) -> None:
    ts = int(time.time())
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clusters(doc_id, cluster_id, score, ts) VALUES(?,?,?,?) "
        "ON CONFLICT(doc_id) DO UPDATE SET "
        "cluster_id=excluded.cluster_id, "
        "score=excluded.score, "
        "ts=excluded.ts",
        (doc_id, cluster_id, score, ts),
    )
    conn.commit()


def get_clusters(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT c.cluster_id, d.id, d.title, d.url, d.text, d.ts, c.score "
        "FROM clusters c JOIN docs d ON d.id = c.doc_id "
        "ORDER BY d.ts DESC"
    )

    out: Dict[str, Dict[str, Any]] = {}
    for row in cur.fetchall():
        cid = row["cluster_id"]
        out.setdefault(cid, {"docs": [], "score_sum": 0.0, "n": 0})
        out[cid]["docs"].append(
            {
                "id": row["id"],
                "title": row["title"],
                "url": row["url"],
                "text": row["text"],
                "ts": row["ts"],
                "score": row["score"],
            }
        )
        out[cid]["score_sum"] += float(row["score"])
        out[cid]["n"] += 1

    for cid, payload in out.items():
        payload["score"] = payload["score_sum"] / max(1, payload["n"])
        del payload["score_sum"]
        del payload["n"]

    return out


def get_cluster_docs(conn: sqlite3.Connection, cluster_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT d.id, d.title, d.url, d.text, d.ts, c.score "
        "FROM clusters c JOIN docs d ON d.id = c.doc_id "
        "WHERE c.cluster_id=? ORDER BY d.ts DESC",
        (cluster_id,),
    )
    return [dict(row) for row in cur.fetchall()]
