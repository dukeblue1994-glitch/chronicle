"""Tests for database operations."""
import pytest
from chronicle.storage import db


class TestDatabase:
    """Tests for database operations."""
    
    def test_connect_creates_tables(self, temp_db):
        """Test that connect creates necessary tables."""
        conn = db.connect()
        cursor = conn.cursor()
        
        # Check that tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        assert 'docs' in tables
        assert 'vectors' in tables
        assert 'clusters' in tables
        
        conn.close()
    
    def test_insert_doc(self, temp_db, sample_docs):
        """Test inserting a document."""
        conn = db.connect()
        doc_id = db.insert_doc(conn, sample_docs[0])
        
        assert isinstance(doc_id, int)
        assert doc_id > 0
        
        conn.close()
    
    def test_insert_multiple_docs(self, temp_db, sample_docs):
        """Test inserting multiple documents."""
        conn = db.connect()
        ids = []
        for doc in sample_docs:
            doc_id = db.insert_doc(conn, doc)
            ids.append(doc_id)
        
        assert len(ids) == len(sample_docs)
        assert len(set(ids)) == len(ids)  # All unique
        
        conn.close()
    
    def test_get_recent_docs(self, temp_db, sample_docs):
        """Test retrieving recent documents."""
        conn = db.connect()
        
        # Insert documents
        for doc in sample_docs:
            db.insert_doc(conn, doc)
        
        # Retrieve them
        docs = db.get_recent_docs(conn, limit=10)
        
        assert len(docs) == len(sample_docs)
        assert all('id' in doc for doc in docs)
        assert all('title' in doc for doc in docs)
        
        conn.close()
    
    def test_get_recent_docs_limit(self, temp_db, sample_docs):
        """Test limit parameter in get_recent_docs."""
        conn = db.connect()
        
        # Insert documents
        for doc in sample_docs:
            db.insert_doc(conn, doc)
        
        # Retrieve with limit
        docs = db.get_recent_docs(conn, limit=2)
        
        assert len(docs) == 2
        
        conn.close()
    
    def test_upsert_cluster(self, temp_db, sample_docs):
        """Test upserting cluster assignments."""
        conn = db.connect()
        
        # Insert a document
        doc_id = db.insert_doc(conn, sample_docs[0])
        
        # Assign to cluster
        db.upsert_cluster(conn, doc_id, "cluster-1", 0.95)
        
        # Check it was inserted
        cursor = conn.cursor()
        cursor.execute("SELECT cluster_id, score FROM clusters WHERE doc_id=?", (doc_id,))
        result = cursor.fetchone()
        
        assert result is not None
        assert result[0] == "cluster-1"
        assert abs(result[1] - 0.95) < 0.01
        
        conn.close()
    
    def test_upsert_cluster_updates(self, temp_db, sample_docs):
        """Test that upsert updates existing cluster assignments."""
        conn = db.connect()
        
        # Insert a document
        doc_id = db.insert_doc(conn, sample_docs[0])
        
        # Assign to cluster
        db.upsert_cluster(conn, doc_id, "cluster-1", 0.80)
        
        # Update assignment
        db.upsert_cluster(conn, doc_id, "cluster-2", 0.90)
        
        # Check it was updated
        cursor = conn.cursor()
        cursor.execute("SELECT cluster_id, score FROM clusters WHERE doc_id=?", (doc_id,))
        results = cursor.fetchall()
        
        assert len(results) == 1  # Should only have one entry
        assert results[0][0] == "cluster-2"
        
        conn.close()
    
    def test_get_clusters(self, temp_db, sample_docs):
        """Test retrieving clusters."""
        conn = db.connect()
        
        # Insert documents
        doc_ids = [db.insert_doc(conn, doc) for doc in sample_docs]
        
        # Assign to clusters
        db.upsert_cluster(conn, doc_ids[0], "cluster-ai", 0.9)
        db.upsert_cluster(conn, doc_ids[1], "cluster-ai", 0.85)
        db.upsert_cluster(conn, doc_ids[2], "cluster-space", 0.95)
        
        # Get clusters
        clusters = db.get_clusters(conn)
        
        assert len(clusters) == 2
        assert "cluster-ai" in clusters
        assert "cluster-space" in clusters
        assert len(clusters["cluster-ai"]["docs"]) == 2
        assert len(clusters["cluster-space"]["docs"]) == 1
        
        conn.close()
    
    def test_get_cluster_docs(self, temp_db, sample_docs):
        """Test retrieving documents for a specific cluster."""
        conn = db.connect()
        
        # Insert documents
        doc_ids = [db.insert_doc(conn, doc) for doc in sample_docs]
        
        # Assign to cluster
        db.upsert_cluster(conn, doc_ids[0], "cluster-test", 0.9)
        db.upsert_cluster(conn, doc_ids[1], "cluster-test", 0.85)
        
        # Get cluster docs
        docs = db.get_cluster_docs(conn, "cluster-test")
        
        assert len(docs) == 2
        assert all('title' in doc for doc in docs)
        assert all('score' in doc for doc in docs)
        
        conn.close()
    
    def test_get_cluster_docs_nonexistent(self, temp_db):
        """Test retrieving documents for a nonexistent cluster."""
        conn = db.connect()
        docs = db.get_cluster_docs(conn, "nonexistent-cluster")
        assert docs == []
        conn.close()
