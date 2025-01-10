from typing import Dict, List
import networkx as nx
import logging

logger = logging.getLogger(__name__)

def generate_knowledge_graph(ontology: Dict) -> Dict:
    """Generate a knowledge graph from validated ontology."""
    try:
        G = nx.DiGraph()

        # Ensure ontology has required keys
        entities = ontology.get('entities', [])
        relationships = ontology.get('relationships', [])

        logger.info(f"Processing {len(entities)} entities and {len(relationships)} relationships")

        # Add nodes for entities, filtering out test data
        node_mapping = {}  # Track entity label to node_id mapping
        for entity in entities:
            # Skip test data (Stamping Press assets)
            if entity[1] == 'Asset' and 'Stamping Press' in entity[0]:
                logger.debug(f"Skipping test asset: {entity[0]}")
                continue

            node_id = f"entity_{len(G.nodes)}"
            G.add_node(node_id, label=entity[0], type=entity[1])
            node_mapping[entity[0]] = node_id
            logger.debug(f"Added node {node_id}: {entity}")

        # Add edges for relationships
        edge_count = 0
        for rel in relationships:
            source_label = rel['source']
            target_label = rel['target']

            if source_label in node_mapping and target_label in node_mapping:
                source_id = node_mapping[source_label]
                target_id = node_mapping[target_label]
                G.add_edge(source_id, target_id, type=rel['type'])
                edge_count += 1
                logger.debug(f"Added edge: {source_label} -{rel['type']}-> {target_label}")
            else:
                logger.warning(f"Skipped relationship due to missing nodes: {rel}")

        logger.info(f"Created graph with {len(G.nodes)} nodes and {edge_count} edges")

        # Convert to format suitable for visualization and database storage
        graph_data = {
            'nodes': [
                {
                    'id': node_id,
                    'label': attr['label'],
                    'type': attr['type']
                }
                for node_id, attr in G.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'type': data.get('type', 'relates_to')
                }
                for u, v, data in G.edges(data=True)
            ]
        }

        logger.info(f"Generated graph data with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")
        logger.debug("Sample nodes:")
        for node in graph_data['nodes'][:5]:
            logger.debug(f"Node: {node}")
        logger.debug("Sample edges:")
        for edge in graph_data['edges'][:5]:
            logger.debug(f"Edge: {edge}")

        return graph_data

    except Exception as e:
        logger.error(f"Error generating knowledge graph: {str(e)}", exc_info=True)
        # Return empty graph structure on error
        return {
            'nodes': [],
            'edges': []
        }