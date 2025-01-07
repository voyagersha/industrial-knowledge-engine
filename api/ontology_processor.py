import pandas as pd
import spacy
from typing import Dict, List
import networkx as nx

nlp = spacy.load("en_core_web_sm")

def extract_entities(text: str) -> List[Dict]:
    """Extract named entities from text using spaCy."""
    doc = nlp(text)
    entities = []
    for ent in doc.ents:
        entities.append({
            'text': ent.text,
            'label': ent.label_,
            'start': ent.start_char,
            'end': ent.end_char
        })
    return entities

def extract_relationships(text: str) -> List[Dict]:
    """Extract relationships between entities."""
    doc = nlp(text)
    relationships = []
    
    for token in doc:
        if token.dep_ in ['nsubj', 'dobj', 'pobj']:
            relationships.append({
                'source': token.text,
                'target': token.head.text,
                'type': token.dep_
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
