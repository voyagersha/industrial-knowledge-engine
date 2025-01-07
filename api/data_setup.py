import os
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_neo4j_directories():
    """Create and set up Neo4j data directories with proper permissions."""
    try:
        # Create base directory in /tmp for better permissions handling
        base_path = Path(tempfile.gettempdir()) / 'neo4j_data'
        base_path.mkdir(exist_ok=True)

        # Define required directories
        directories = {
            'data': base_path / 'data',
            'plugins': base_path / 'plugins',
            'logs': base_path / 'logs',
            'import': base_path / 'import',
            'conf': base_path / 'conf'
        }

        # Create directories with proper permissions
        for dir_name, dir_path in directories.items():
            if dir_path.exists():
                shutil.rmtree(dir_path)
            dir_path.mkdir(parents=True)
            os.chmod(dir_path, 0o777)
            logger.info(f"Created directory with write permissions: {dir_path}")

        # Copy neo4j.conf to the conf directory
        conf_source = Path(__file__).parent.parent / 'neo4j.conf'
        conf_dest = directories['conf'] / 'neo4j.conf'
        if conf_source.exists():
            shutil.copy2(conf_source, conf_dest)
            os.chmod(conf_dest, 0o666)
            logger.info(f"Copied neo4j.conf to: {conf_dest}")

        return str(base_path)
    except Exception as e:
        logger.error(f"Failed to set up Neo4j directories: {str(e)}")
        return None

if __name__ == "__main__":
    setup_neo4j_directories()