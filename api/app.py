import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from neo4j import GraphDatabase
import logging
import tempfile

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Neo4j configuration
TEMP_DIR = tempfile.mkdtemp()
NEO4J_URI = "bolt://localhost:7687"

class Neo4jConnection:
    def __init__(self):
        self._driver = None

    def get_driver(self):
        if not self._driver:
            try:
                self._driver = GraphDatabase.driver(NEO4J_URI)
                # Test connection
                with self._driver.session() as session:
                    session.run("RETURN 1")
                logger.info("Successfully connected to Neo4j")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {str(e)}")
                self._driver = None
        return self._driver

# Initialize Neo4j connection
neo4j_connection = Neo4jConnection()

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        driver = neo4j_connection.get_driver()
        if not driver:
            return jsonify({
                'error': 'Neo4j connection not available'
            }), 503

        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({'error': 'No query provided'}), 400

        from chat_handler import ChatHandler
        handler = ChatHandler(driver)
        response = handler.get_response(query)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }), 500

@app.route('/test')
def test():
    """Test endpoint to verify API functionality"""
    logger.info("Test endpoint hit")
    try:
        driver = neo4j_connection.get_driver()
        if not driver:
            return jsonify({
                "status": "warning",
                "message": "API is working but Neo4j connection failed"
            }), 200

        with driver.session() as session:
            result = session.run("RETURN 1 as num").data()
            if result and result[0]["num"] == 1:
                return jsonify({
                    "status": "success",
                    "message": "API and Neo4j connection working"
                }), 200
            else:
                return jsonify({
                    "status": "warning",
                    "message": "API working but Neo4j query failed"
                }), 200

    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({
            "status": "error",
            "message": f"API working but error occurred: {str(e)}"
        }), 200

@app.route('/')
def home():
    """Root endpoint"""
    logger.info("Root endpoint hit")
    return jsonify({"message": "Welcome to the Knowledge Graph API"}), 200

# Register routes
from routes import register_routes
register_routes(app, neo4j_connection.get_driver())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=True)