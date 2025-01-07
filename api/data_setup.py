import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_neo4j_directories():
    """Create and set up Neo4j data directories with proper permissions."""
    base_dirs = [
        'data/neo4j/data',
        'data/neo4j/plugins',
        'data/neo4j/logs',
        'data/neo4j/import'
    ]
    
    try:
        # Create base directories if they don't exist
        for dir_path in base_dirs:
            os.makedirs(dir_path, exist_ok=True)
            # Ensure directory is writable
            os.chmod(dir_path, 0o777)
            logger.info(f"Created directory with write permissions: {dir_path}")
            
        return True
    except Exception as e:
        logger.error(f"Failed to set up Neo4j directories: {str(e)}")
        return False

if __name__ == "__main__":
    setup_neo4j_directories()
