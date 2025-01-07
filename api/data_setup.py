import os
import logging
import shutil
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_neo4j_directories():
    """Create and set up Neo4j data directories with proper permissions."""
    try:
        # Create base directory in /tmp for Neo4j data
        base_path = Path(tempfile.gettempdir()) / 'neo4j_data'
        if base_path.exists():
            shutil.rmtree(base_path)
        base_path.mkdir(exist_ok=True)
        os.chmod(base_path, 0o777)

        # Define and create required directories with proper permissions
        directories = {
            'data': base_path / 'data',
            'plugins': base_path / 'plugins',
            'logs': base_path / 'logs',
            'import': base_path / 'import',
            'conf': base_path / 'conf',
            'metrics': base_path / 'metrics',
            'lib': base_path / 'lib',
            'run': base_path / 'run',
            'certificates': base_path / 'certificates'
        }

        # Create all directories with proper permissions
        for dir_name, dir_path in directories.items():
            dir_path.mkdir(parents=True, exist_ok=True)
            os.chmod(dir_path, 0o777)
            logger.info(f"Created directory with write permissions: {dir_path}")

        # Create necessary log files with proper permissions
        log_files = ['neo4j.log', 'debug.log', 'http.log', 'query.log', 'security.log']
        for log_file in log_files:
            log_path = directories['logs'] / log_file
            log_path.touch(exist_ok=True)
            os.chmod(log_path, 0o666)
            logger.info(f"Created log file with write permissions: {log_path}")

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

def main():
    """Main function to set up Neo4j environment."""
    logger.info("Setting up Neo4j environment...")
    base_path = setup_neo4j_directories()
    if base_path:
        logger.info(f"Successfully set up Neo4j environment at: {base_path}")
        return 0
    return 1

if __name__ == "__main__":
    exit(main())