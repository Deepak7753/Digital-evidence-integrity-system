from app.extensions import db
from .user import User, Role, user_roles
from .case import Case, CaseEvidence
from .evidence import Evidence, EvidenceHash, EvidenceMetadata
from .custody import CustodyRecord
from .audit import AuditLog
from .report import Report
from .notification import Notification
from .deletion_request import DeletionRequest

def init_models():
    """
    Dummy function just to force imports of all modules 
    so SQLAlchemy is aware of them for migrations/table creation.
    """
    pass
