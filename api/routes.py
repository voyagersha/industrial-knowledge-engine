from flask import request, jsonify
import pandas as pd
from ontology_processor import extract_ontology
from graph_generator import generate_knowledge_graph
from config import logger
from models import Node, Edge
from database import db

def register_routes(app):
    @app.route('/api/upload', methods=['POST', 'OPTIONS'])
    def upload_file():
        """Handle file upload."""
        logger.info("Upload endpoint hit")

        # Handle OPTIONS request for CORS preflight
        if request.method == 'OPTIONS':
            return '', 204

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

            # Clear existing data
            try:
                Node.query.delete()
                Edge.query.delete()
                db.session.commit()
                logger.info("Cleared existing graph data")
            except Exception as e:
                logger.error(f"Error clearing data: {str(e)}")
                db.session.rollback()

            # Process the file
            df = pd.read_csv(file)
            logger.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")

            # Extract initial ontology
            ontology = extract_ontology(df)
            logger.info(f"Extracted ontology: {len(ontology.get('entities', []))} entities, {len(ontology.get('relationships', []))} relationships")

            # Debug ontology contents
            for entity in ontology.get('entities', []):
                if entity[1] == 'WorkOrder':
                    logger.debug(f"Found WorkOrder entity: {entity}")

            for rel in ontology.get('relationships', []):
                if 'WorkOrder' in [rel.get('source_type'), rel.get('target_type')]:
                    logger.debug(f"Found WorkOrder relationship: {rel}")

            return jsonify({
                'message': 'File processed successfully',
                'ontology': ontology
            })
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/validate-ontology', methods=['POST', 'OPTIONS'])
    def validate_ontology():
        """Validate ontology and generate graph."""
        logger.info(f"Validate ontology endpoint hit with method: {request.method}")
        logger.debug(f"Request headers: {request.headers}")

        # Handle OPTIONS request for CORS preflight
        if request.method == 'OPTIONS':
            logger.info("Handling OPTIONS preflight request")
            return '', 204

        try:
            data = request.json
            logger.debug(f"Received data: {data}")

            if not data or 'ontology' not in data:
                logger.error("Invalid request data")
                return jsonify({'error': 'Invalid request data'}), 400

            validated_ontology = data.get('ontology')
            logger.info(f"Processing ontology with {len(validated_ontology.get('entities', []))} entities")

            # Generate graph structure
            graph_data = generate_knowledge_graph(validated_ontology)
            logger.info(f"Generated graph with {len(graph_data.get('nodes', []))} nodes")

            try:
                # Store data in PostgreSQL
                node_mapping = {}
                for node_data in graph_data.get('nodes', []):
                    node = Node(
                        label=node_data.get('label'),
                        type=node_data.get('type'),
                        properties={'id': node_data.get('id')}
                    )
                    db.session.add(node)
                    node_mapping[node_data.get('id')] = node

                db.session.flush()
                logger.info(f"Created {len(node_mapping)} nodes")

                # Create edges
                edge_count = 0
                for edge_data in graph_data.get('edges', []):
                    source_id = edge_data.get('source')
                    target_id = edge_data.get('target')
                    if source_id in node_mapping and target_id in node_mapping:
                        edge = Edge(
                            source=node_mapping[source_id],
                            target=node_mapping[target_id],
                            type=edge_data.get('type', 'relates_to')
                        )
                        db.session.add(edge)
                        edge_count += 1

                db.session.commit()
                logger.info(f"Created {edge_count} edges")

                # Verify data was stored
                stored_nodes = Node.query.count()
                stored_edges = Edge.query.count()
                logger.info(f"Database verification - Nodes: {stored_nodes}, Edges: {stored_edges}")

                return jsonify({
                    'message': 'Ontology validated and stored successfully',
                    'graph': graph_data
                })

            except Exception as e:
                logger.error(f"Database error: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/chat', methods=['POST', 'OPTIONS'])
    def chat():
        """Handle chat requests."""
        logger.info("Chat endpoint hit")

        # Handle OPTIONS request for CORS preflight
        if request.method == 'OPTIONS':
            return '', 204

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

    logger.info("Routes registered successfully")