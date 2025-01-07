import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import logger, wait_for_neo4j
from neo4j import GraphDatabase
import config
from chat_handler import ChatHandler

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Neo4j driver
driver = None

# Initialize ChatHandler
chat_handler = None

# Wait for Neo4j to be available before starting the app
if wait_for_neo4j():
    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        chat_handler = ChatHandler()
        logger.info("Successfully initialized Neo4j driver and ChatHandler")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
else:
    logger.warning("Starting app without Neo4j connection. Export functionality will be limited.")

# Routes
@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        if not chat_handler:
            return jsonify({
                'error': 'Chat functionality is not available. Please check Neo4j connection.'
            }), 503

        data = request.json
        query = data.get('query')

        if not query:
            return jsonify({'error': 'No query provided'}), 400

        response = chat_handler.get_response(query)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test():
    logger.info("Test endpoint hit")
    return jsonify({"message": "API is working"}), 200

@app.route('/')
def home():
    logger.info("Root endpoint hit")
    return jsonify({"message": "Welcome to the Knowledge Graph API"}), 200

# Register all other routes
from routes import register_routes
register_routes(app, driver)

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)