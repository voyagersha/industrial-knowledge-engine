import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from database import db, init_db
from flask_migrate import Migrate
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SQLALCHEMY_ENGINE_OPTIONS
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/dist')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Initialize database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

with app.app_context():
    # Import models here so they can be created
    from models import Node, Edge, User
    db.create_all()

@app.before_request
def log_request_info():
    """Log details about every incoming request."""
    logger.debug('Headers: %s', dict(request.headers))
    logger.debug('Body: %s', request.get_data())
    logger.debug('URL: %s', request.url)
    logger.debug('Method: %s', request.method)

@app.route('/')
def serve_frontend():
    """Serve the frontend application."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files from the frontend build."""
    return send_from_directory(app.static_folder, path)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        result = db.session.execute(text("SELECT 1")).scalar()
        return jsonify({
            'status': 'healthy',
            'message': 'API is running'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }), 500

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

# Register routes
from routes import register_routes
register_routes(app)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=True)