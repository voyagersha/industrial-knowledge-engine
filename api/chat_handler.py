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
                # Get all relevant work order relationships
                result = session.run("""
                    MATCH (wo:Entity {type: 'WorkOrder'})-[r1]-(related1)
                    OPTIONAL MATCH (related1)-[r2]-(related2)
                    WHERE related2 <> wo
                    RETURN 
                        wo.label as work_order,
                        type(r1) as primary_relation,
                        related1.label as related_entity1,
                        related1.type as entity1_type,
                        type(r2) as secondary_relation,
                        related2.label as related_entity2,
                        related2.type as entity2_type
                    LIMIT 10
                """)

                records = result.data()
                if not records:
                    return "No work order data found in the knowledge graph."

                context = "Work Order Information:\n"
                for record in records:
                    wo_id = record['work_order'].replace('WO_', 'Work Order ')
                    context += f"\n- {wo_id}:\n"

                    # Primary relationship
                    if record['primary_relation'] == 'MAINTAINS':
                        context += f"  • Maintains: {record['related_entity1']} ({record['entity1_type']})\n"
                    elif record['primary_relation'] == 'ASSIGNED_TO':
                        context += f"  • Assigned to: {record['related_entity1']} ({record['entity1_type']})\n"

                    # Secondary relationships
                    if record['secondary_relation']:
                        if record['secondary_relation'] == 'LOCATED_IN':
                            context += f"  • Location: {record['related_entity2']} ({record['entity2_type']})\n"
                        elif record['secondary_relation'] == 'BELONGS_TO':
                            context += f"  • Department: {record['related_entity2']} ({record['entity2_type']})\n"

                return context

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return "Unable to retrieve context from the knowledge graph."

    def get_response(self, user_query: str) -> Dict:
        """Get response from OpenAI based on Neo4j context."""
        try:
            # Get relevant context from Neo4j
            graph_context = self._get_graph_context(user_query)

            # Construct prompt with context
            prompt = f"""You are an AI assistant that helps users understand work order data stored in a knowledge graph.

            Here's the current work order information from our knowledge graph:

            {graph_context}

            User's question: {user_query}

            Please provide a clear, specific answer based on the work order information above. If you can't find relevant information
            in the context to answer the question, please say what specific information you would need to answer it."""

            # Get completion from OpenAI
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides specific information about work orders and maintenance records. Always reference specific work orders, assets, or personnel in your responses when possible."},
                    {"role": "user", "content": prompt}
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