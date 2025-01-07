from flask import request, jsonify
import logging
import pandas as pd
from ontology_processor import extract_ontology
from graph_generator import generate_knowledge_graph

logger = logging.getLogger(__name__)

def register_routes(app):
    @app.route('/upload', methods=['POST'])
    def upload_file():
        logger.info("Upload endpoint hit")
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

            ontology = extract_ontology(df)
            logger.info("Successfully extracted ontology")

            return jsonify({
                'message': 'File processed successfully',
                'ontology': ontology
            })
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/validate-ontology', methods=['POST'])
    def validate_ontology():
        logger.info("Validate ontology endpoint hit")
        try:
            data = request.json
            validated_ontology = data.get('ontology', {})
            graph = generate_knowledge_graph(validated_ontology)
            
            return jsonify({
                'message': 'Ontology validated successfully',
                'graph': graph
            })
        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}")
            return jsonify({'error': str(e)}), 500

    logger.info("Routes registered successfully")
