import logging
import os
import time
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Neo4j configuration for embedded mode
NEO4J_URI = "bolt://localhost:7687"
NEO4J_AUTH = ("neo4j", "password")  # Default credentials for development

def wait_for_neo4j(max_retries=5, retry_interval=2):
    """Wait for Neo4j to become available"""
    logger.info(f"Attempting to connect to Neo4j at {NEO4J_URI}")

    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=NEO4J_AUTH
            )
            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1 as num")
                if result.single()['num'] == 1:
                    logger.info("Successfully connected to Neo4j")
                    driver.close()
                    return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} to connect to Neo4j failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)

    logger.error("Failed to connect to Neo4j after multiple attempts")
    return False