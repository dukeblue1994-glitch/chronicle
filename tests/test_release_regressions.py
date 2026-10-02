"""Regression coverage for upgrades, empty inputs, and batch consistency."""

import sqlite3
import sys
from unittest.mock import Mock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from chronicle.cluster import algos, pipeline
from chronicle.config import settings
from chronicle.nlp import embedding
from chronicle.storage import db
from chronicle.timeline.summarize import summarize


@pytest.mark.parametrize("version", [0, 1, 2])
def test_legacy_schema_upgrade_preserves_newest_document(temp_db, version):
    conn = sqlite3.connect(temp_db)
    conn.executescript("""
        CREATE TABLE docs (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
          external_id TEXT, title TEXT, url TEXT, text TEXT, ts INTEGER);
        CREATE TABLE vectors (doc_id INTEGER PRIMARY KEY, dim INTEGER, vec BLOB,
          FOREIGN KEY(doc_id) REFERENCES docs(id));
        CREATE TABLE clusters (doc_id INTEGER, cluster_id TEXT, score REAL, ts INTEGER,
          FOREIGN KEY(doc_id) REFERENCES docs(id));
        INSERT INTO docs VALUES(1,'hn','42','old',NULL,'old',1);
        INSERT INTO docs VALUES(2,'hn','42','new',NULL,'new',2);
        INSERT INTO vectors VALUES(1,1,X'01');
        INSERT INTO vectors VALUES(2,1,X'02');
        INSERT INTO clusters VALUES(1,'old',0.5,1);
        INSERT INTO clusters VALUES(2,'new',0.9,2);
    """)
    if version == 2:
        # Version 2 had already deduplicated documents, but retained legacy FKs.
        conn.execute("DELETE FROM clusters WHERE doc_id=1")
        conn.execute("DELETE FROM vectors WHERE doc_id=1")
        conn.execute("DELETE FROM docs WHERE id=1")
    conn.execute(f"PRAGMA user_version={version}")
    conn.commit()
    conn.close()
    conn = db.connect()
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert [row["title"] for row in conn.execute("SELECT title FROM docs")] == ["new"]
    assert conn.execute("SELECT doc_id FROM vectors").fetchone()[0] == 2
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.execute("DELETE FROM docs WHERE id=2")
    assert conn.execute("SELECT COUNT(*) FROM vectors").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM clusters").fetchone()[0] == 0
    conn.commit()
    conn.close()
    db.connect().close()  # Migration is repeatable.


