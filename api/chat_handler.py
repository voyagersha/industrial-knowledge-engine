import os
import logging
from typing import Dict, List
from openai import OpenAI
import json
from datetime import datetime
from models import Node, Edge, db

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

class ChatHandler:
    def __init__(self, db):
        self.openai = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        self.db = db

    def _analyze_query_intent(self, query: str) -> Dict[str, float]:
        """Analyze query to determine the intent and confidence scores."""
        query_lower = query.lower()
        intents = {
            'facility': 0.0,
            'asset': 0.0,
            'maintenance': 0.0
        }

        # Keywords for each intent
        intent_keywords = {
            'facility': ['facility', 'building', 'location', 'site', 'plant'],
            'asset': ['asset', 'equipment', 'machine', 'device', 'system'],
            'maintenance': ['maintenance', 'repair', 'fix', 'broken', 'issue']
        }

        # Calculate scores based on keyword presence
        for intent, keywords in intent_keywords.items():
            score = sum(2.0 if word in query_lower else 0.0 for word in keywords)
            intents[intent] = min(1.0, score / 4.0)  # Normalize to [0,1]

        return intents

    def _get_relevant_context(self, query: str) -> Dict:
        """Get relevant context based on query analysis."""
        try:
            intents = self._analyze_query_intent(query)
            primary_intent = max(intents.items(), key=lambda x: x[1])[0]
            logger.info(f"Primary intent detected: {primary_intent}")

            if primary_intent == 'asset':
                return self._get_asset_context()
            elif primary_intent == 'facility':
                return self._get_facility_context()
            else:
                return {'type': 'general_context', 'data': []}

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}", exc_info=True)
            return {'type': 'error', 'data': []}

    def _get_facility_context(self) -> Dict:
        """Get facility-specific context."""
        facilities = []
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
                        'status': edge.source.properties.get('status') if edge.source.properties else None
                    })

            # Count work orders
            work_order_count = Edge.query.join(Node, Edge.source_id == Node.id)\
                .filter(Node.type == 'WorkOrder')\
                .filter(Edge.target_id == facility.id)\
                .count()

            facility_data['workOrderCount'] = work_order_count
            facilities.append(facility_data)

        return {
            "type": "facility_context",
            "data": facilities
        }

    def _get_asset_context(self) -> Dict:
        """Get asset-specific context."""
        try:
            assets = Node.query.filter_by(type='Asset').all()
            asset_contexts = []

            for asset in assets:
                asset_data = {
                    'asset': asset.label,
                    'facility': None,
                    'status': asset.properties.get('status') if asset.properties else None,
                    'workOrders': []
                }

                # Get facility for this asset
                facility_edge = Edge.query.join(Node, Edge.target_id == Node.id)\
                    .filter(Edge.source_id == asset.id)\
                    .filter(Node.type == 'Facility')\
                    .first()
                if facility_edge:
                    asset_data['facility'] = facility_edge.target.label

                # Get work orders for this asset
                work_orders = Edge.query.join(Node, Edge.source_id == Node.id)\
                    .filter(Edge.target_id == asset.id)\
                    .filter(Node.type == 'WorkOrder')\
                    .all()

                for wo in work_orders:
                    asset_data['workOrders'].append({
                        'id': wo.source.label,
                        'status': wo.source.properties.get('status') if wo.source.properties else None
                    })

                asset_contexts.append(asset_data)

            return {
                "type": "asset_context",
                "data": asset_contexts
            }

        except Exception as e:
            logger.error(f"Error in _get_asset_context: {str(e)}", exc_info=True)
            return {"type": "asset_context", "data": []}

    def get_response(self, user_query: str) -> Dict:
        """Generate response using context."""
        try:
            logger.info(f"Processing chat query: {user_query}")
            context = self._get_relevant_context(user_query)

            system_message = """You are an expert in enterprise asset management and maintenance operations.
            When analyzing and responding to queries:
            1. Focus on the most relevant information based on the query intent
            2. Highlight key relationships between assets, facilities, and work orders
            3. Keep responses clear and focused on the user's needs"""

            try:
                response = self.openai.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": system_message},
                        {
                            "role": "user", 
                            "content": f"Based on this context:\n{json.dumps(context, indent=2)}\n\nQuestion: {user_query}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )

                if not response.choices or not response.choices[0].message:
                    raise ValueError("Empty response received from OpenAI")

                return {
                    "response": response.choices[0].message.content,
                    "context": context
                }

            except Exception as e:
                logger.error(f"OpenAI API error: {str(e)}", exc_info=True)
                raise

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "error": "Failed to process your question",
                "details": str(e)
            }