import pytest
import json
import os
from io import BytesIO

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['message'] == 'API is running'

def test_upload_empty_file(client):
    """Test file upload with no file."""
    response = client.post('/upload')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'No file provided'

def test_upload_invalid_file(client):
    """Test file upload with invalid file type."""
    data = {
        'file': (BytesIO(b'invalid file content'), 'test.txt')
    }
    response = client.post('/upload', data=data)
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'Only CSV files are supported'

def test_validate_ontology_empty_request(client):
    """Test ontology validation with empty request."""
    response = client.post('/validate-ontology', 
                         json={})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'graph' in data

def test_chat_empty_query(client):
    """Test chat endpoint with empty query."""
    response = client.post('/chat', 
                         json={})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'No query provided'

def test_export_neo4j_empty_graph(client):
    """Test Neo4j export with empty graph."""
    response = client.post('/export-neo4j',
                         json={'graph': {'nodes': [], 'edges': []}})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert 'Created 0 nodes and 0 edges' in data['message']
