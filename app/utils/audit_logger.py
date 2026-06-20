from flask import request, has_request_context
from flask_login import current_user
from app.extensions import db
from app.models.audit import AuditLog
from datetime import datetime

def log_audit_action(action: str, user_id: int = None, details: str = None) -> None:
    """
    Log an event to the AuditLog database table.
    Automatically grabs IP and browser context if within an active Flask request.
    """
    ip_address = None
    browser = None
    
    if has_request_context():
        # Get client IP address
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0]
        else:
            ip_address = request.remote_addr
            
        # Get browser info
        if request.user_agent:
            browser = request.user_agent.string[:255]
            
    # Default user if not specified
    if not user_id and current_user and current_user.is_authenticated:
        user_id = current_user.id
        
    full_action = action
    if details:
        full_action = f"{action} | Details: {details}"
        
    log_entry = AuditLog(
        user_id=user_id,
        action=full_action[:255],
        ip_address=ip_address,
        browser=browser,
        timestamp=datetime.utcnow()
    )
    
    try:
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Fallback to standard app logging if database log fails
        from flask import current_app
        current_app.logger.error(f"Failed to write audit log: {str(e)}")
