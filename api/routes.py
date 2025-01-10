from flask import request, jsonify
import pandas as pd
from ontology_processor import extract_ontology
from graph_generator import generate_knowledge_graph
from config import logger
from models import Node, Edge
from database import db

def register_routes(app):
    @app.route('/validate-ontology', methods=['POST'])
    def validate_ontology():
        logger.info("Validate ontology endpoint hit")
        try:
            data = request.json
            validated_ontology = data.get('ontology') if data else {}

            # Initialize empty ontology if none provided
            if validated_ontology is None:
                validated_ontology = {'entities': [], 'relationships': [], 'attributes': []}

            logger.info(f"Received ontology with {len(validated_ontology.get('entities', []))} entities")
            logger.debug(f"Validating ontology: {validated_ontology}")

            # Generate graph structure
            graph_data = generate_knowledge_graph(validated_ontology)
            logger.info(f"Generated graph with {len(graph_data.get('nodes', []))} nodes and {len(graph_data.get('edges', []))} edges")
            logger.debug(f"Generated graph: {graph_data}")

            return jsonify({
                'message': 'Ontology validated successfully',
                'graph': graph_data
            })
        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}", exc_info=True)
            return jsonify({'error': str(e)}), 500

    @app.route('/export-neo4j', methods=['POST'])
    def export_to_neo4j():
        logger.info("Export to database endpoint hit")
        try:
            data = request.json
            graph_data = data.get('graph', {})
            logger.info(f"Received graph with {len(graph_data.get('nodes', []))} nodes for database export")
            logger.debug(f"Full graph data: {graph_data}")

            try:
                # Clear existing data
                Node.query.delete()
                Edge.query.delete()
                db.session.commit()
                logger.info("Cleared existing graph data")

                # Create nodes
                nodes = {}
                for node_data in graph_data.get('nodes', []):
                    logger.debug(f"Creating node: {node_data}")
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
                    if not source_id or not target_id or source_id not in nodes or target_id not in nodes:
                        logger.warning(f"Skipping edge due to missing nodes: {edge}")
                        continue

                    logger.debug(f"Creating relationship: {source_id} -{edge.get('type', 'Unknown')}-> {target_id}")
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
                    'message': f'Graph exported to database successfully. Created {len(nodes)} nodes and {edge_count} edges.'
                })

            except Exception as e:
                logger.error(f"Error during database export: {str(e)}", exc_info=True)
                db.session.rollback()
                raise

        except Exception as e:
            logger.error(f"Error exporting to database: {str(e)}", exc_info=True)
            return jsonify({
                'error': f'Failed to export graph to database: {str(e)}'
            }), 500

    logger.info("Routes registered successfully")