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

            # Process the file
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

            return jsonify({
                'message': 'Ontology validated successfully',
                'graph': graph_data
            })
        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/api/export-neo4j', methods=['POST', 'OPTIONS'])
    def export_to_neo4j():
        """Export graph to Neo4j database."""
        logger.info("Export to Neo4j endpoint hit")

        # Handle OPTIONS request for CORS preflight
        if request.method == 'OPTIONS':
            return '', 204

        try:
            data = request.json
            if not data or 'graph' not in data:
                return jsonify({'error': 'No graph data provided'}), 400

            graph_data = data.get('graph', {})
            logger.info(f"Received graph with {len(graph_data.get('nodes', []))} nodes")

            try:
                # Clear existing data
                Node.query.delete()
                Edge.query.delete()
                db.session.commit()
                logger.info("Cleared existing graph data")

                # Create nodes
                nodes = {}
                for node_data in graph_data.get('nodes', []):
                    node = Node(
                        label=node_data.get('label', ''),
                        type=node_data.get('type', 'Unknown'),
                        properties={'id': node_data.get('id')}
                    )
                    db.session.add(node)
                    nodes[node_data.get('id')] = node

                db.session.commit()
                logger.info(f"Created {len(nodes)} nodes")

                # Create relationships
                edge_count = 0
                for edge in graph_data.get('edges', []):
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    if source_id and target_id and source_id in nodes and target_id in nodes:
                        new_edge = Edge(
                            source=nodes[source_id],
                            target=nodes[target_id],
                            type=edge.get('type', 'Unknown')
                        )
                        db.session.add(new_edge)
                        edge_count += 1

                db.session.commit()
                logger.info(f"Created {edge_count} relationships")

                return jsonify({
                    'message': f'Graph exported successfully. Created {len(nodes)} nodes and {edge_count} edges.'
                })

            except Exception as e:
                logger.error(f"Database error: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

        except Exception as e:
            logger.error(f"Error exporting to Neo4j: {str(e)}", exc_info=True)
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