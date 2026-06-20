from app.extensions import db
from datetime import datetime

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)  # Path to stored PDF on server
    generated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    generated_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    # Relationships
    case = db.relationship('Case', backref=db.backref('reports', lazy='dynamic'))
    generator = db.relationship('User', backref=db.backref('generated_reports', lazy='dynamic'))
    
    def __repr__(self):
        return f"<Report CaseID:{self.case_id} Name:{self.name}>"
