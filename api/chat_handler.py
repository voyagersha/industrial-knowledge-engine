import os
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
import json
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np
import re
from sqlalchemy import text
from models import Node, Edge, db

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self, db):
        self.openai = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.db = db

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

    def _get_entities_by_type(self, entity_type: str) -> List[Dict]:
        """Get entities of a specific type from the database."""
        return Node.query.filter_by(type=entity_type).all()

    def _get_relationships(self, node_id: int) -> List[Dict]:
        """Get relationships for a specific node."""
        outgoing = Edge.query.filter_by(source_id=node_id).all()
        incoming = Edge.query.filter_by(target_id=node_id).all()
        return outgoing + incoming

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

        contexts = []
        for facility in Node.query.filter_by(type='Facility').all():
            facility_data = {
                'facility': facility.label,
                'assets': [],
                'workOrderCount': 0
            }

            # Get assets in this facility
            for edge in facility.incoming_edges:
                if edge.source.type == 'Asset':
                    facility_data['assets'].append({
                        'name': edge.source.label,
                        'type': edge.source.type,
                        'status': edge.source.properties.get('status') if edge.source.properties else None
                    })

            # Count work orders
            work_order_count = Edge.query.join(Node, Edge.source_id == Node.id)\
                .filter(Node.type == 'WorkOrder')\
                .filter(Edge.target_id == facility.id)\
                .count()

            facility_data['workOrderCount'] = work_order_count
            contexts.append(facility_data)

        return {
            "type": "facility_context",
            "data": contexts
        }

    def _get_asset_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get asset-specific context."""
        asset_pattern = r"(?:asset|equipment|machine|system)\s+([A-Za-z0-9\s-]+)(?:\s|$)"
        matches = re.finditer(asset_pattern, query.lower())
        asset_names = [match.group(1).strip() for match in matches]

        contexts = []
        for asset in Node.query.filter_by(type='Asset').all():
            asset_data = {
                'asset': asset.label,
                'facility': None,
                'status': asset.properties.get('status') if asset.properties else None,
                'workOrders': []
            }

            # Get facility
            facility_edge = Edge.query.join(Node, Edge.target_id == Node.id)\
                .filter(Edge.source_id == asset.id)\
                .filter(Node.type == 'Facility')\
                .first()
            if facility_edge:
                asset_data['facility'] = facility_edge.target.label

            # Get work orders
            work_orders = Edge.query.join(Node, Edge.source_id == Node.id)\
                .filter(Edge.target_id == asset.id)\
                .filter(Node.type == 'WorkOrder')\
                .all()

            asset_data['workOrders'] = [{
                'id': wo.source.label,
                'type': wo.type,
                'status': wo.source.properties.get('status') if wo.source.properties else None
            } for wo in work_orders]

            contexts.append(asset_data)

        return {
            "type": "asset_context",
            "data": contexts,
            "query_embedding": query_embedding
        }

    def _get_maintenance_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get maintenance-related context."""
        #Adapt this to SQLAlchemy
        result = [] # Placeholder - needs SQLAlchemy implementation

        return {
            "type": "maintenance_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def _get_personnel_context(self, query: str, query_embedding: List[float]) -> Dict:
        """Get personnel-related context."""
        #Adapt this to SQLAlchemy
        result = [] # Placeholder - needs SQLAlchemy implementation

        return {
            "type": "personnel_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def _get_general_context(self, query_embedding: List[float]) -> Dict:
        """Get optimized general context from the graph."""
        #Adapt this to SQLAlchemy
        result = [] # Placeholder - needs SQLAlchemy implementation

        return {
            "type": "general_context",
            "data": result,
            "query_embedding": query_embedding
        }

    def get_response(self, user_query: str) -> Dict:
        """Generate optimized response using RAG with graph context."""
        try:
            logger.info(f"Processing chat query: {user_query}")

            # Get relevant context
            context = self._get_relevant_context(user_query)
            logger.debug(f"Retrieved context: {context}")

            if "error" in context:
                return {
                    "response": f"Error: {context['error']}. Please try rephrasing your question.",
                    "context": str(context)
                }

            # Format context for GPT
            formatted_context = self._format_context_for_gpt(context)
            logger.debug(f"Formatted context: {formatted_context}")

            # Generate response using GPT-4
            system_message = """You are an expert in enterprise asset management and maintenance operations.
            When analyzing and responding to queries:
            1. Focus on the most relevant information based on the query intent
            2. Highlight key relationships between assets, facilities, and work orders
            3. Provide specific details about maintenance history when relevant
            4. Include actionable insights based on the available data
            5. Keep responses clear, structured, and focused on the user's needs"""

            try:
                logger.info("Sending request to OpenAI")
                response = self.openai.chat.completions.create(
                    model="gpt-4-turbo-preview",  # Updated to latest model
                    messages=[
                        {"role": "system", "content": system_message},
                        {
                            "role": "user", 
                            "content": f"Based on this context:\n{formatted_context}\n\nQuestion: {user_query}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                logger.info("Received response from OpenAI")
                logger.debug(f"OpenAI response: {response}")

                if not response.choices or not response.choices[0].message:
                    raise ValueError("Empty response received from OpenAI")

                return {
                    "response": response.choices[0].message.content,
                    "context": formatted_context
                }

            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}")
                raise

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
            formatted += f"Work Orders: {facility['workOrderCount']}\n"

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

            if asset.get('workOrders'):
                formatted += "\nWork Orders:\n"
                for wo in asset['workOrders']:
                    formatted += f"- ID: {wo['id']} - Type: {wo['type']} - Status: {wo['status']}\n"
        return formatted

    def _format_maintenance_context(self, data: List[Dict]) -> str:
        formatted = "Maintenance History:\n"
        for record in data:
            formatted += f"\nWork Order: {record.get('workOrder','N/A')}\n" #Handle potential missing keys
            formatted += f"Status: {record.get('status','N/A')}\n"
            formatted += f"Asset: {record.get('asset','N/A')}\n"
            formatted += f"Facility: {record.get('facility','N/A')}\n"
            formatted += f"Type: {record.get('relationship','N/A')}\n"
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