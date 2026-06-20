from app.extensions import db
from datetime import datetime

class DeletionRequest(db.Model):
    __tablename__ = 'deletion_requests'
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id'), nullable=False)
    requested_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum('pending', 'approved', 'rejected', name='deletion_status'), default='pending')
    requested_at = db.Column(db.DateTime, default=db.func.now())
    reviewed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)

    # Relationships (optional)
    evidence = db.relationship('Evidence', backref=db.backref('deletion_requests', cascade='all, delete-orphan'))
    requester = db.relationship('User', foreign_keys=[requested_by], backref=db.backref('requested_deletions', lazy='dynamic'))
    reviewer = db.relationship('User', foreign_keys=[reviewed_by], backref=db.backref('reviewed_deletions', lazy='dynamic'))
