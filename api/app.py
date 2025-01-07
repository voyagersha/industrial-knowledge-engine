import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import logger
from neo4j import GraphDatabase
import config

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Neo4j driver
driver = None
try:
    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )
    # Test connection
    with driver.session() as session:
        result = session.run("RETURN 1")
        result.single()
    logger.info("Successfully connected to Neo4j")
except Exception as e:
    logger.error(f"Failed to connect to Neo4j: {str(e)}")

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