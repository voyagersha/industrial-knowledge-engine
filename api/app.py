import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from database import db
from models import Node, Edge

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///knowledge_graph.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy with app
db.init_app(app)

# Enable CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

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
    """Test endpoint to verify API functionality"""
    logger.info("Test endpoint hit")
    try:
        # Test database connection
        test_node = Node(label="test", type="test")
        db.session.add(test_node)
        db.session.commit()
        db.session.delete(test_node)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "API and database connection working"
        }), 200

    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"API working but database error occurred: {str(e)}"
        }), 200

@app.route('/')
def home():
    """Root endpoint"""
    logger.info("Root endpoint hit")
    return jsonify({"message": "Welcome to the Knowledge Graph API"}), 200

# Register routes
from routes import register_routes
register_routes(app)

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Starting Flask application...")
    app.run(host='0.0.0.0', port=port, debug=True)