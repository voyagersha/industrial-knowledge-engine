import os
import pytest
import json
from io import BytesIO
import pandas as pd
from app import app
from models import Node, Edge, db

@pytest.fixture
def test_client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def create_test_csv():
    """Create a test CSV file with sample work order data"""
    data = {
        'Work Order ID': ['WO001', 'WO002'],
        'Asset ID': ['A001', 'A002'],
        'Asset Name': ['Pump 1', 'Motor 1'],
        'Facility Name': ['Plant A', 'Plant B'],
        'Department': ['Maintenance', 'Operations'],
        'Assigned To': ['John Doe', 'Jane Smith']
    }
    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False).encode('utf-8')
    return BytesIO(csv_data)

def test_complete_workflow(test_client):
    """Test the complete workflow from file upload to chat interaction"""
    # Step 1: Upload CSV file
    csv_file = create_test_csv()
    response = test_client.post(
        '/upload',
        data={'file': (csv_file, 'test.csv')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'ontology' in data
    ontology = data['ontology']
    
    # Step 2: Validate ontology
    response = test_client.post(
        '/validate-ontology',
        json={'ontology': ontology}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'graph' in data
    graph_data = data['graph']
    
    # Step 3: Export to database
    response = test_client.post(
        '/export-neo4j',
        json={'graph': graph_data}
    )
    assert response.status_code == 200
    
    # Verify database state
    with app.app_context():
        assert Node.query.count() > 0
        assert Edge.query.count() > 0
        
        # Verify specific nodes exist
        nodes = Node.query.all()
        node_labels = [node.label for node in nodes]
        assert 'Pump 1' in node_labels
        assert 'Plant A' in node_labels
        
        # Verify relationships
        edges = Edge.query.all()
        assert any(edge.type == 'LOCATED_IN' for edge in edges)
        assert any(edge.type == 'ASSIGNED_TO' for edge in edges)

    # Step 4: Test chat interface
    response = test_client.post(
        '/chat',
        json={'query': 'What assets are in Plant A?'}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'response' in data
    assert not data.get('error')

def test_error_handling(test_client):
    """Test error handling in the workflow"""
    # Test file upload with invalid file
    response = test_client.post(
        '/upload',
        data={'file': (BytesIO(b'invalid data'), 'test.txt')},
        content_type='multipart/form-data'
    )
    assert response.status_code == 400
    
    # Test ontology validation with invalid data
    response = test_client.post(
        '/validate-ontology',
        json={'ontology': None}
    )
    assert response.status_code == 200  # Returns empty graph on invalid data
    
    # Test chat with empty query
    response = test_client.post(
        '/chat',
        json={}
    )
    assert response.status_code == 400

def test_health_check(test_client):
    """Test health check endpoint"""
    response = test_client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
