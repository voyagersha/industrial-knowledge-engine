import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from py2neo import Graph
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

@app.route('/health')
def health_check():
    """Health check endpoint."""
    logger.info("Handling health check request")
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    }), 200

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
        logger.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")

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

        # Initialize empty ontology if none provided
        if not validated_ontology:
            validated_ontology = {'entities': [], 'relationships': [], 'attributes': []}

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