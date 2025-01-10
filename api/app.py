import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from database import db, init_db
from sqlalchemy import text
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SQLALCHEMY_ENGINE_OPTIONS

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize database
db.init_app(app)
with app.app_context():
    # Make sure to import the models here so they can be created
    from models import Node, Edge
    db.create_all()

@app.route('/health')
def health_check():
    """Health check endpoint."""
    logger.info("Handling health check request")
    return jsonify({
        'status': 'healthy',
        'message': 'API is running'
    }), 200

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        data = request.json
        query = data.get('query')
        if not query:
            return jsonify({'error': 'No query provided'}), 400

        from chat_handler import ChatHandler
        handler = ChatHandler(db)
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
    """Test endpoint to verify API functionality."""
    logger.info("Test endpoint hit")
    try:
        # Test database connection
        result = db.session.execute(text("SELECT 1")).scalar()
        if result == 1:
            return jsonify({
                "status": "success",
                "message": "API and database connection working"
            }), 200
        else:
            return jsonify({
                "status": "error",
                "message": "Database connection test failed"
            }), 500

    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"API working but database error occurred: {str(e)}"
        }), 500

@app.route('/')
def home():
    """Root endpoint"""
    logger.info("Root endpoint hit")
    return jsonify({"message": "Welcome to the Knowledge Graph API"}), 200

# Register routes
from routes import register_routes
register_routes(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=True)