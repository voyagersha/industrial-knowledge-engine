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
                # Create a more comprehensive query that looks for relevant information
                result = session.run("""
                    // Find work orders and their immediate relationships
                    MATCH (wo:Entity {type: 'WorkOrder'})-[r1]-(related1)

                    // Get secondary relationships to gather more context
                    OPTIONAL MATCH (related1)-[r2]-(related2)
                    WHERE related2 <> wo

                    // Get tertiary relationships for deeper context
                    OPTIONAL MATCH (related2)-[r3]-(related3)
                    WHERE related3 <> related1 AND related3 <> wo

                    RETURN 
                        wo.label as work_order,
                        wo.type as work_order_type,
                        type(r1) as primary_relation,
                        related1.label as related_entity1,
                        related1.type as entity1_type,
                        type(r2) as secondary_relation,
                        related2.label as related_entity2,
                        related2.type as entity2_type,
                        type(r3) as tertiary_relation,
                        related3.label as related_entity3,
                        related3.type as entity3_type
                    ORDER BY work_order
                    LIMIT 15
                """)

                records = result.data()
                if not records:
                    return "No relevant work order data found in the knowledge graph."

                context = "Work Order Information:\n"
                current_wo = None

                for record in records:
                    wo_id = record['work_order']

                    # Start a new work order section if it's different
                    if wo_id != current_wo:
                        current_wo = wo_id
                        wo_display = wo_id.replace('WO_', 'Work Order ')
                        context += f"\n{wo_display}:\n"

                    # Add primary relationship
                    if record['primary_relation']:
                        label = self._format_relationship(
                            record['primary_relation'],
                            record['related_entity1'],
                            record['entity1_type']
                        )
                        context += f"  • {label}\n"

                    # Add secondary relationship if exists
                    if record['secondary_relation']:
                        label = self._format_relationship(
                            record['secondary_relation'],
                            record['related_entity2'],
                            record['entity2_type']
                        )
                        context += f"    ↳ {label}\n"

                    # Add tertiary relationship if exists
                    if record['tertiary_relation']:
                        label = self._format_relationship(
                            record['tertiary_relation'],
                            record['related_entity3'],
                            record['entity3_type']
                        )
                        context += f"      ↳ {label}\n"

                logger.debug(f"Generated context: {context}")
                return context

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return "Unable to retrieve context from the knowledge graph."

    def _format_relationship(self, relation_type: str, entity: str, entity_type: str) -> str:
        """Format relationship information in a readable way."""
        relation_map = {
            'MAINTAINS': 'Maintains',
            'LOCATED_IN': 'Located in',
            'BELONGS_TO': 'Belongs to',
            'ASSIGNED_TO': 'Assigned to',
            'RELATED_TO': 'Related to',
            'PART_OF': 'Part of',
            'REPORTS_TO': 'Reports to'
        }

        relation = relation_map.get(relation_type, relation_type.replace('_', ' ').title())
        return f"{relation}: {entity} ({entity_type})"

    def get_response(self, user_query: str) -> Dict:
        """Get response from OpenAI based on Neo4j context."""
        try:
            # Get relevant context from Neo4j
            graph_context = self._get_graph_context(user_query)

            # Construct prompt with context
            system_message = """You are a knowledgeable assistant that helps users understand work order and maintenance data.
            Your responses should:
            1. Be specific, citing work order IDs, asset names, and other entities when relevant
            2. Explain relationships between different entities clearly
            3. If you can't find specific information, explain what data would be needed
            4. Keep responses concise but informative"""

            user_prompt = f"""Based on the following work order information from our knowledge graph:

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