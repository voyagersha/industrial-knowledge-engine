from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from flask_login import UserMixin

class Node(db.Model):
    """Represents a node in the knowledge graph"""
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes for better query performance
    __table_args__ = (
        db.Index('idx_node_label_type', 'label', 'type'),
        db.Index('idx_node_type', 'type'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'type': self.type,
            'properties': self.properties or {},
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f'<Node {self.type}:{self.label}>'

class Edge(db.Model):
    """Represents a relationship between nodes"""
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('node.id', ondelete='CASCADE'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('node.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    source = db.relationship('Node', foreign_keys=[source_id], backref=db.backref('outgoing_edges', lazy='dynamic'))
    target = db.relationship('Node', foreign_keys=[target_id], backref=db.backref('incoming_edges', lazy='dynamic'))

    # Indexes for better query performance
    __table_args__ = (
        db.Index('idx_edge_source_target', 'source_id', 'target_id'),
        db.Index('idx_edge_type', 'type'),
    )

    def to_dict(self):
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
        return f'<Edge {self.type} from {self.source_id} to {self.target_id}>'

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username}>'