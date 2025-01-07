import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
from py2neo import Graph, Node, Relationship
import logging
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
# Configure CORS to allow requests from the frontend
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Create a temporary directory for Neo4j data
TEMP_DIR = tempfile.mkdtemp()
NEO4J_URI = f"file://{TEMP_DIR}"

def get_graph():
    """Get or create Neo4j graph connection using embedded mode."""
    try:
        graph = Graph(NEO4J_URI)
        # Test connection with a simple query
        graph.run("RETURN 1")
        logger.info("Successfully connected to Neo4j (embedded mode)")
        return graph
    except Exception as e:
        logger.error(f"Failed to connect to Neo4j: {str(e)}")
        return None

# Serve static files
@app.route('/')
def serve_frontend():
    return send_from_directory('../frontend/dist', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../frontend/dist', path)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400

        # Read CSV with pandas
        df = pd.read_csv(file)
        logger.info(f"Successfully read CSV file with columns: {df.columns.tolist()}")

        # Extract initial ontology
        from ontology_processor import extract_ontology
        ontology = extract_ontology(df)
        logger.info("Successfully extracted ontology")
        logger.debug(f"Extracted ontology: {ontology}")  # Debug log to see the content

        return jsonify({
            'message': 'File processed successfully',
            'ontology': ontology
        })
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate-ontology', methods=['POST'])
def validate_ontology():
    try:
        data = request.json
        validated_ontology = data.get('ontology', {})
        logger.info("Received ontology for validation")
        logger.debug(f"Validating ontology: {validated_ontology}")  # Debug log

        # Generate graph structure
        from graph_generator import generate_knowledge_graph
        graph = generate_knowledge_graph(validated_ontology)
        logger.info("Successfully generated knowledge graph")
        logger.debug(f"Generated graph: {graph}")  # Debug log

        return jsonify({
            'message': 'Ontology validated successfully',
            'graph': graph
        })
    except Exception as e:
        logger.error(f"Error validating ontology: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-neo4j', methods=['POST'])
def export_to_neo4j():
    try:
        # Get Neo4j connection
        graph_db = get_graph()
        if not graph_db:
            return jsonify({
                'error': 'Neo4j connection failed. Please check the logs for details.'
            }), 503

        data = request.json
        graph_data = data.get('graph', {})
        logger.info("Received graph for Neo4j export")
        logger.debug(f"Graph data to export: {graph_data}")  # Debug log

        try:
            # Clear existing graph
            graph_db.run("MATCH (n) DETACH DELETE n")
            logger.info("Cleared existing graph data")

            # Create nodes and store them for relationship creation
            tx = graph_db.begin()
            nodes = {}

            for node_data in graph_data['nodes']:
                node = Node("Entity",
                          id=node_data['id'],
                          label=node_data['label'],
                          type=node_data['type'])
                tx.create(node)
                nodes[node_data['id']] = node

            logger.info(f"Created {len(nodes)} nodes")

            # Create relationships
            rel_count = 0
            for edge in graph_data['edges']:
                source = nodes.get(edge['source'])
                target = nodes.get(edge['target'])
                if source and target:
                    rel = Relationship(source, edge['type'], target)
                    tx.create(rel)
                    rel_count += 1

            tx.commit()
            logger.info(f"Created {rel_count} relationships")
            return jsonify({'message': 'Graph exported to Neo4j successfully'})

        except Exception as e:
            logger.error(f"Error during Neo4j export: {str(e)}")
            if 'tx' in locals():
                tx.rollback()
            raise

    except Exception as e:
        logger.error(f"Error exporting to Neo4j: {str(e)}")
        return jsonify({
            'error': f'Failed to export graph to Neo4j: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    graph_db = get_graph()
    neo4j_status = "connected" if graph_db else "disconnected"
    return jsonify({
        'status': 'healthy',
        'neo4j_status': neo4j_status
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)