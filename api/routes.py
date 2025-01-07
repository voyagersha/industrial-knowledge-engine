from flask import request, jsonify
import pandas as pd
from ontology_processor import extract_ontology
from graph_generator import generate_knowledge_graph
from config import logger
from models import Node, Edge
from database import db

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

            # Extract initial ontology
            ontology = extract_ontology(df)
            logger.info(f"Extracted ontology with {len(ontology.get('entities', []))} entities")
            logger.debug(f"Extracted ontology: {ontology}")

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
            logger.info(f"Received ontology with {len(validated_ontology.get('entities', []))} entities")
            logger.debug(f"Validating ontology: {validated_ontology}")

            # Generate graph structure
            graph_data = generate_knowledge_graph(validated_ontology)
            logger.info(f"Generated graph with {len(graph_data.get('nodes', []))} nodes")
            logger.debug(f"Generated graph: {graph_data}")

            return jsonify({
                'message': 'Ontology validated successfully',
                'graph': graph_data
            })
        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/export-neo4j', methods=['POST'])
    def export_to_neo4j():
        logger.info("Export to database endpoint hit")
        try:
            data = request.json
            graph_data = data.get('graph', {})
            logger.info(f"Received graph with {len(graph_data.get('nodes', []))} nodes for database export")

            try:
                # Clear existing data
                Node.query.delete()
                Edge.query.delete()
                db.session.commit()
                logger.info("Cleared existing graph data")

                # Create nodes
                nodes = {}
                for node_data in graph_data['nodes']:
                    logger.debug(f"Creating node: {node_data}")
                    node = Node(
                        label=node_data['label'],
                        type=node_data['type'],
                        properties={'id': node_data['id']}
                    )
                    db.session.add(node)
                    nodes[node_data['id']] = node

                db.session.commit()
                logger.info(f"Created {len(nodes)} nodes")

                # Create relationships
                edge_count = 0
                for edge in graph_data['edges']:
                    logger.debug(f"Creating relationship: {edge['source']} -{edge['type']}-> {edge['target']}")
                    new_edge = Edge(
                        source=nodes[edge['source']],
                        target=nodes[edge['target']],
                        type=edge['type']
                    )
                    db.session.add(new_edge)
                    edge_count += 1

                db.session.commit()
                logger.info(f"Created {edge_count} relationships")

                return jsonify({'message': 'Graph exported to database successfully'})

            except Exception as e:
                logger.error(f"Error during database export: {str(e)}")
                db.session.rollback()
                raise

        except Exception as e:
            logger.error(f"Error exporting to database: {str(e)}")
            return jsonify({
                'error': f'Failed to export graph to database: {str(e)}'
            }), 500

    logger.info("Routes registered successfully")