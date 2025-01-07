import os
from flask import Flask, request, jsonify
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

# Configure CORS - Allow all origins during development
CORS(app, 
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True)

# Create a temporary directory for Neo4j data
TEMP_DIR = tempfile.mkdtemp()
NEO4J_URI = f"file://{TEMP_DIR}"

@app.before_request
def log_request_info():
    """Log details about every incoming request."""
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)
    logger.debug('Endpoint: %s', request.endpoint)
    logger.debug('View Args: %s', request.view_args)
    logger.debug('Method: %s', request.method)

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

# API routes
@app.route('/test')
def test():
    """Test endpoint to verify API functionality."""
    logger.info("Handling /test request")
    return jsonify({"message": "API is working"}), 200

@app.route('/upload', methods=['POST'])
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
        logger.debug(f"Extracted ontology: {ontology}")

        return jsonify({
            'message': 'File processed successfully',
            'ontology': ontology
        })
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/validate-ontology', methods=['POST'])
def validate_ontology():
    try:
        data = request.json
        validated_ontology = data.get('ontology', {})
        logger.info("Received ontology for validation")
        logger.debug(f"Validating ontology: {validated_ontology}")

        # Generate graph structure
        from graph_generator import generate_knowledge_graph
        graph = generate_knowledge_graph(validated_ontology)
        logger.info("Successfully generated knowledge graph")
        logger.debug(f"Generated graph: {graph}")

        return jsonify({
            'message': 'Ontology validated successfully',
            'graph': graph
        })
    except Exception as e:
        logger.error(f"Error validating ontology: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/export-neo4j', methods=['POST'])
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
        logger.debug(f"Graph data to export: {graph_data}")

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

@app.route('/health')
def health_check():
    """Health check endpoint."""
    logger.info("Handling health check request")
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    }), 200

# Error handler for 404 Not Found
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url}")
    return jsonify({
        'error': 'Not Found',
        'message': 'The requested resource was not found on this server'
    }), 404

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)