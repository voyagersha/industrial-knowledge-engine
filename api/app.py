import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import logger, wait_for_neo4j
from neo4j import GraphDatabase
import config

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Neo4j driver
driver = None

# Wait for Neo4j to be available before starting the app
if wait_for_neo4j():
    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        logger.info("Successfully initialized Neo4j driver")
    except Exception as e:
        logger.error(f"Failed to initialize Neo4j driver: {str(e)}")
else:
    logger.warning("Starting app without Neo4j connection. Export functionality will be limited.")

# Routes
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