import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
from database import db
from flask_migrate import Migrate

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
static_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend', 'dist')
app.static_folder = static_folder
logger.info(f"Static folder path: {static_folder}")
logger.info(f"Static folder exists: {os.path.exists(static_folder)}")

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Initialize extensions
db.init_app(app)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow CORS for all routes
migrate = Migrate(app, db)

# Initialize database tables
with app.app_context():
    try:
        from models import Node, Edge, User
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}", exc_info=True)

@app.before_request
def log_request_info():
    """Log details about every incoming request."""
    logger.info(f"Request: {request.method} {request.url}")
    logger.debug(f"Request headers: {request.headers}")
    logger.debug(f"Request data: {request.get_data()}")

# Direct upload route without /api prefix
@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload."""
    logger.info("Upload endpoint hit")
    try:
        if 'file' not in request.files:
            logger.error("No file part in request")
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            logger.error("No selected file")
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            logger.error("Invalid file type")
            return jsonify({'error': 'Only CSV files are supported'}), 400

        # Process the file
        import pandas as pd
        from ontology_processor import extract_ontology

        df = pd.read_csv(file)
        logger.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")

        # Extract initial ontology
        ontology = extract_ontology(df)
        logger.info(f"Extracted ontology: {len(ontology.get('entities', []))} entities, {len(ontology.get('relationships', []))} relationships")
        logger.debug(f"Full ontology data: {ontology}")

        return jsonify({
            'message': 'File processed successfully',
            'ontology': ontology
        })
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        with db.engine.connect() as connection:
            connection.execute("SELECT 1")
        return jsonify({'status': 'healthy'}), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests."""
    try:
        data = request.json
        if not data or 'query' not in data:
            return jsonify({'error': 'No query provided'}), 400

        from chat_handler import ChatHandler
        handler = ChatHandler(db)
        response = handler.get_response(data['query'])
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Register other routes
from routes import register_routes
register_routes(app)

# Serve frontend routes
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the frontend application."""
    try:
        if not os.path.exists(app.static_folder):
            logger.error(f"Static folder not found at {app.static_folder}")
            return jsonify({'error': 'Frontend build not found'}), 404

        # First try to serve the exact file
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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)