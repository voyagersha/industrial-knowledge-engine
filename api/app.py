import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import spacy
from neo4j import GraphDatabase
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize spaCy
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.info("Downloading spaCy model...")
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

# Neo4j configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

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
        
        # Extract initial ontology
        from ontology_processor import extract_ontology
        ontology = extract_ontology(df)
        
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
        
        # Store validated ontology
        from graph_generator import generate_knowledge_graph
        graph = generate_knowledge_graph(validated_ontology)
        
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
        data = request.json
        graph = data.get('graph', {})
        
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
        
        return jsonify({'message': 'Graph exported to Neo4j successfully'})
    except Exception as e:
        logger.error(f"Error exporting to Neo4j: {str(e)}")
        return jsonify({'error': str(e)}), 500