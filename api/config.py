import logging
import os
import time
import tempfile
from py2neo import Graph

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a temporary directory for Neo4j data
TEMP_DIR = tempfile.mkdtemp()
NEO4J_URI = "bolt://localhost:7687"


def wait_for_neo4j(max_retries=5, retry_interval=1):
    """Wait for Neo4j to become available"""
    logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}")

    for attempt in range(max_retries):
        try:
            graph = Graph(NEO4J_URI)
            # Test connection with a simple query
            graph.run("RETURN 1")
            logger.info("Successfully connected to Neo4j")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} to connect to Neo4j failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)

    logger.error("Failed to connect to Neo4j after multiple attempts")
    return False