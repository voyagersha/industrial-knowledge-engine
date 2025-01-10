"""
Main Flask application entry point for the AI-Powered Industrial Data Management Platform.

This module initializes and configures the Flask application, including:
- Database connection and configuration
- CORS settings for API access
- Static file serving for the frontend
- Health check endpoint
- Route registration

The application uses Flask-SQLAlchemy for ORM and Flask-Migrate for database migrations.
"""

import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from database import db
from flask_migrate import Migrate

# Configure logging with debug level for development
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

# Configure static folder path for serving the frontend build
static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
app.static_folder = static_folder
logger.info(f"Static folder path: {static_folder}")
logger.info(f"Static folder exists: {os.path.exists(static_folder)}")

# Database Configuration
# Uses environment variables for secure credential management
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,  # Verify connection before usage
    'pool_recycle': 300,    # Recycle connections every 5 minutes
}

# Initialize database instance
db.init_app(app)

# Configure CORS for cross-origin requests
# In production, replace "*" with specific origins
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize database migration support
migrate = Migrate(app, db)

# Create database tables
with app.app_context():
    try:
        from models import Node, Edge, User
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}", exc_info=True)

@app.before_request
def log_request_info():
    """Log details about incoming requests for debugging and monitoring."""
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"Request data: {request.get_data()}")

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring application status.

    Returns:
        JSON response with application health status
        200: If the application and database are healthy
        500: If there are any issues
    """
    try:
        # Verify database connection
        with db.engine.connect() as connection:
            connection.execute("SELECT 1")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Register API routes
from routes import register_routes
register_routes(app)

# Frontend route handler
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the frontend application and handle client-side routing.

    Args:
        path: The requested path from the client

    Returns:
        The appropriate static file or index.html for client-side routing
    """
    try:
        if not os.path.exists(app.static_folder):
            logger.error(f"Static folder not found at {app.static_folder}")
            return jsonify({'error': 'Frontend build not found'}), 404

        # Try to serve the exact file first
        file_path = os.path.join(app.static_folder, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(app.static_folder, path)

        # Otherwise, serve index.html for client-side routing
        logger.info(f"Serving index.html for path: {path}")
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        logger.error(f"Error serving frontend: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Start the development server
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)