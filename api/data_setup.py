import os
import logging
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_neo4j_directories():
    """Create and set up Neo4j data directories with proper permissions."""
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'neo4j'))
    base_dirs = [
        'data',
        'plugins',
        'logs',
        'import'
    ]

    try:
        # Create base directory if it doesn't exist
        os.makedirs(base_path, exist_ok=True)
        os.chmod(base_path, 0o777)

        # Create and set permissions for subdirectories
        for dir_name in base_dirs:
            dir_path = os.path.join(base_path, dir_name)
            # Remove directory if it exists to ensure clean state
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            # Create directory with proper permissions
            os.makedirs(dir_path)
            os.chmod(dir_path, 0o777)
            logger.info(f"Created directory with write permissions: {dir_path}")

        return True
    except Exception as e:
        logger.error(f"Failed to set up Neo4j directories: {str(e)}")
        return False

if __name__ == "__main__":
    setup_neo4j_directories()