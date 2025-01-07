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
                # Determine query type and execute appropriate Cypher query
                if any(keyword in query.lower() for keyword in ['asset', 'equipment', 'machine']):
                    if any(keyword in query.lower() for keyword in ['plant', 'facility', 'location']):
                        # Query for assets by location
                        result = session.run("""
                            MATCH (asset:Entity {type: 'Asset'})-[r1:LOCATED_IN]->(facility:Entity {type: 'Facility'})
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
                    else:
                        # Query for all assets and their relationships
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
                else:
                    # Default to work order focused query
                    result = session.run("""
                        MATCH (wo:Entity {type: 'WorkOrder'})-[r1:MAINTAINS]->(asset:Entity {type: 'Asset'})
                        OPTIONAL MATCH (asset)-[:LOCATED_IN]->(facility:Entity {type: 'Facility'})
                        OPTIONAL MATCH (asset)-[:BELONGS_TO]->(dept:Entity {type: 'Department'})
                        OPTIONAL MATCH (wo)-[:ASSIGNED_TO]->(personnel:Entity {type: 'Personnel'})
                        RETURN 
                            wo.label as work_order,
                            asset.label as asset_name,
                            facility.label as facility_name,
                            dept.label as department,
                            personnel.label as assigned_to
                        ORDER BY work_order
                        LIMIT 15
                    """)

                records = result.data()
                if not records:
                    return "No relevant data found in the knowledge graph matching your query."

                context = self._format_query_results(query, records)
                logger.debug(f"Generated context: {context}")
                return context

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return "Unable to retrieve context from the knowledge graph."

    def _format_query_results(self, query: str, records: List[Dict]) -> str:
        """Format query results based on the type of query."""
        if any(keyword in query.lower() for keyword in ['asset', 'equipment', 'machine']):
            if 'facility_name' in records[0] and 'assets' in records[0]:
                # Format facility-grouped assets
                context = "Assets by Facility:\n"
                for record in records:
                    facility = record['facility_name'] or 'Unassigned Facility'
                    context += f"\n{facility}:\n"
                    for asset_info in record['assets']:
                        context += f"  • {asset_info['asset_name']}\n"
                        if asset_info['department']:
                            context += f"    ↳ Department: {asset_info['department']}\n"
                        if asset_info['work_orders']:
                            wo_count = len(asset_info['work_orders'])
                            context += f"    ↳ Associated Work Orders: {wo_count}\n"
            else:
                # Format individual asset records
                context = "Asset Information:\n"
                for record in records:
                    context += f"\n• {record['asset_name']}\n"
                    if record['facility_name']:
                        context += f"  ↳ Location: {record['facility_name']}\n"
                    if record['department']:
                        context += f"  ↳ Department: {record['department']}\n"
                    if record['work_orders']:
                        wo_count = len(record['work_orders'])
                        context += f"  ↳ Associated Work Orders: {wo_count}\n"
        else:
            # Format work order records
            context = "Work Order Information:\n"
            for record in records:
                wo_id = record['work_order'].replace('WO_', 'Work Order ')
                context += f"\n{wo_id}:\n"
                if record['asset_name']:
                    context += f"  • Asset: {record['asset_name']}\n"
                if record['facility_name']:
                    context += f"  • Location: {record['facility_name']}\n"
                if record['department']:
                    context += f"  • Department: {record['department']}\n"
                if record['assigned_to']:
                    context += f"  • Assigned to: {record['assigned_to']}\n"

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