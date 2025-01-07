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
                # Example queries based on common work order questions
                if "asset" in query.lower():
                    result = session.run("""
                        MATCH (a:Entity {type: 'Asset'})-[r]-(related)
                        RETURN a.label as asset, type(r) as relationship, 
                               related.label as related_entity, related.type as entity_type
                        LIMIT 5
                    """)
                elif "facility" in query.lower():
                    result = session.run("""
                        MATCH (f:Entity {type: 'Facility'})-[r]-(related)
                        RETURN f.label as facility, type(r) as relationship,
                               related.label as related_entity, related.type as entity_type
                        LIMIT 5
                    """)
                else:
                    # General query to get a sample of relationships
                    result = session.run("""
                        MATCH (n)-[r]-(m)
                        RETURN n.label as source, type(r) as relationship,
                               m.label as target, m.type as target_type
                        LIMIT 5
                    """)
                
                records = result.data()
                context = "Based on the work order data:\n"
                for record in records:
                    context += f"- {record.get('source', record.get('asset', record.get('facility')))} "
                    context += f"{record['relationship']} {record['target'] if 'target' in record else record['related_entity']}\n"
                
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
            Use the following context to answer the user's question:
            
            {graph_context}
            
            User's question: {user_query}
            
            Provide a clear, concise answer based on the available information. If you cannot find relevant information
            in the context, say so explicitly."""

            # Get completion from OpenAI
            response = self.openai.chat.completions.create(
                model="gpt-4o",  # Latest model as of May 13, 2024
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that provides information about work orders and maintenance records."},
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
