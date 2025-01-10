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

        logger.debug(f"Processing {len(entities)} entities and {len(relationships)} relationships")

        # Add nodes for entities
        for entity in entities:
            node_id = f"entity_{len(G.nodes)}"
            G.add_node(node_id, label=entity[0], type=entity[1])
            logger.debug(f"Added node {node_id}: {entity}")

        # Add edges for relationships
        for rel in relationships:
            source_nodes = [n for n, attr in G.nodes(data=True) 
                          if attr['label'] == rel['source']]
            target_nodes = [n for n, attr in G.nodes(data=True) 
                          if attr['label'] == rel['target']]

            if source_nodes and target_nodes:
                G.add_edge(source_nodes[0], target_nodes[0], 
                          type=rel['type'])
                logger.debug(f"Added edge from {source_nodes[0]} to {target_nodes[0]}")

        # Convert to format suitable for visualization
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

        logger.info(f"Generated graph with {len(graph_data['nodes'])} nodes and {len(graph_data['edges'])} edges")
        return graph_data

    except Exception as e:
        logger.error(f"Error generating knowledge graph: {str(e)}")
        # Return empty graph structure on error
        return {
            'nodes': [],
            'edges': []
        }