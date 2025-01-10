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

        logger.debug(f"Query intent analysis: {intents}")
        return intents

    def _get_relevant_context(self, query: str) -> Dict:
        """Get relevant context based on query analysis."""
        try:
            intents = self._analyze_query_intent(query)
            primary_intent = max(intents.items(), key=lambda x: x[1])[0]
            logger.info(f"Primary intent detected: {primary_intent}")

            # Debug database state
            logger.debug(f"Total nodes in database: {Node.query.count()}")
            logger.debug(f"Total edges in database: {Edge.query.count()}")
            logger.debug(f"Asset nodes: {Node.query.filter_by(type='Asset').count()}")

            if primary_intent == 'asset':
                return self._get_asset_context()
            elif primary_intent == 'facility':
                return self._get_facility_context()
            else:
                logger.info("No specific context type matched, returning general context")
                return self._get_general_context()

        except Exception as e:
            logger.error(f"Error getting context: {str(e)}", exc_info=True)
            return {'type': 'error', 'data': []}

    def _get_general_context(self) -> Dict:
        """Get general context about the knowledge graph."""
        try:
            context = {
                'nodes': Node.query.count(),
                'edges': Edge.query.count(),
                'asset_count': Node.query.filter_by(type='Asset').count(),
                'facility_count': Node.query.filter_by(type='Facility').count()
            }
            return {
                'type': 'general_context',
                'data': [context]
            }
        except Exception as e:
            logger.error(f"Error getting general context: {str(e)}", exc_info=True)
            return {'type': 'general_context', 'data': []}

    def _get_facility_context(self) -> Dict:
        """Get facility-specific context."""
        facilities = []
        try:
            facility_nodes = Node.query.filter_by(type='Facility').all()
            logger.debug(f"Found {len(facility_nodes)} facility nodes")

            for facility in facility_nodes:
                # Get work order count for this facility
                work_order_count = Edge.query.join(
                    Node, Edge.source_id == Node.id
                ).filter(
                    Node.type == 'WorkOrder',
                    Edge.target_id == facility.id,
                    Edge.type == 'ASSIGNED_TO'
                ).count()

                logger.debug(f"Found {work_order_count} work orders for facility {facility.label}")

                facility_data = {
                    'facility': facility.label,
                    'assets': [],
                    'workOrderCount': work_order_count
                }

                # Get assets in this facility
                asset_edges = Edge.query.join(
                    Node, Edge.source_id == Node.id
                ).filter(
                    Node.type == 'Asset',
                    Edge.target_id == facility.id,
                    Edge.type == 'LOCATED_IN'
                ).all()

                logger.debug(f"Found {len(asset_edges)} assets for facility {facility.label}")

                for edge in asset_edges:
                    asset = edge.source
                    # Get work orders for this asset
                    asset_work_orders = Edge.query.join(
                        Node, Edge.source_id == Node.id
                    ).filter(
                        Node.type == 'WorkOrder',
                        Edge.target_id == asset.id,
                        Edge.type == 'ASSIGNED_TO'
                    ).all()

                    facility_data['assets'].append({
                        'name': asset.label,
                        'status': asset.properties.get('status') if asset.properties else None,
                        'workOrders': [
                            {'id': wo.source.label, 'status': wo.source.properties.get('status')}
                            for wo in asset_work_orders
                        ]
                    })

                facilities.append(facility_data)

            logger.info(f"Returning context for {len(facilities)} facilities")
            return {
                "type": "facility_context",
                "data": facilities
            }
        except Exception as e:
            logger.error(f"Error in _get_facility_context: {str(e)}", exc_info=True)
            return {"type": "facility_context", "data": []}

    def _get_asset_context(self) -> Dict:
        """Get asset-specific context."""
        try:
            assets = Node.query.filter_by(type='Asset').all()
            logger.debug(f"Found {len(assets)} asset nodes")
            asset_contexts = []

            for asset in assets:
                asset_data = {
                    'asset': asset.label,
                    'facility': None,
                    'status': asset.properties.get('status') if asset.properties else None,
                    'workOrders': []
                }

                # Get facility for this asset
                facility_edge = Edge.query.join(
                    Node, Edge.target_id == Node.id
                ).filter(
                    Edge.source_id == asset.id,
                    Node.type == 'Facility',
                    Edge.type == 'LOCATED_IN'
                ).first()

                if facility_edge:
                    asset_data['facility'] = facility_edge.target.label

                # Get work orders for this asset
                work_orders = Edge.query.join(
                    Node, Edge.source_id == Node.id
                ).filter(
                    Edge.target_id == asset.id,
                    Node.type == 'WorkOrder'
                ).all()

                logger.debug(f"Found {len(work_orders)} work orders for asset {asset.label}")

                for wo in work_orders:
                    asset_data['workOrders'].append({
                        'id': wo.source.label,
                        'status': wo.source.properties.get('status') if wo.source.properties else None
                    })

                asset_contexts.append(asset_data)

            logger.info(f"Returning context for {len(asset_contexts)} assets")
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
            logger.debug(f"Generated context: {json.dumps(context, indent=2)}")

            system_message = """You are an expert in enterprise asset management and maintenance operations.
            When analyzing and responding to queries:
            1. Focus on the most relevant information based on the query intent
            2. If the data is empty or missing, explicitly state that and suggest checking if data has been uploaded
            3. Highlight key relationships between assets, facilities, and work orders
            4. Keep responses clear and focused on the user's needs"""

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