import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

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
register_routes(app)

if __name__ == '__main__':
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=5000, debug=True)