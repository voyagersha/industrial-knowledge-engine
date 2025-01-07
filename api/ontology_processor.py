import pandas as pd
from typing import Dict, List
import re

def extract_entities(text: str) -> List[Dict]:
    """Extract entities from text using basic pattern matching."""
    # Simple word extraction (excluding common stop words)
    words = re.findall(r'\b\w+\b', text.lower())
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
    entities = []

    for word in words:
        if word not in stop_words and len(word) > 2:
            entities.append({
                'text': word,
                'label': 'CONCEPT',
                'start': text.lower().find(word),
                'end': text.lower().find(word) + len(word)
            })
    return entities

def extract_relationships(text: str) -> List[Dict]:
    """Extract basic relationships between consecutive entities."""
    words = text.split()
    relationships = []

    for i in range(len(words) - 1):
        if len(words[i]) > 2 and len(words[i + 1]) > 2:  # Simple filter for meaningful words
            relationships.append({
                'source': words[i],
                'target': words[i + 1],
                'type': 'NEXT_TO'
            })

    return relationships

def extract_ontology(df: pd.DataFrame) -> Dict:
    """Extract ontology from work order data."""
    ontology = {
        'entities': set(),
        'relationships': [],
        'attributes': set()
    }

    # Process each work order
    for _, row in df.iterrows():
        # Assuming work orders have 'description' and 'title' columns
        text = f"{row.get('title', '')} {row.get('description', '')}"

        # Extract entities
        entities = extract_entities(text)
        for entity in entities:
            ontology['entities'].add((entity['text'], entity['label']))

        # Extract relationships
        relationships = extract_relationships(text)
        ontology['relationships'].extend(relationships)

        # Extract attributes (column names from DataFrame)
        ontology['attributes'].update(df.columns)

    # Convert sets to lists for JSON serialization
    return {
        'entities': list(ontology['entities']),
        'relationships': ontology['relationships'],
        'attributes': list(ontology['attributes'])
    }