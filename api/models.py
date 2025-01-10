from database import db
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB

class Node(db.Model):
    """Represents a node in the knowledge graph"""
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Node {self.type}:{self.label}>'

class Edge(db.Model):
    """Represents a relationship between nodes"""
    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('node.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    properties = db.Column(JSONB)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source = db.relationship('Node', foreign_keys=[source_id], backref=db.backref('outgoing_edges', lazy='dynamic'))
    target = db.relationship('Node', foreign_keys=[target_id], backref=db.backref('incoming_edges', lazy='dynamic'))

    def __repr__(self):
        return f'<Edge {self.type} from {self.source_id} to {self.target_id}>'