import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from py2neo import Graph
import logging
from config import wait_for_neo4j, NEO4J_URI
from data_setup import setup_neo4j_directories

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize database
def init_db():
    """Initialize database connection and setup"""
    try:
        # Setup Neo4j directories first
        if not setup_neo4j_directories():
            logger.error("Failed to set up Neo4j directories")
            return None

        # Wait for Neo4j to be available
        if not wait_for_neo4j():
            logger.error("Neo4j failed to initialize")
            return None

        # Create graph connection
        graph = Graph(NEO4J_URI)
        logger.info("Successfully connected to Neo4j")
        return graph
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        return None

# Initialize graph connection
graph = init_db()
if not graph:
    logger.error("Failed to initialize database connection")
    # Gracefully handle the case where Neo4j isn't available
    # perhaps return a 503 error on all routes.
    

# Routes
@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        handler = get_chat_handler()
        if not handler:
            return jsonify({
                'error': 'Chat functionality is not available. Please ensure Neo4j is running and try again.'
            }), 503

        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({'error': 'No query provided'}), 400

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
        if not graph:
            return jsonify({
                "status": "warning",
                "message": "API is working but Neo4j connection failed"
            }), 200

        result = graph.run("RETURN 1 as num").data()
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

# Register all other routes
from routes import register_routes
register_routes(app, graph)


def get_chat_handler():
    """Get or create ChatHandler"""
    global chat_handler
    if not chat_handler:
        from chat_handler import ChatHandler
        try:
            chat_handler = ChatHandler(graph) 
            logger.info("Successfully initialized ChatHandler")
        except Exception as e:
            logger.error(f"Failed to initialize ChatHandler: {str(e)}")
            chat_handler = None
    return chat_handler

chat_handler = None # Initialize chat_handler globally

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=True)