import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Neo4j configuration - make it optional for development
try:
    NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    logger.info("Successfully connected to Neo4j")
except Exception as e:
    logger.warning(f"Neo4j connection failed: {str(e)}. Some features may be limited.")
    neo4j_driver = None

@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400

        df = pd.read_csv(file)
        logger.info(f"Successfully read CSV file with columns: {df.columns.tolist()}")

        # Extract initial ontology
        from ontology_processor import extract_ontology
        ontology = extract_ontology(df)
        logger.info("Successfully extracted ontology")

        return jsonify({
            'message': 'File processed successfully',
            'ontology': ontology
        })
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/validate-ontology', methods=['POST'])
def validate_ontology():
    try:
        data = request.json
        validated_ontology = data.get('ontology', {})
        logger.info("Received ontology for validation")

        # Store validated ontology
        from graph_generator import generate_knowledge_graph
        graph = generate_knowledge_graph(validated_ontology)
        logger.info("Successfully generated knowledge graph")

        return jsonify({
            'message': 'Ontology validated successfully',
            'graph': graph
        })
    except Exception as e:
        logger.error(f"Error validating ontology: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/export-neo4j', methods=['POST'])
def export_to_neo4j():
    try:
        if not neo4j_driver:
            return jsonify({'error': 'Neo4j connection not available'}), 503

        data = request.json
        graph = data.get('graph', {})
        logger.info("Received graph for Neo4j export")

        with neo4j_driver.session() as session:
            # Clear existing graph
            session.run("MATCH (n) DETACH DELETE n")

            # Create nodes
            for node in graph['nodes']:
                session.run(
                    "CREATE (n:Entity {id: $id, label: $label, type: $type})",
                    id=node['id'], label=node['label'], type=node['type']
                )

            # Create relationships
            for edge in graph['edges']:
                session.run("""
                    MATCH (source:Entity {id: $source_id})
                    MATCH (target:Entity {id: $target_id})
                    CREATE (source)-[:RELATES_TO {type: $type}]->(target)
                """, source_id=edge['source'], target_id=edge['target'], type=edge['type'])

        logger.info("Successfully exported graph to Neo4j")
        return jsonify({'message': 'Graph exported to Neo4j successfully'})
    except Exception as e:
        logger.error(f"Error exporting to Neo4j: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200