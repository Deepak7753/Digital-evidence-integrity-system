from app.extensions import db
from datetime import datetime

class Case(db.Model):
    __tablename__ = 'cases'
    
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Open', nullable=False)  # Open, Active, Closed, Archived
    investigator_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    evidence_links = db.relationship('CaseEvidence', back_populates='case', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Case {self.case_number} - {self.name}>"

class CaseEvidence(db.Model):
    __tablename__ = 'case_evidence'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False)
    linked_at = db.Column(db.DateTime, default=datetime.utcnow)
    linked_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    case = db.relationship('Case', back_populates='evidence_links')
    evidence = db.relationship('Evidence', back_populates='case_links')
    
    def __repr__(self):
        return f"<CaseEvidence Case:{self.case_id} Evidence:{self.evidence_id}>"
