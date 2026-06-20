from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(*roles):
    """
    Decorator to restrict access to specific user roles.
    Example: @role_required('admin', 'investigator')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
            
            # Check if user has any of the required roles
            has_valid_role = any(current_user.has_role(r) for r in roles)
            if not has_valid_role:
                abort(403)  # Forbidden
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
