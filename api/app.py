import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import logger, wait_for_neo4j, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from neo4j import GraphDatabase
import config

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize Neo4j driver
driver = None
chat_handler = None

def get_neo4j_driver():
    """Get or create Neo4j driver"""
    global driver
    if not driver:
        try:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Test connection
            with driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
            driver = None
    return driver

def get_chat_handler():
    """Get or create ChatHandler"""
    global chat_handler
    if not chat_handler:
        from chat_handler import ChatHandler
        try:
            chat_handler = ChatHandler()
            logger.info("Successfully initialized ChatHandler")
        except Exception as e:
            logger.error(f"Failed to initialize ChatHandler: {str(e)}")
            chat_handler = None
    return chat_handler

# Routes
@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        handler = get_chat_handler()
        if not handler:
            return jsonify({
                'error': 'Chat functionality is not available. Please check Neo4j connection.'
            }), 503

        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({'error': 'No query provided'}), 400

        response = handler.get_response(query)
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/test')
def test():
    """Test endpoint to verify API functionality"""
    logger.info("Test endpoint hit")
    return jsonify({"message": "API is working"}), 200

@app.route('/')
def home():
    """Root endpoint"""
    logger.info("Root endpoint hit")
    return jsonify({"message": "Welcome to the Knowledge Graph API"}), 200

# Register all other routes
from routes import register_routes
register_routes(app, get_neo4j_driver)

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)