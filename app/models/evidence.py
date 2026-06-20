from app.extensions import db
from datetime import datetime

class Evidence(db.Model):
    __tablename__ = 'evidence'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    stored_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.BigInteger, nullable=False)  # in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Image, Video, Audio, Document, Malware Sample, Network Capture, Mobile Evidence
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    original_hash = db.Column(db.String(64), nullable=False, index=True)  # SHA-256
    is_encrypted = db.Column(db.Boolean, default=True)
    is_tampered = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Verified', nullable=False)  # Verified, Warning, Tampered
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    
    # Relationships
    case_links = db.relationship('CaseEvidence', back_populates='evidence', cascade='all, delete-orphan')
    hashes = db.relationship('EvidenceHash', back_populates='evidence', cascade='all, delete-orphan')
    metadata_entries = db.relationship('EvidenceMetadata', back_populates='evidence', cascade='all, delete-orphan')
    custody_records = db.relationship('CustodyRecord', back_populates='evidence', cascade='all, delete-orphan')
    tamper_alerts = db.relationship('TamperAlert', back_populates='evidence', cascade='all, delete-orphan')
    
    # Uploaded by User relationship
    uploader = db.relationship('User', foreign_keys=[uploaded_by_id], backref=db.backref('uploaded_evidence', lazy='dynamic'))

    @property
    def current_case(self):
        if self.case_links:
            # Return the first linked case (supporting one primary case)
            return self.case_links[0].case
        return None

    def __repr__(self):
        return f"<Evidence {self.id} - {self.file_name}>"

class EvidenceHash(db.Model):
    __tablename__ = 'evidence_hashes'
    
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False)
    hash_val = db.Column(db.String(64), nullable=False)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(20), default='Verified', nullable=False)  # Verified, Warning, Tampered
    
    # Relationships
    evidence = db.relationship('Evidence', back_populates='hashes')
    verifier = db.relationship('User', backref=db.backref('verified_hashes', lazy='dynamic'))
    
    def __repr__(self):
        return f"<EvidenceHash EvidenceID:{self.evidence_id} Status:{self.status}>"

class EvidenceMetadata(db.Model):
    __tablename__ = 'evidence_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    evidence_id = db.Column(db.Integer, db.ForeignKey('evidence.id', ondelete='CASCADE'), nullable=False)
    meta_key = db.Column(db.String(100), nullable=False)
    meta_value = db.Column(db.Text, nullable=True)
    
    # Relationships
    evidence = db.relationship('Evidence', back_populates='metadata_entries')
    
    def __repr__(self):
        return f"<EvidenceMetadata EvidenceID:{self.evidence_id} Key:{self.meta_key}>"
