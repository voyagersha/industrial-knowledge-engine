from flask import request, jsonify
import pandas as pd
from ontology_processor import extract_ontology
from graph_generator import generate_knowledge_graph
from config import logger

def register_routes(app, driver):
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
            graph_data = generate_knowledge_graph(validated_ontology)

            return jsonify({
                'message': 'Ontology validated successfully',
                'graph': graph_data
            })
        except Exception as e:
            logger.error(f"Error validating ontology: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/export-neo4j', methods=['POST'])
    def export_to_neo4j():
        logger.info("Export to Neo4j endpoint hit")
        try:
            if not driver:
                return jsonify({
                    'error': 'Neo4j connection not available. Please check the server logs.'
                }), 503

            data = request.json
            graph_data = data.get('graph', {})
            logger.info("Received graph for Neo4j export")

            try:
                with driver.session() as session:
                    # Clear existing graph
                    session.run("MATCH (n) DETACH DELETE n")
                    logger.info("Cleared existing graph data")

                    # Create nodes
                    nodes = {}
                    for node_data in graph_data['nodes']:
                        logger.debug(f"Creating node: {node_data}")
                        result = session.run(
                            """
                            CREATE (n:Entity {
                                id: $id,
                                label: $label,
                                type: $type
                            })
                            RETURN n
                            """,
                            id=node_data['id'],
                            label=node_data['label'],
                            type=node_data['type']
                        )
                        nodes[node_data['id']] = result.single()['n']

                    # Create relationships
                    for edge in graph_data['edges']:
                        logger.debug(f"Creating relationship: {edge['source']} -{edge['type']}-> {edge['target']}")
                        session.run(
                            """
                            MATCH (source:Entity {id: $source_id})
                            MATCH (target:Entity {id: $target_id})
                            CREATE (source)-[r:RELATES_TO {type: $type}]->(target)
                            """,
                            source_id=edge['source'],
                            target_id=edge['target'],
                            type=edge['type']
                        )

                return jsonify({'message': 'Graph exported to Neo4j successfully'})

            except Exception as e:
                logger.error(f"Error during Neo4j export: {str(e)}")
                raise

        except Exception as e:
            logger.error(f"Error exporting to Neo4j: {str(e)}")
            return jsonify({
                'error': f'Failed to export graph to Neo4j: {str(e)}'
            }), 500

    logger.info("Routes registered successfully")