import os
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from neo4j import GraphDatabase, Driver
import json
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np
import re

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, driver: Driver):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.driver = driver

        # Initialize cache for embeddings with TTL
        self.embedding_cache = {}
        self.cache_ttl = timedelta(hours=1)
        self.similarity_threshold = 0.75

    @lru_cache(maxsize=100)
    def _get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text with caching."""
        cache_key = text.strip().lower()

        # Check cache
        if cache_key in self.embedding_cache:
            timestamp, embedding = self.embedding_cache[cache_key]
            if datetime.now() - timestamp < self.cache_ttl:
                return embedding

        try:
            # Get new embedding
            response = self.openai.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            embedding = response.data[0].embedding

            # Update cache
            self.embedding_cache[cache_key] = (datetime.now(), embedding)
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            raise

    def _calculate_similarity(self, embed1: List[float], embed2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings."""
        try:
            return float(np.dot(embed1, embed2) / (np.linalg.norm(embed1) * np.linalg.norm(embed2)))
        except Exception as e:
            logger.error(f"Error calculating similarity: {str(e)}")
            return 0.0

    def _analyze_query_intent(self, query: str) -> Dict[str, float]:
        """Analyze query to determine the intent and confidence scores."""
        query_lower = query.lower()
        intents = {
            'facility': 0.0,
            'asset': 0.0,
            'maintenance': 0.0,
            'personnel': 0.0,
            'relationship': 0.0
        }

        # Keywords and their weights for each intent
        intent_keywords = {
            'facility': ['facility', 'building', 'location', 'site', 'plant'],
            'asset': ['asset', 'equipment', 'machine', 'device', 'system'],
            'maintenance': ['maintenance', 'repair', 'fix', 'broken', 'issue'],
            'personnel': ['staff', 'worker', 'employee', 'technician', 'operator'],
            'relationship': ['connected', 'related', 'between', 'link', 'association']
        }

        # Calculate scores based on keyword presence and context
        for intent, keywords in intent_keywords.items():
            score = sum(2.0 if word in query_lower else 0.0 for word in keywords)
            # Add partial matching
            score += sum(0.5 for keyword in keywords 
                        if any(re.search(f"{keyword}[es|s|ed|ing]*", word) 
                              for word in query_lower.split()))
            intents[intent] = min(1.0, score / 4.0)  # Normalize to [0,1]

        return intents

    def _execute_query(self, query, params=None):
        """Execute Neo4j query with error handling"""
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return result.data()
        except Exception as e:
            logger.error(f"Neo4j query failed: {str(e)}")
            raise

    def _get_relevant_context(self, query: str) -> Dict:
        """Get relevant context based on query analysis."""
        try:
            # Analyze query intent
            intents = self._analyze_query_intent(query)
            logger.debug(f"Query intents: {intents}")

            # Get query embedding
            query_embedding = self._get_embedding(query)

            primary_intent = max(intents.items(), key=lambda x: x[1])[0]
            logger.info(f"Primary intent detected: {primary_intent}")

            if primary_intent == 'facility':
                return self._get_facility_context(query)
            elif primary_intent == 'asset':
                return self._get_asset_context(query, query_embedding)
            elif primary_intent == 'maintenance':
                return self._get_maintenance_context(query, query_embedding)
            elif primary_intent == 'personnel':
                return self._get_personnel_context(query, query_embedding)
            else:
                return self._get_general_context(query_embedding)

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            raise

    def _get_facility_context(self, query: str) -> Dict:
        """Get facility-specific context."""
        facility_pattern = r"(?:facility|plant|site|building)\s+([A-Za-z0-9\s-]+)(?:\s|$)"
        matches = re.finditer(facility_pattern, query.lower())
        facility_names = [match.group(1).strip() for match in matches]

        if not facility_names:
            result = self._execute_query("""
                MATCH (f:Entity)
                WHERE f.type = 'Facility'
                RETURN f.label as facility
                LIMIT 5
            """)
            facility_names = [r['facility'] for r in result]

        contexts = []
        for facility_name in facility_names:
            result = self._execute_query("""
                MATCH (f:Entity)
                WHERE f.type = 'Facility' AND toLower(f.label) CONTAINS toLower($facility_name)
                OPTIONAL MATCH (a:Entity)-[r:LOCATED_IN]->(f)
                WHERE a.type = 'Asset'
                WITH f, collect(DISTINCT {
                    name: a.label,
                    type: a.type,
                    status: a.status
                }) as assets
                OPTIONAL MATCH (w:Entity)-[r2]->(f)
                WHERE w.type = 'WorkOrder'
                RETURN f.label as facility,
                       assets,
                       count(DISTINCT w) as workOrderCount,
                       collect(DISTINCT type(r2)) as relationTypes
            """, {"facility_name": facility_name})
            contexts.extend(result)

        return {
            "type": "facility_context",
            "data": contexts
        }

    def _get_asset_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get optimized asset-specific context."""
        asset_pattern = r"(?:asset|equipment|machine|system)\s+([A-Za-z0-9\s-]+)(?:\s|$)"
        matches = re.finditer(asset_pattern, query.lower())
        asset_names = [match.group(1).strip() for match in matches]

        if not asset_names:
            # Use semantic search for assets
            result = self._execute_query("""
                MATCH (a:Entity)
                WHERE a.type = 'Asset'
                RETURN a.label as asset
                LIMIT 5
            """)
            asset_names = [r['asset'] for r in result]

        contexts = []
        for asset_name in asset_names:
            result = self._execute_query("""
                MATCH (a:Entity)
                WHERE a.type = 'Asset' AND toLower(a.label) CONTAINS toLower($asset_name)
                OPTIONAL MATCH (a)-[r:LOCATED_IN]->(f:Entity)
                OPTIONAL MATCH (w:Entity)-[r2]->(a)
                WHERE w.type = 'WorkOrder'
                RETURN a.label as asset,
                       f.label as facility,
                       a.status as status,
                       count(DISTINCT w) as workOrderCount,
                       collect(DISTINCT {
                           id: w.id,
                           type: type(r2),
                           status: w.status
                       }) as workOrders
            """, asset_name=asset_name)

            if result:
                contexts.extend(result)

        return {
            "type": "asset_context",
            "data": contexts,
            "query_embedding": query_embedding
        }

    def _get_maintenance_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get maintenance-related context."""
        result = self._execute_query("""
            MATCH (w:Entity)
            WHERE w.type = 'WorkOrder'
            WITH w
            OPTIONAL MATCH (w)-[r]->(a:Entity)
            WHERE a.type = 'Asset'
            OPTIONAL MATCH (a)-[:LOCATED_IN]->(f:Entity)
            RETURN w.id as workOrder,
                   w.status as status,
                   a.label as asset,
                   f.label as facility,
                   type(r) as relationship
            ORDER BY w.createdAt DESC
            LIMIT 10
        """)

        return {
            "type": "maintenance_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def _get_personnel_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get personnel-related context."""
        result = self._execute_query("""
            MATCH (p:Entity)
            WHERE p.type = 'Personnel'
            OPTIONAL MATCH (w:Entity)-[r]->(p)
            WHERE w.type = 'WorkOrder'
            RETURN p.label as personnel,
                   collect(DISTINCT {
                       id: w.id,
                       type: type(r),
                       status: w.status
                   }) as workOrders
            LIMIT 10
        """)

        return {
            "type": "personnel_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def _get_general_context(self, query_embedding: List[float]) -> Dict:
        """Get optimized general context from the graph."""
        result = self._execute_query("""
            MATCH (n:Entity)
            WITH n
            OPTIONAL MATCH (n)-[r]-(related:Entity)
            WITH n, collect({
                node: related,
                relationship: type(r)
            }) as connections
            RETURN n.label as entity,
                   n.type as type,
                   n.status as status,
                   connections
            LIMIT 15
        """)

        return {
            "type": "general_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def get_response(self, user_query: str) -> Dict:
        """Generate optimized response using RAG with Neo4j context."""
        try:
            # Get relevant context
            context = self._get_relevant_context(user_query)
            if "error" in context:
                return {
                    "response": f"Error: {context['error']}. Please try rephrasing your question.",
                    "context": str(context)
                }

            # Format context for GPT
            formatted_context = self._format_context_for_gpt(context)

            # Generate response using GPT-4
            system_message = """You are an expert in enterprise asset management and maintenance operations.
            When analyzing and responding to queries:
            1. Focus on the most relevant information based on the query intent
            2. Highlight key relationships between assets, facilities, and work orders
            3. Provide specific details about maintenance history when relevant
            4. Include actionable insights based on the available data
            5. Keep responses clear, structured, and focused on the user's needs"""

            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {
                        "role": "user", 
                        "content": f"Based on this context:\n{formatted_context}\n\nQuestion: {user_query}"
                    }
                ],
                temperature=0.7
            )

            return {
                "response": response.choices[0].message.content,
                "context": formatted_context
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "error": "Failed to process your question",
                "details": str(e)
            }

    def _format_context_for_gpt(self, context: Dict) -> str:
        """Format context for GPT consumption with improved structure."""
        if "data" not in context:
            return str(context)

        context_type = context.get("type", "unknown")
        data = context["data"]

        if context_type == "facility_context":
            return self._format_facility_context(data)
        elif context_type == "asset_context":
            return self._format_asset_context(data)
        elif context_type == "maintenance_context":
            return self._format_maintenance_context(data)
        elif context_type == "personnel_context":
            return self._format_personnel_context(data)
        else:
            return self._format_general_context(data)

    def _format_facility_context(self, data: List[Dict]) -> str:
        formatted = "Facility Information:\n"
        for facility in data:
            formatted += f"\nFacility: {facility['facility']}\n"
            formatted += f"Number of Assets: {len(facility['assets'])}\n"
            formatted += f"Work Orders: {facility.get('workOrderCount', 0)}\n"

            if facility['assets']:
                formatted += "\nAssets:\n"
                for asset in facility['assets']:
                    formatted += f"- {asset['name']} ({asset['type']})"
                    if asset.get('status'):
                        formatted += f" - Status: {asset['status']}"
                    formatted += "\n"
        return formatted

    def _format_asset_context(self, data: List[Dict]) -> str:
        formatted = "Asset Information:\n"
        for asset in data:
            formatted += f"\nAsset: {asset['asset']}\n"
            if asset.get('facility'):
                formatted += f"Located in: {asset['facility']}\n"
            if asset.get('status'):
                formatted += f"Status: {asset['status']}\n"
            formatted += f"Work Orders: {asset.get('workOrderCount', 0)}\n"

            if asset.get('workOrders'):
                formatted += "\nRecent Work Orders:\n"
                for wo in asset['workOrders'][:5]:  # Show only recent 5
                    formatted += f"- ID: {wo['id']} - Type: {wo['type']} - Status: {wo['status']}\n"
        return formatted

    def _format_maintenance_context(self, data: List[Dict]) -> str:
        formatted = "Maintenance History:\n"
        for record in data:
            formatted += f"\nWork Order: {record['workOrder']}\n"
            formatted += f"Status: {record['status']}\n"
            if record.get('asset'):
                formatted += f"Asset: {record['asset']}\n"
            if record.get('facility'):
                formatted += f"Facility: {record['facility']}\n"
            if record.get('relationship'):
                formatted += f"Type: {record['relationship']}\n"
        return formatted

    def _format_personnel_context(self, data: List[Dict]) -> str:
        formatted = "Personnel Information:\n"
        for record in data:
            formatted += f"\nPerson: {record['personnel']}\n"
            if record.get('workOrders'):
                formatted += "Work Orders:\n"
                for wo in record['workOrders']:
                    formatted += f"- ID: {wo['id']} - Type: {wo['type']} - Status: {wo['status']}\n"
        return formatted

    def _format_general_context(self, data: List[Dict]) -> str:
        formatted = "General Context:\n"
        for record in data:
            formatted += f"\nEntity: {record['entity']} ({record['type']}) - Status: {record.get('status', 'N/A')}\n"
            if record.get('connections'):
                formatted += "Connections:\n"
                for connection in record['connections']:
                    formatted += f"  - {connection['relationship']} -> {connection['node'].get('label', 'N/A')} ({connection['node'].get('type', 'N/A')})\n"
        return formatted

    def _get_available_facilities(self) -> List[str]:
        """Get list of available facilities when specified facility not found."""
        result = self._execute_query("""
            MATCH (f:Entity)
            WHERE f.type = 'Facility'
            RETURN collect(DISTINCT f.label) as facilities
        """)
        return result[0]["facilities"]