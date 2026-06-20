from app.extensions import db
from datetime import datetime

class CustodyRecord(db.Model):
    __tablename__ = 'custody_records'
    
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False)
    from_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    to_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # e.g., Uploaded, Transferred, Downloaded, Verified
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    
    # Relationships
    evidence = db.relationship('Evidence', back_populates='custody_records')
    from_user = db.relationship('User', foreign_keys=[from_user_id], backref=db.backref('custody_sent', lazy='dynamic'))
    to_user = db.relationship('User', foreign_keys=[to_user_id], backref=db.backref('custody_received', lazy='dynamic'))
    
    def __repr__(self):
        return f"<CustodyRecord EvidenceID:{self.evidence_id} Action:{self.action}>"
