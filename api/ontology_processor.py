import pandas as pd
from typing import Dict, List, Tuple
import re
import logging

logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """Clean and normalize text values."""
    if pd.isna(text):
        return ""
    return str(text).strip()

def extract_entities(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """Extract entities from work order data with meaningful types."""
    entities = set()
    logger.debug(f"Starting entity extraction from DataFrame with columns: {df.columns}")

    # Process each row
    for _, row in df.iterrows():
        # Asset entities
        if pd.notna(row.get('Asset ID')):
            asset_id = clean_text(row['Asset ID'])
            if asset_id:
                entities.add((asset_id, 'Asset'))

        if pd.notna(row.get('Asset Name')):
            asset_name = clean_text(row['Asset Name'])
            if asset_name:
                entities.add((asset_name, 'Asset'))

        # Facility entities
        if pd.notna(row.get('Facility Name')):
            facility_name = clean_text(row['Facility Name'])
            if facility_name:
                entities.add((facility_name, 'Facility'))

        # Department entities
        if pd.notna(row.get('Department')):
            department = clean_text(row['Department'])
            if department:
                entities.add((department, 'Department'))

        # Work Order entities
        if pd.notna(row.get('Work Order ID')):
            wo_id = f"WO_{clean_text(row['Work Order ID'])}"
            entities.add((wo_id, 'WorkOrder'))

        # Personnel entities
        if pd.notna(row.get('Assigned To')):
            personnel = clean_text(row['Assigned To'])
            if personnel:
                entities.add((personnel, 'Personnel'))

    logger.debug(f"Extracted {len(entities)} entities")
    return sorted(list(entities))

def extract_relationships(df: pd.DataFrame) -> List[Dict]:
    """Extract relationships between entities."""
    relationships = []
    logger.debug("Starting relationship extraction")

    for _, row in df.iterrows():
        # Work Order to Asset relationships
        if pd.notna(row.get('Work Order ID')) and pd.notna(row.get('Asset ID')):
            wo_id = f"WO_{clean_text(row['Work Order ID'])}"
            asset_id = clean_text(row['Asset ID'])
            if wo_id and asset_id:
                relationships.append({
                    'source': wo_id,
                    'target': asset_id,
                    'type': 'MAINTAINS'
                })

        # Asset ID to Asset Name relationship
        if pd.notna(row.get('Asset ID')) and pd.notna(row.get('Asset Name')):
            asset_id = clean_text(row['Asset ID'])
            asset_name = clean_text(row['Asset Name'])
            if asset_id and asset_name:
                relationships.append({
                    'source': asset_id,
                    'target': asset_name,
                    'type': 'HAS_NAME'
                })

        # Asset to Facility relationship
        if pd.notna(row.get('Asset ID')) and pd.notna(row.get('Facility Name')):
            asset_id = clean_text(row['Asset ID'])
            facility_name = clean_text(row['Facility Name'])
            if asset_id and facility_name:
                relationships.append({
                    'source': asset_id,
                    'target': facility_name,
                    'type': 'LOCATED_IN'
                })

        # Asset to Department relationship
        if pd.notna(row.get('Asset ID')) and pd.notna(row.get('Department')):
            asset_id = clean_text(row['Asset ID'])
            department = clean_text(row['Department'])
            if asset_id and department:
                relationships.append({
                    'source': asset_id,
                    'target': department,
                    'type': 'BELONGS_TO'
                })

        # Work Order to Personnel relationship
        if pd.notna(row.get('Work Order ID')) and pd.notna(row.get('Assigned To')):
            wo_id = f"WO_{clean_text(row['Work Order ID'])}"
            personnel = clean_text(row['Assigned To'])
            if wo_id and personnel:
                relationships.append({
                    'source': wo_id,
                    'target': personnel,
                    'type': 'ASSIGNED_TO'
                })

    logger.debug(f"Extracted {len(relationships)} relationships")
    return relationships

def extract_ontology(df: pd.DataFrame) -> Dict:
    """Extract ontology from work order data."""
    logger.info("Starting ontology extraction")
    try:
        entities = extract_entities(df)
        relationships = extract_relationships(df)

        ontology = {
            'entities': entities,
            'relationships': relationships,
            'attributes': list(df.columns)
        }

        logger.info(f"Completed ontology extraction: {len(entities)} entities, {len(relationships)} relationships")
        logger.debug(f"Sample of first 5 entities: {entities[:5] if entities else []}")
        logger.debug(f"Sample of first 5 relationships: {relationships[:5] if relationships else []}")
        return ontology

    except Exception as e:
        logger.error(f"Error in ontology extraction: {str(e)}", exc_info=True)
        raise