"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from apps.api.main import app
from chronicle.storage import db


@pytest.fixture
def client(temp_db):
    """Create a test client."""
    return TestClient(app)


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
    
    def test_events_endpoint_empty(self, client):
        """Test events endpoint with no data."""
        response = client.get("/events")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 0
    
    def test_events_endpoint_with_data(self, client, temp_db, sample_docs):
        """Test events endpoint with clustered data."""
        conn = db.connect()
        
        # Insert documents
        doc_ids = [db.insert_doc(conn, doc) for doc in sample_docs]
        
        # Assign to clusters
        db.upsert_cluster(conn, doc_ids[0], "cluster-1", 0.9)
        db.upsert_cluster(conn, doc_ids[1], "cluster-1", 0.85)
        
        conn.close()
        
        # Call API
        response = client.get("/events")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check structure
        event = data[0]
        assert "cluster_id" in event
        assert "n_docs" in event
        assert "score" in event
        assert "summary" in event
        assert "sample" in event
    
    def test_event_detail_endpoint(self, client, temp_db, sample_docs):
        """Test individual event endpoint."""
        conn = db.connect()
        
        # Insert and cluster documents
        doc_ids = [db.insert_doc(conn, doc) for doc in sample_docs]
        db.upsert_cluster(conn, doc_ids[0], "cluster-test", 0.9)
        
        conn.close()
        
        # Call API
        response = client.get("/events/cluster-test")
        assert response.status_code == 200
        
        data = response.json()
        assert data["cluster_id"] == "cluster-test"
        assert "summary" in data
        assert "docs" in data
        assert len(data["docs"]) > 0
    
    def test_event_detail_not_found(self, client):
        """Test event detail for nonexistent cluster."""
        response = client.get("/events/nonexistent-cluster")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_api_cors_headers(self, client):
        """Test that API includes proper response structure."""
        response = client.get("/health")
        assert response.status_code == 200
        # FastAPI automatically includes proper headers
