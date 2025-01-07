import os
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from neo4j import GraphDatabase
import json
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        try:
            self.neo4j_driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Test connection
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise Exception("Neo4j connection failed. Please ensure the database is running.")

        # Initialize cache for embeddings
        self.embedding_cache = {}
        self.cache_ttl = timedelta(hours=1)

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

    def _get_graph_context(self, query: str) -> str:
        """Query Neo4j based on semantic understanding of the question."""
        try:
            with self.neo4j_driver.session() as session:
                # Basic query to verify connection and data existence
                test_result = session.run("""
                    MATCH (n:Entity) 
                    RETURN count(n) as count
                """).single()

                if test_result and test_result["count"] == 0:
                    return "The knowledge graph is empty. Please ensure data has been imported."

                # Simple initial query to test data retrieval
                result = session.run("""
                    MATCH (n:Entity)
                    RETURN n.label as label, n.type as type
                    LIMIT 5
                """)

                records = result.data()
                if not records:
                    return "No data found in the knowledge graph. Please verify data import."

                # If basic queries work, proceed with actual querying
                query_lower = query.lower()

                if "asset" in query_lower:
                    result = session.run("""
                        MATCH (asset:Entity {type: 'Asset'})
                        OPTIONAL MATCH (asset)-[:LOCATED_IN]->(facility:Entity {type: 'Facility'})
                        OPTIONAL MATCH (asset)-[:BELONGS_TO]->(dept:Entity {type: 'Department'})
                        RETURN 
                            asset.label as asset_name,
                            facility.label as facility_name,
                            dept.label as department_name
                    """)
                elif "facility" in query_lower or "plant" in query_lower:
                    result = session.run("""
                        MATCH (facility:Entity {type: 'Facility'})
                        OPTIONAL MATCH (asset:Entity {type: 'Asset'})-[:LOCATED_IN]->(facility)
                        RETURN 
                            facility.label as facility_name,
                            collect(asset.label) as assets
                    """)
                else:
                    result = session.run("""
                        MATCH (n:Entity)
                        OPTIONAL MATCH (n)-[r]-(related:Entity)
                        RETURN 
                            n.label as entity,
                            n.type as type,
                            collect({
                                label: related.label,
                                type: related.type,
                                relation: type(r)
                            }) as relations
                        LIMIT 10
                    """)

                records = result.data()

                # Format response
                context = "Knowledge Graph Information:\n"
                for record in records:
                    if 'asset_name' in record:
                        context += f"\nAsset: {record['asset_name']}"
                        if record['facility_name']:
                            context += f"\n  Location: {record['facility_name']}"
                        if record['department_name']:
                            context += f"\n  Department: {record['department_name']}"
                    elif 'facility_name' in record:
                        context += f"\nFacility: {record['facility_name']}"
                        if record['assets']:
                            context += "\n  Assets:"
                            for asset in record['assets']:
                                context += f"\n    - {asset}"
                    else:
                        context += f"\n{record['type']}: {record['entity']}"
                        for rel in record['relations']:
                            if rel['label']:
                                context += f"\n  {rel['relation']} -> {rel['label']} ({rel['type']})"

                return context

        except Exception as e:
            logger.error(f"Error querying Neo4j: {str(e)}")
            return f"Error accessing the knowledge graph: {str(e)}"

    def get_response(self, user_query: str) -> Dict:
        """Get response from OpenAI based on Neo4j context with semantic understanding."""
        try:
            # Get relevant context from Neo4j
            graph_context = self._get_graph_context(user_query)

            if graph_context.startswith("Error"):
                return {
                    "response": "I apologize, but I'm having trouble accessing the knowledge graph data. Please ensure the system is properly set up and try again.",
                    "context": graph_context
                }

            system_message = """You are a knowledgeable assistant that helps users understand work order and maintenance data.
            Your responses should:
            1. Be specific about assets, locations, and departments
            2. Include relevant statistics when available
            3. Explain relationships clearly and concisely
            4. If information is missing, explain what specific data would help
            5. Keep responses structured and easy to understand"""

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