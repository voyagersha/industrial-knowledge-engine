from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import text
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the Flask app"""
    try:
        db.init_app(app)

        with app.app_context():
            # Create all tables
            db.create_all()

            # Enable PostgreSQL extensions we need
            db.session.execute(text('CREATE EXTENSION IF NOT EXISTS btree_gist'))
            db.session.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm'))
            db.session.commit()

            logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}", exc_info=True)
        raise

def recursive_graph_query(start_node_id: int, relationship_type: Optional[str] = None, max_depth: int = 5) -> List[Dict[str, Any]]:
    """
    Execute a recursive CTE query to traverse the graph
    Args:
        start_node_id: The ID of the starting node
        relationship_type: Optional filter for relationship type
        max_depth: Maximum depth of traversal (default: 5)
    Returns:
        List of dictionaries containing node information and path
    """
    try:
        relationship_filter = ""
        if relationship_type:
            relationship_filter = f"AND e.type = '{relationship_type}'"

        query = text(f"""
        WITH RECURSIVE graph_traversal AS (
            -- Base case: start node
            SELECT 
                n.id,
                n.label,
                n.type,
                n.properties,
                ARRAY[n.id] as path,
                0 as depth
            FROM node n
            WHERE n.id = :start_node_id

            UNION ALL

            -- Recursive case: follow relationships
            SELECT 
                next_node.id,
                next_node.label,
                next_node.type,
                next_node.properties,
                gt.path || next_node.id,
                gt.depth + 1
            FROM graph_traversal gt
            JOIN edge e ON gt.id = e.source_id
            JOIN node next_node ON e.target_id = next_node.id
            WHERE gt.depth < :max_depth
            {relationship_filter}
            AND NOT next_node.id = ANY(gt.path)  -- Prevent cycles
        )
        SELECT 
            id,
            label,
            type,
            properties,
            path,
            depth
        FROM graph_traversal
        ORDER BY depth, id;
        """)

        result = db.session.execute(
            query,
            {"start_node_id": start_node_id, "max_depth": max_depth}
        )

        return [dict(row) for row in result]

    except Exception as e:
        logger.error(f"Error in recursive graph query: {str(e)}", exc_info=True)
        raise