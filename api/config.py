import logging
import os
import time
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Neo4j configuration
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = None  # Auth is disabled in our configuration
NEO4J_PASSWORD = None

# Ensure Neo4j directories exist with correct permissions
NEO4J_DIRS = [
    'data/neo4j/data',
    'data/neo4j/plugins',
    'data/neo4j/logs',
    'data/neo4j/import'
]

for dir_path in NEO4J_DIRS:
    try:
        os.makedirs(dir_path, exist_ok=True)
        # Ensure directory is writable
        os.chmod(dir_path, 0o777)
    except Exception as e:
        logger.error(f"Failed to create/configure directory {dir_path}: {str(e)}")

def wait_for_neo4j(max_retries=30, retry_interval=1):
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