def test_migration_rolls_back_on_failure(temp_db, monkeypatch):
    conn = sqlite3.connect(temp_db)
    conn.execute("CREATE TABLE marker(value TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(db, "_migrate_to_v3", Mock(side_effect=RuntimeError("failure")))
    with pytest.raises(RuntimeError):
        db.connect()
    conn = sqlite3.connect(temp_db)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 0
    assert (
        conn.execute("SELECT name FROM sqlite_master WHERE name='docs'").fetchone()
        is None
    )
    conn.close()


def test_document_update_invalidates_derived_data(temp_db, sample_docs):
    conn = db.connect()
    doc = sample_docs[0]
    doc_id = db.insert_doc(conn, doc)
    db.upsert_cluster(conn, doc_id, "old", 0.9)
    db.insert_doc(conn, doc)
    assert db.get_cluster_docs(conn, "old")
    updated = {**doc, "title": "Updated title", "text": "Updated text"}
    assert db.insert_doc(conn, updated) == doc_id
    stored = db.get_recent_docs(conn)[0]
    assert (stored["title"], stored["text"]) == ("Updated title", "Updated text")
    assert db.get_clusters(conn) == {}
    conn.close()


def test_assignment_replacement_rolls_back(temp_db, sample_docs):
    conn = db.connect()
    doc_id = db.insert_doc(conn, sample_docs[0])
    db.upsert_cluster(conn, doc_id, "original", 0.9)
    with pytest.raises(sqlite3.IntegrityError):
        db.replace_assignments(conn, [doc_id], [(9999, "invalid", 1.0)])
    assert db.get_cluster_docs(conn, "original")
    conn.close()


@pytest.mark.parametrize("texts", [["a", "!"], ["", "  "], ["...", "!?"], ["你", "好"]])
def test_tfidf_handles_sparse_vocabulary(texts, monkeypatch):
    monkeypatch.setattr(settings, "embedding_backend", "tfidf")
    vectors = embedding.encode(texts)
    assert vectors.shape[0] == len(texts)
    assert np.isfinite(vectors).all()


def test_explicit_tfidf_does_not_load_a_model(monkeypatch):
    monkeypatch.setattr(settings, "embedding_backend", "tfidf")
    monkeypatch.setattr(embedding, "_ensure_sbert", Mock(side_effect=AssertionError))
    assert embedding.encode(["local text"]).shape[0] == 1


def test_semantic_mode_reports_missing_dependency(monkeypatch):
    monkeypatch.setattr(settings, "embedding_backend", "semantic")
    monkeypatch.setattr(embedding, "_model", None)
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    with pytest.raises(RuntimeError, match="Semantic model unavailable"):
        embedding.encode(["hello"])


@pytest.mark.parametrize("minimum,expected", [(1, 0), (2, -1), (3, -1)])
def test_singleton_respects_minimum(minimum, expected):
    labels, scores = algos.cluster_embeddings(np.array([[1.0, 0.0]]), minimum)
    assert labels.tolist() == [expected]
    assert scores.tolist() == [1.0 if expected == 0 else 0.0]


def test_fallback_removes_small_groups(monkeypatch):
    monkeypatch.setitem(sys.modules, "hdbscan", None)
    vectors = np.array([[1, 0], [1, 0.01], [0.01, 1], [0, 1], [-1, 0]])
    labels, scores = algos.cluster_embeddings(vectors, min_cluster_size=2)
    assert labels[-1] == -1
    assert scores[-1] == 0
    assert set(np.bincount(labels[labels >= 0])) == {2}


def test_zero_vectors_are_noise():
    labels, scores = algos.cluster_embeddings(np.zeros((4, 1)), min_cluster_size=1)
    assert np.all(labels == -1)
    assert np.all(scores == 0)


@pytest.mark.parametrize("vectors", [np.array([1, 2]), np.array([[float("nan")]])])
def test_invalid_vectors_rejected(vectors):
    with pytest.raises(ValueError):
        algos.cluster_embeddings(vectors)


def test_empty_titles_not_collapsed():
    assert algos.deduplicate(["", "", " "]) == [0, 1, 2]


def test_event_identity_independent_of_document_order():
    assert pipeline._cluster_id([1, 2, 3]) == pipeline._cluster_id([3, 1, 2])
    assert pipeline._cluster_id([1, 2]) != pipeline._cluster_id([1, 3])


def test_batch_clears_noise_assignments(temp_db, sample_docs, monkeypatch):
    conn = db.connect()
    for doc in sample_docs:
        doc_id = db.insert_doc(conn, doc)
        db.upsert_cluster(conn, doc_id, "stale", 1.0)
    monkeypatch.setattr(pipeline, "encode", lambda texts: np.ones((len(texts), 2)))
    monkeypatch.setattr(
        pipeline,
        "cluster_embeddings",
        lambda X, **kw: (np.full(len(X), -1), np.zeros(len(X))),
    )
    assert pipeline.run_batch() == 0
    assert db.get_clusters(conn) == {}
    conn.close()


def test_punctuation_summary_does_not_crash():
    assert summarize([{"text": "! ! ! ! ! !"}], max_sentences=2) == "! !"
    assert summarize([{"text": "text"}], max_sentences=0) == ""


def test_search_timeline_and_stats(temp_db, sample_docs):
    conn = db.connect()
    for doc in sample_docs:
        doc_id = db.insert_doc(conn, doc)
        db.upsert_cluster(conn, doc_id, "event", 0.9)
    conn.close()
    client = TestClient(app)
    result = client.get(
        "/events", params={"q": "AI", "source": "test", "since": 1000000001}
    )
    assert result.status_code == 200
    assert result.json()[0]["sources"] == ["test"]
    assert result.json()[0]["n_docs"] == 3  # Full context, even when one doc matches.
    assert client.get("/events?q=absent").json() == []
    assert client.get("/events?offset=1").json() == []
    assert client.get("/events?since=10&until=1").status_code == 422
    assert client.get("/events?sort_by=invalid").status_code == 422
    timeline = client.get("/events/event/timeline").json()["docs"]
    assert [doc["ts"] for doc in timeline] == sorted(doc["ts"] for doc in timeline)
    assert client.get("/events/missing/timeline").status_code == 404
    stats = client.get("/stats").json()
    assert stats["documents"] == 3
    assert stats["clustered_documents"] == 3
    assert stats["events"] == 1
    assert client.get("/ready").status_code == 200


def test_readiness_reports_database_failure(temp_db, monkeypatch):
    monkeypatch.setattr(
        db, "connect", Mock(side_effect=sqlite3.OperationalError("unavailable"))
    )
    assert TestClient(app).get("/ready").status_code == 503
