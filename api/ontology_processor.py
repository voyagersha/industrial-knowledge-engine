import pandas as pd
from typing import Dict, List
import re

def extract_entities(df: pd.DataFrame) -> List[tuple]:
    """Extract entities from work order data with meaningful types."""
    entities = set()

    # Add assets as entities
    for _, row in df.iterrows():
        if pd.notna(row.get('Asset ID')) and pd.notna(row.get('Asset Name')):
            entities.add((str(row['Asset Name']), 'Asset'))

        if pd.notna(row.get('Facility Name')):
            entities.add((str(row['Facility Name']), 'Facility'))

        if pd.notna(row.get('Department')):
            entities.add((str(row['Department']), 'Department'))

        if pd.notna(row.get('Workstation Name')):
            entities.add((str(row['Workstation Name']), 'Workstation'))

        if pd.notna(row.get('Assigned To')):
            entities.add((str(row['Assigned To']), 'Personnel'))

    return list(entities)

def extract_relationships(df: pd.DataFrame) -> List[Dict]:
    """Extract relationships between entities."""
    relationships = []

    for _, row in df.iterrows():
        # Asset to Facility relationship
        if pd.notna(row.get('Asset Name')) and pd.notna(row.get('Facility Name')):
            relationships.append({
                'source': str(row['Asset Name']),
                'target': str(row['Facility Name']),
                'type': 'LOCATED_IN'
            })

        # Asset to Department relationship
        if pd.notna(row.get('Asset Name')) and pd.notna(row.get('Department')):
            relationships.append({
                'source': str(row['Asset Name']),
                'target': str(row['Department']),
                'type': 'BELONGS_TO'
            })

        # Workstation to Department relationship
        if pd.notna(row.get('Workstation Name')) and pd.notna(row.get('Department')):
            relationships.append({
                'source': str(row['Workstation Name']),
                'target': str(row['Department']),
                'type': 'ASSIGNED_TO'
            })

        # Work Order to Asset relationship
        if pd.notna(row.get('Asset Name')) and pd.notna(row.get('Work Order ID')):
            relationships.append({
                'source': f"WO_{row['Work Order ID']}",
                'target': str(row['Asset Name']),
                'type': 'MAINTAINS'
            })

    return relationships

def extract_ontology(df: pd.DataFrame) -> Dict:
    """Extract ontology from work order data."""
    ontology = {
        'entities': extract_entities(df),
        'relationships': extract_relationships(df),
        'attributes': list(df.columns)  # Include all columns as potential attributes
    }

    return ontology