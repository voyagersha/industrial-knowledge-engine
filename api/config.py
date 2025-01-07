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

# Get absolute path to the project root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Neo4j configuration
NEO4J_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'neo4j', 'data')
NEO4J_URI = f"file://{NEO4J_DATA_DIR}"  # Use file-based storage
NEO4J_USER = None  # No authentication for embedded mode
NEO4J_PASSWORD = None

# Create Neo4j data directory with correct permissions
os.makedirs(NEO4J_DATA_DIR, exist_ok=True)
try:
    os.chmod(NEO4J_DATA_DIR, 0o777)
except Exception as e:
    logger.warning(f"Could not set permissions on Neo4j data directory: {e}")

def wait_for_neo4j(max_retries=5, retry_interval=1):
    """Wait for Neo4j to become available"""
    from py2neo import Graph

    logger.info(f"Initializing embedded Neo4j database at {NEO4J_URI}")

    for attempt in range(max_retries):
        try:
            graph = Graph(NEO4J_URI)
            # Test connection with a simple query
            graph.run("RETURN 1 as num")
            logger.info("Successfully connected to embedded Neo4j")
            return True
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1}/{max_retries} to initialize Neo4j failed: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(retry_interval)

    logger.error("Failed to initialize Neo4j after multiple attempts")
    return False