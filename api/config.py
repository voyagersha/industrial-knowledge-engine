import logging
import os
import time

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Neo4j configuration
NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://127.0.0.1:7687')  # Use localhost for client connections
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = ""  # Auth is disabled in our configuration

# Ensure Neo4j directories exist
os.makedirs('./data/neo4j/data', exist_ok=True)
os.makedirs('./data/neo4j/plugins', exist_ok=True)
os.makedirs('./data/neo4j/logs', exist_ok=True)
os.makedirs('./data/neo4j/import', exist_ok=True)

def wait_for_neo4j(max_retries=60, retry_interval=2):
    """Wait for Neo4j to become available"""
    from neo4j import GraphDatabase

    logger.info(f"Waiting for Neo4j to become available at {NEO4J_URI}")

    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD)
            )
            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
            driver.close()
            logger.info("Successfully connected to Neo4j")
            return True
        except Exception as e:
            if "address already in use" in str(e).lower():
                logger.error(f"Neo4j port is already in use: {str(e)}")
                return False
            logger.warning(f"Attempt {attempt + 1}/{max_retries} to connect to Neo4j failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)

    logger.error("Failed to connect to Neo4j after multiple attempts")
    return False