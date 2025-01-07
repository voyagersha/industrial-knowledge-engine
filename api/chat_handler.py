import os
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from neo4j import GraphDatabase
import json
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )
        # Initialize cache for embeddings
        self.embedding_cache = {}
        self.cache_ttl = timedelta(hours=1)

    def _get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text with caching."""
        cache_key = text.strip().lower()

        # Check cache
        if cache_key in self.embedding_cache:
            timestamp, embedding = self.embedding_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return embedding

        # Get new embedding
        response = self.openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = response.data[0].embedding

        # Update cache
        self.embedding_cache[cache_key] = (datetime.now(), embedding)
        return embedding

    def _calculate_similarity(self, embed1: List[float], embed2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        return np.dot(embed1, embed2) / (np.linalg.norm(embed1) * np.linalg.norm(embed2))

    @lru_cache(maxsize=100)
    def _get_query_patterns(self) -> List[Dict]:
        """Get predefined query patterns with their embeddings."""
        patterns = [
            {
                "pattern": "assets in location",
                "cypher": """
                    MATCH (facility:Entity {type: 'Facility'})
                    WHERE toLower(facility.label) CONTAINS toLower($location)
                    WITH facility
                    MATCH (asset:Entity {type: 'Asset'})-[r1:LOCATED_IN]->(facility)
                    OPTIONAL MATCH (asset)-[r2:BELONGS_TO]->(dept:Entity {type: 'Department'})
                    OPTIONAL MATCH (wo:Entity {type: 'WorkOrder'})-[r3:MAINTAINS]->(asset)
                    RETURN 
                        facility.label as facility_name,
                        collect(DISTINCT {
                            asset_name: asset.label,
                            department: dept.label,
                            work_orders: collect(DISTINCT wo.label)
                        }) as assets
                    ORDER BY facility_name
                """
            },
            {
                "pattern": "work orders for asset",
                "cypher": """
                    MATCH (asset:Entity {type: 'Asset'})
                    WHERE toLower(asset.label) CONTAINS toLower($asset)
                    MATCH (wo:Entity {type: 'WorkOrder'})-[r1:MAINTAINS]->(asset)
                    OPTIONAL MATCH (wo)-[r2:ASSIGNED_TO]->(personnel:Entity {type: 'Personnel'})
                    RETURN
                        asset.label as asset_name,
                        collect({
                            work_order: wo.label,
                            assigned_to: personnel.label
                        }) as work_orders
                """
            },
            {
                "pattern": "department assets",
                "cypher": """
                    MATCH (dept:Entity {type: 'Department'})
                    WHERE toLower(dept.label) CONTAINS toLower($department)
                    MATCH (asset:Entity {type: 'Asset'})-[r:BELONGS_TO]->(dept)
                    OPTIONAL MATCH (asset)-[r2:LOCATED_IN]->(facility:Entity {type: 'Facility'})
                    RETURN
                        dept.label as department_name,
                        collect({
                            asset_name: asset.label,
                            facility: facility.label
                        }) as assets
                """
            }
        ]

        # Add embeddings to patterns
        for pattern in patterns:
            pattern['embedding'] = self._get_embedding(pattern['pattern'])

        return patterns

    def _extract_parameters(self, query: str) -> Dict[str, str]:
        """Extract parameters from query based on common patterns."""
        params = {}
        query_lower = query.lower()

        # Location extraction
        location_terms = ['plant', 'facility', 'building', 'site']
        for term in location_terms:
            if term in query_lower:
                term_index = query_lower.index(term)
                remaining = query_lower[term_index:].split()
                if len(remaining) > 1:
                    params['location'] = remaining[1]
                    break

        # Asset extraction
        asset_terms = ['asset', 'equipment', 'machine']
        for term in asset_terms:
            if term in query_lower:
                term_index = query_lower.index(term)
                remaining = query_lower[term_index:].split()
                if len(remaining) > 1:
                    params['asset'] = remaining[1]
                    break

        # Department extraction
        dept_terms = ['department', 'dept', 'division']
        for term in dept_terms:
            if term in query_lower:
                term_index = query_lower.index(term)
                remaining = query_lower[term_index:].split()
                if len(remaining) > 1:
                    params['department'] = remaining[1]
                    break

        return params

    def _get_graph_context(self, query: str) -> str:
        """Query Neo4j based on semantic understanding of the question."""
        try:
            # Get query embedding
            query_embedding = self._get_embedding(query)

            # Get query patterns
            patterns = self._get_query_patterns()

            # Find best matching pattern
            best_pattern = None
            best_similarity = -1

            for pattern in patterns:
                similarity = self._calculate_similarity(query_embedding, pattern['embedding'])
                if similarity > best_similarity and similarity > 0.7:  # Threshold for matching
                    best_similarity = similarity
                    best_pattern = pattern

            # Extract parameters
            params = self._extract_parameters(query)

            with self.neo4j_driver.session() as session:
                if best_pattern:
                    # Execute optimized query
                    result = session.run(best_pattern['cypher'], **params)
                else:
                    # Fallback to generic query
                    result = session.run("""
                        MATCH (n:Entity)
                        WHERE any(term IN $search_terms WHERE toLower(n.label) CONTAINS toLower(term))
                        OPTIONAL MATCH (n)-[r]-(related:Entity)
                        RETURN n.label as entity, n.type as type,
                            collect({
                                related_entity: related.label,
                                related_type: related.type,
                                relationship: type(r)
                            }) as relationships
                        LIMIT 10
                    """, search_terms=query.lower().split())

                records = result.data()
                if not records:
                    # Try to find similar entities
                    similar = session.run("""
                        MATCH (n:Entity)
                        RETURN DISTINCT n.type as type, collect(n.label) as labels
                        ORDER BY type
                    """).data()

                    if similar:
                        context = "No exact matches found. Available entities:\n"
                        for record in similar:
                            context += f"\n{record['type']}s:"
                            for label in record['labels'][:5]:  # Show first 5 of each type
                                context += f"\n- {label}"
                            if len(record['labels']) > 5:
                                context += f"\n(and {len(record['labels'])-5} more...)"
                        return context

                    return "No relevant data found in the knowledge graph."

                return self._format_query_results(query, records)

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return "Unable to retrieve context from the knowledge graph."

    def _format_query_results(self, query: str, records: List[Dict]) -> str:
        """Format query results based on the type of query and data structure."""
        try:
            # Handle facility-grouped assets format
            if 'facility_name' in records[0] and 'assets' in records[0]:
                return self._format_facility_assets(records)

            # Handle work order format
            elif 'work_order' in records[0] and 'assigned_to' in records[0]:
                return self._format_work_orders(records)

            # Handle department assets format
            elif 'department_name' in records[0]:
                return self._format_department_assets(records)

            # Handle generic entity relationships
            else:
                return self._format_generic_results(records)

        except Exception as e:
            logger.error(f"Error formatting results: {str(e)}")
            return "Error formatting the query results."

    def _format_facility_assets(self, records: List[Dict]) -> str:
        """Format facility-grouped assets results."""
        context = "Assets by Facility:\n"
        for record in records:
            facility = record['facility_name'] or 'Unassigned Facility'
            assets_info = record['assets']
            if assets_info:
                context += f"\n{facility}:\n"
                for asset_info in assets_info:
                    if asset_info['asset_name']:
                        context += f"  • {asset_info['asset_name']}\n"
                        if asset_info['department']:
                            context += f"    ↳ Department: {asset_info['department']}\n"
                        if asset_info['work_orders']:
                            wo_count = len([wo for wo in asset_info['work_orders'] if wo])
                            if wo_count > 0:
                                context += f"    ↳ Associated Work Orders: {wo_count}\n"
        return context

    def _format_work_orders(self, records: List[Dict]) -> str:
        """Format work order focused results."""
        context = "Work Order Information:\n"
        for record in records:
            wo_id = record['work_order'].replace('WO_', 'Work Order ')
            context += f"\n• {wo_id}\n"
            if record.get('asset_name'):
                context += f"  ↳ Asset: {record['asset_name']}\n"
            if record.get('assigned_to'):
                context += f"  ↳ Assigned to: {record['assigned_to']}\n"
        return context

    def _format_department_assets(self, records: List[Dict]) -> str:
        """Format department-grouped assets results."""
        context = "Department Assets:\n"
        for record in records:
            dept = record['department_name']
            context += f"\n{dept}:\n"
            for asset in record['assets']:
                context += f"  • {asset['asset_name']}\n"
                if asset.get('facility'):
                    context += f"    ↳ Location: {asset['facility']}\n"
        return context

    def _format_generic_results(self, records: List[Dict]) -> str:
        """Format generic entity relationship results."""
        context = "Found Entities and Relationships:\n"
        for record in records:
            context += f"\n• {record['entity']} ({record['type']})\n"
            for rel in record['relationships']:
                if rel['related_entity']:
                    context += f"  ↳ {rel['relationship']} {rel['related_entity']} ({rel['related_type']})\n"
        return context

    def get_response(self, user_query: str) -> Dict:
        """Get response from OpenAI based on Neo4j context with semantic understanding."""
        try:
            # Get relevant context from Neo4j
            graph_context = self._get_graph_context(user_query)

            system_message = """You are a knowledgeable assistant that helps users understand work order and maintenance data.
            Your responses should:
            1. Be specific about assets, locations, and departments
            2. Include relevant statistics when available
            3. Explain relationships clearly and concisely
            4. If information is missing, explain what specific data would help
            5. Keep responses structured and easy to understand"""

            user_prompt = f"""Based on the following information from our knowledge graph:

{graph_context}

User's question: {user_query}

Please provide a clear, specific answer using the information above. If you can't find the exact information needed,
mention what specific data would help answer the question better."""

            # Get completion from OpenAI
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_prompt}
                ]
            )

            return {
                "response": response.choices[0].message.content,
                "context": graph_context
            }

        except Exception as e:
            logger.error(f"Error getting chat response: {str(e)}")
            return {
                "error": "Failed to process your question. Please try again.",
                "details": str(e)
            }