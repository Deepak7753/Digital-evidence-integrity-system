from app.extensions import db
from datetime import datetime

class TamperAlert(db.Model):
    __tablename__ = 'tamper_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False, default='HASH_MISMATCH')  # HASH_MISMATCH, ENCRYPTION_ERROR, CUSTODY_VIOLATION
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Active', nullable=False)  # Active, Resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    evidence = db.relationship('Evidence', back_populates='tamper_alerts')
    
    def __repr__(self):
        return f"<TamperAlert EvidenceID:{self.evidence_id} Type:{self.alert_type}>"
