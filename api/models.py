"""
Database models for the AI-Powered Industrial Data Management Platform.

This module defines the SQLAlchemy ORM models that represent the core entities
of our knowledge graph system:

- Node: Represents vertices in the knowledge graph (assets, facilities, etc.)
- Edge: Represents relationships between nodes
- User: Handles user authentication and management

Each model includes comprehensive indexing for optimized query performance
and proper cascade behaviors for maintaining referential integrity.
"""

from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from flask_login import UserMixin

class Node(db.Model):
    """
    Represents a node (vertex) in the knowledge graph.

    Nodes can represent various entity types such as assets, facilities,
    departments, or work orders. Each node has a type, label, and optional
    JSON properties for flexible attribute storage.

    Attributes:
        id (int): Primary key
        label (str): Human-readable label for the node
        type (str): Entity type (e.g., 'Asset', 'Facility')
        properties (JSONB): Flexible JSON storage for additional attributes
        created_at (datetime): Timestamp of node creation
        updated_at (datetime): Timestamp of last update
    """
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for better query performance
    __table_args__ = (
        db.Index('idx_node_label_type', 'label', 'type'),  # Composite index for label+type queries
        db.Index('idx_node_type', 'type'),                 # Index for type-based filtering
    )

    def to_dict(self):
        """
        Convert the node to a dictionary representation.

        Returns:
            dict: Node data including all attributes and timestamps
        """
        return {
            'id': self.id,
            'label': self.label,
            'type': self.type,
            'properties': self.properties or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        """String representation of the Node."""
        return f'<Node {self.type}:{self.label}>'

class Edge(db.Model):
    """
    Represents a relationship (edge) between two nodes in the knowledge graph.

    Edges define directed relationships between nodes, including the relationship
    type and optional properties. Implements proper cascade behavior to maintain
    referential integrity when nodes are deleted.

    Attributes:
        id (int): Primary key
        source_id (int): Foreign key to source node
        target_id (int): Foreign key to target node
        type (str): Relationship type
        properties (JSONB): Flexible JSON storage for relationship attributes
        created_at (datetime): Timestamp of edge creation
        updated_at (datetime): Timestamp of last update
    """
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('node.id', ondelete='CASCADE'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('node.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships with automatic backref population
    source = db.relationship('Node', foreign_keys=[source_id], backref=db.backref('outgoing_edges', lazy='dynamic'))
    target = db.relationship('Node', foreign_keys=[target_id], backref=db.backref('incoming_edges', lazy='dynamic'))

    # Indexes for better query performance
    __table_args__ = (
        db.Index('idx_edge_source_target', 'source_id', 'target_id'),  # Composite index for edge traversal
        db.Index('idx_edge_type', 'type'),                            # Index for type-based filtering
    )

    def to_dict(self):
        """
        Convert the edge to a dictionary representation.

        Returns:
            dict: Edge data including all attributes and timestamps
        """
        return {
            'id': self.id,
            'source_id': self.source_id,
            'target_id': self.target_id,
            'type': self.type,
            'properties': self.properties or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        """String representation of the Edge."""
        return f'<Edge {self.type} from {self.source_id} to {self.target_id}>'

class User(UserMixin, db.Model):
    """
    User model for authentication and access control.

    Implements Flask-Login's UserMixin for authentication functionality.
    Stores basic user information and tracks account status.

    Attributes:
        id (int): Primary key
        username (str): Unique username
        email (str): Unique email address
        password_hash (str): Securely hashed password
        is_active (bool): Account status
        created_at (datetime): Account creation timestamp
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        """String representation of the User."""
        return f'<User {self.username}>'