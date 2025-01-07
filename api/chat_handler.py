import os
import logging
from typing import Dict, List, Optional, Tuple
from openai import OpenAI
from neo4j import GraphDatabase
import json
from datetime import datetime, timedelta
from functools import lru_cache
import numpy as np

logger = logging.getLogger(__name__)

class ChatHandler:
    def __init__(self):
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        self.openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        try:
            # Initialize embedded Neo4j connection
            self.neo4j_driver = GraphDatabase.driver(
                os.environ.get('NEO4J_URI', "file://./data/neo4j"),
                auth=(None, None)  # No auth needed for embedded mode
            )
            # Test connection
            with self.neo4j_driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j (embedded mode)")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            raise Exception("Neo4j connection failed")

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

    def _get_relevant_context(self, query: str) -> Dict:
        """Get relevant context based on query analysis."""
        query_lower = query.lower()
        context_type = self._analyze_query_type(query_lower)

        try:
            with self.neo4j_driver.session() as session:
                if context_type == 'facility':
                    return self._get_facility_context(session, query_lower)
                elif context_type == 'asset':
                    return self._get_asset_context(session, query_lower)
                else:
                    return self._get_general_context(session)
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            raise

    def _analyze_query_type(self, query: str) -> str:
        """Analyze query to determine the type of information needed."""
        if any(word in query for word in ['facility', 'plant', 'location', 'site']):
            return 'facility'
        elif any(word in query for word in ['asset', 'equipment', 'machine']):
            return 'asset'
        return 'general'

    def _get_facility_context(self, session, query: str) -> Dict:
        """Get facility-specific context including all assets in that facility."""
        # Extract facility name from query (basic implementation)
        facility_terms = ['plant', 'facility']
        words = query.split()
        facility_name = None

        for i, word in enumerate(words):
            if word in facility_terms and i + 1 < len(words):
                facility_name = words[i + 1]
                break

        if not facility_name:
            return {"error": "No facility specified in query"}

        # Query for facility and its assets
        result = session.run("""
            MATCH (f:Entity)
            WHERE f.type = 'Facility' AND toLower(f.label) CONTAINS toLower($facility_name)
            OPTIONAL MATCH (a:Entity)-[:LOCATED_IN]->(f)
            WHERE a.type = 'Asset'
            RETURN f.label as facility,
                   collect(DISTINCT {
                       name: a.label,
                       type: a.type
                   }) as assets
        """, facility_name=facility_name)

        records = result.data()

        if not records:
            return {
                "message": f"No facility found matching '{facility_name}'",
                "suggestions": self._get_available_facilities(session)
            }

        return {
            "type": "facility_context",
            "data": records,
            "query_facility": facility_name
        }

    def _get_available_facilities(self, session) -> Dict:
        """Get list of available facilities when specified facility not found."""
        result = session.run("""
            MATCH (f:Entity)
            WHERE f.type = 'Facility'
            RETURN collect(DISTINCT f.label) as facilities
        """)
        facilities = result.single()["facilities"]
        return {
            "type": "facility_list",
            "facilities": facilities
        }


    def _get_asset_context(self, session, query: str) -> Dict:
        """Get asset specific context"""
        #This is a placeholder,  needs a more robust implementation to extract asset name
        asset_name = query.split()[0] # Basic implementation, improve as needed.
        result = session.run("""
            MATCH (a:Entity)
            WHERE a.type = 'Asset' AND toLower(a.label) CONTAINS toLower($asset_name)
            OPTIONAL MATCH (a)-[:LOCATED_IN]->(f:Entity)
            RETURN a.label as asset, f.label as facility
        """, asset_name=asset_name)
        records = result.data()
        if not records:
            return {"message": f"No asset found matching '{asset_name}'"}
        return {"type": "asset_context", "data": records}


    def _get_general_context(self, session) -> Dict:
        """Get general context from the graph."""
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
        return {"type": "general_context", "data": records}


    def get_response(self, user_query: str) -> Dict:
        """Generate response using RAG with Neo4j context."""
        try:
            # Get relevant context based on query type
            context = self._get_relevant_context(user_query)

            if "error" in context:
                return {
                    "response": f"Error: {context['error']}. Please try rephrasing your question.",
                    "context": str(context)
                }

            # Format context for GPT
            formatted_context = self._format_context_for_gpt(context)

            system_message = """You are a knowledgeable assistant that helps users understand their enterprise asset management data.
            When asked about specific facilities or assets:
            1. Be precise about asset names, locations, and relationships
            2. If a facility is not found, suggest available facilities
            3. Include relevant asset counts and statistics
            4. Always mention if the data seems incomplete
            5. Keep responses clear and structured"""

            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_message},
                    {
                        "role": "user", 
                        "content": f"Based on this context:\n{formatted_context}\n\nQuestion: {user_query}"
                    }
                ]
            )

            return {
                "response": response.choices[0].message.content,
                "context": formatted_context
            }

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {
                "error": "Failed to process your question",
                "details": str(e)
            }

    def _format_context_for_gpt(self, context: Dict) -> str:
        """Format Neo4j context for GPT consumption."""
        if context["type"] == "facility_context":
            facility_data = context["data"][0]
            formatted = f"Facility Information:\n"
            formatted += f"Facility: {facility_data['facility']}\n"
            formatted += f"Number of Assets: {len(facility_data['assets'])}\n"

            if facility_data['assets']:
                formatted += "\nAssets:\n"
                for asset in facility_data['assets']:
                    formatted += f"- {asset['name']} ({asset['type']})\n"
            else:
                formatted += "\nNo assets found in this facility.\n"

            return formatted

        elif context["type"] == "facility_list":
            return f"Available Facilities:\n" + \
                   "\n".join([f"- {f}" for f in context["facilities"]])
        elif context["type"] == "asset_context":
            asset_data = context["data"][0]
            formatted = f"Asset Information:\n"
            formatted += f"Asset: {asset_data['asset']}\n"
            if asset_data['facility']:
                formatted += f"Facility: {asset_data['facility']}\n"
            return formatted
        elif context["type"] == "general_context":
            formatted = "General Context:\n"
            for record in context["data"]:
                formatted += f"\n{record['type']}: {record['entity']}"
                for rel in record['relations']:
                    if rel['label']:
                        formatted += f"\n  {rel['relation']} -> {rel['label']} ({rel['type']})"
            return formatted

        return str(context)

    def close(self):
        """Clean up resources."""
        if self.neo4j_driver:
            self.neo4j_driver.close()