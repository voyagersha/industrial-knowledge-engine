import os
import logging
from typing import Dict, List
from openai import OpenAI
import json
from datetime import datetime
from sqlalchemy import text
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

        intent_keywords = {
            'facility': ['facility', 'building', 'location', 'site', 'plant'],
            'asset': ['asset', 'equipment', 'machine', 'device', 'system'],
            'maintenance': ['maintenance', 'repair', 'fix', 'broken', 'issue', 'work order', 'workorder']
        }

        for intent, keywords in intent_keywords.items():
            score = sum(2.0 if word in query_lower else 0.0 for word in keywords)
            intents[intent] = min(1.0, score / 4.0)

        logger.debug(f"Query intent analysis: {intents}")
        return intents

    def _get_asset_context(self) -> Dict:
        """Get asset-specific context using optimized queries."""
        try:
            # Use a single efficient query to get all asset data
            query = text("""
                WITH RECURSIVE
                unique_assets AS (
                    -- Get distinct assets with their primary facility
                    SELECT DISTINCT ON (a.id)
                        a.id as asset_id,
                        a.label as asset_label,
                        a.properties as asset_properties,
                        f.label as facility_label
                    FROM node a
                    LEFT JOIN edge e_f ON a.id = e_f.source_id
                    LEFT JOIN node f ON e_f.target_id = f.id AND f.type = 'Facility'
                    WHERE a.type = 'Asset'
                    ORDER BY a.id, f.id
                ),
                work_orders AS (
                    -- Get unique work orders for each asset
                    SELECT DISTINCT
                        ua.asset_id,
                        json_agg(DISTINCT 
                            json_build_object(
                                'id', wo.label,
                                'status', wo.properties->>'status',
                                'type', e_wo.type
                            )
                        ) FILTER (WHERE wo.id IS NOT NULL) as work_orders
                    FROM unique_assets ua
                    LEFT JOIN edge e_wo ON ua.asset_id = e_wo.target_id
                    LEFT JOIN node wo ON e_wo.source_id = wo.id AND wo.type = 'WorkOrder'
                    GROUP BY ua.asset_id
                )
                -- Combine asset data with their work orders
                SELECT 
                    ua.*,
                    wo.work_orders
                FROM unique_assets ua
                LEFT JOIN work_orders wo ON ua.asset_id = wo.asset_id
                ORDER BY ua.asset_label;
            """)

            result = db.session.execute(query)
            asset_contexts = []

            for row in result:
                asset_data = {
                    'asset': row.asset_label,
                    'facility': row.facility_label,
                    'status': row.asset_properties.get('status') if row.asset_properties else None,
                    'workOrders': row.work_orders if row.work_orders else []
                }
                asset_contexts.append(asset_data)

            logger.info(f"Returning context for {len(asset_contexts)} assets")

            # Add system note to help LLM understand the data
            return {
                "type": "asset_context",
                "data": asset_contexts,
                "system_note": """
                This data represents unique assets and their associated work orders.
                Each asset appears exactly once with its primary facility.
                Work orders are deduplicated to avoid double-counting.
                The total work order count should be calculated by summing unique work orders across all assets.
                """
            }

        except Exception as e:
            logger.error(f"Error in _get_asset_context: {str(e)}", exc_info=True)
            return {"type": "asset_context", "data": []}

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
                    Node.type == 'WorkOrder'
                ).filter(
                    Edge.target_id == facility.id
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
                    Edge.target_id == facility.id
                ).all()

                logger.debug(f"Found {len(asset_edges)} assets for facility {facility.label}")

                for edge in asset_edges:
                    asset = edge.source
                    # Get work orders for this asset
                    asset_work_orders = Edge.query.join(
                        Node, Edge.source_id == Node.id
                    ).filter(
                        Node.type == 'WorkOrder',
                        Edge.target_id == asset.id
                    ).all()

                    facility_data['assets'].append({
                        'name': asset.label,
                        'status': asset.properties.get('status') if asset.properties else None,
                        'workOrders': [
                            {
                                'id': wo.source.label,
                                'status': wo.source.properties.get('status') if wo.source.properties else None,
                                'type': wo.type
                            }
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


    def get_response(self, user_query: str) -> Dict:
        """Generate response using context."""
        try:
            logger.info(f"Processing chat query: {user_query}")
            context = self._get_asset_context()  # Always use asset context for work order queries
            logger.debug(f"Generated context: {json.dumps(context, indent=2)}")

            system_message = """You are an expert in enterprise asset management and maintenance operations.
            When analyzing and responding to queries:
            1. Focus on the most relevant information based on the query intent
            2. If the data is empty or missing, explicitly state that and suggest checking if data has been uploaded
            3. Highlight key relationships between assets, facilities, and work orders
            4. Keep responses clear and focused on the user's needs
            5. When counting work orders, include the total number and break it down by facility if applicable"""

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