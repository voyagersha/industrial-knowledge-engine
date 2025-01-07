from typing import Dict, List
import networkx as nx
import json

def generate_knowledge_graph(ontology: Dict) -> Dict:
    """Generate a knowledge graph from validated ontology."""
    G = nx.DiGraph()
    
    # Add nodes for entities
    for entity in ontology['entities']:
        node_id = f"entity_{len(G.nodes)}"
        G.add_node(node_id, label=entity[0], type=entity[1])
    
    # Add edges for relationships
    for rel in ontology['relationships']:
        source_nodes = [n for n, attr in G.nodes(data=True) 
                       if attr['label'] == rel['source']]
        target_nodes = [n for n, attr in G.nodes(data=True) 
                       if attr['label'] == rel['target']]
        
        if source_nodes and target_nodes:
            G.add_edge(source_nodes[0], target_nodes[0], 
                      type=rel['type'])
    
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
    
    return graph_data
