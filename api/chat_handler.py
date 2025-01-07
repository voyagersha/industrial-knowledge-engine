import os
import logging
from typing import Dict, List
from openai import OpenAI
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.neo4j_driver = GraphDatabase.driver(
            NEO4J_URI,
            auth=(NEO4J_USER, NEO4J_PASSWORD)
        )

    def _get_graph_context(self, query: str) -> str:
        """Query Neo4j based on user's question and return relevant context."""
        try:
            with self.neo4j_driver.session() as session:
                # Extract potential facility name from query
                facility_terms = ['plant', 'facility', 'location', 'building', 'site']
                query_lower = query.lower()

                # Check if query is about assets in a specific location
                if any(term in query_lower for term in facility_terms):
                    # Extract potential facility name (text after location terms)
                    facility_name = None
                    for term in facility_terms:
                        if term in query_lower:
                            term_index = query_lower.index(term)
                            remaining_text = query_lower[term_index:].split()
                            if len(remaining_text) > 1:
                                facility_name = remaining_text[1]  # Get the word after the facility term
                                break

                    if facility_name:
                        # Query for assets by location with fuzzy matching
                        result = session.run("""
                            MATCH (facility:Entity {type: 'Facility'})
                            WHERE toLower(facility.label) CONTAINS toLower($facility_name)
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
                        """, facility_name=facility_name)

                        records = result.data()
                        if not records:
                            # Try to find similar facility names
                            similar_facilities = session.run("""
                                MATCH (f:Entity {type: 'Facility'})
                                RETURN f.label as facility_name
                                ORDER BY f.label
                            """).data()

                            if similar_facilities:
                                facilities_list = "\n".join([f"- {f['facility_name']}" for f in similar_facilities])
                                return f"No assets found for facility '{facility_name}'. Available facilities are:\n{facilities_list}"
                            return "No facility information found in the knowledge graph."
                    else:
                        # Query for all facilities and their assets
                        result = session.run("""
                            MATCH (facility:Entity {type: 'Facility'})
                            OPTIONAL MATCH (asset:Entity {type: 'Asset'})-[r1:LOCATED_IN]->(facility)
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
                        """)
                        records = result.data()

                else:
                    # Default query for assets
                    result = session.run("""
                        MATCH (asset:Entity {type: 'Asset'})
                        OPTIONAL MATCH (asset)-[r1:LOCATED_IN]->(facility:Entity {type: 'Facility'})
                        OPTIONAL MATCH (asset)-[r2:BELONGS_TO]->(dept:Entity {type: 'Department'})
                        OPTIONAL MATCH (wo:Entity {type: 'WorkOrder'})-[r3:MAINTAINS]->(asset)
                        RETURN 
                            asset.label as asset_name,
                            facility.label as facility_name,
                            dept.label as department,
                            collect(DISTINCT wo.label) as work_orders
                        ORDER BY asset_name
                    """)
                    records = result.data()

                if not records:
                    return "No relevant data found in the knowledge graph matching your query."

                return self._format_query_results(query, records)

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return "Unable to retrieve context from the knowledge graph."

    def _format_query_results(self, query: str, records: List[Dict]) -> str:
        """Format query results based on the type of query."""
        if 'facility_name' in records[0] and 'assets' in records[0]:
            # Format facility-grouped assets
            context = "Assets by Facility:\n"
            for record in records:
                facility = record['facility_name'] or 'Unassigned Facility'
                assets_info = record['assets']
                if assets_info:  # Only show facilities with assets
                    context += f"\n{facility}:\n"
                    for asset_info in assets_info:
                        if asset_info['asset_name']:  # Only show valid assets
                            context += f"  • {asset_info['asset_name']}\n"
                            if asset_info['department']:
                                context += f"    ↳ Department: {asset_info['department']}\n"
                            if asset_info['work_orders']:
                                wo_count = len([wo for wo in asset_info['work_orders'] if wo])
                                if wo_count > 0:
                                    context += f"    ↳ Associated Work Orders: {wo_count}\n"
        else:
            # Format individual asset records
            context = "Asset Information:\n"
            for record in records:
                if record['asset_name']:  # Only show valid assets
                    context += f"\n• {record['asset_name']}\n"
                    if record['facility_name']:
                        context += f"  ↳ Location: {record['facility_name']}\n"
                    if record['department']:
                        context += f"  ↳ Department: {record['department']}\n"
                    if record['work_orders']:
                        wo_count = len([wo for wo in record['work_orders'] if wo])
                        if wo_count > 0:
                            context += f"  ↳ Associated Work Orders: {wo_count}\n"

        return context

    def get_response(self, user_query: str) -> Dict:
        """Get response from OpenAI based on Neo4j context."""
        try:
            # Get relevant context from Neo4j
            graph_context = self._get_graph_context(user_query)

            system_message = """You are a knowledgeable assistant that helps users understand work order and maintenance data.
            Your responses should:
            1. Be specific about assets, locations, and departments
            2. Include relevant statistics (e.g., number of assets per facility)
            3. Highlight any patterns or relationships in the data
            4. If information is missing, explain what specific data would help
            5. Keep responses clear and structured"""

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