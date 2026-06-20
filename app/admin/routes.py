from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models.user import User, Role
from app.models.audit import AuditLog
from app.models.tamper import TamperAlert
from app.models.notification import Notification
from app.auth.decorators import role_required
from app.utils.audit_logger import log_audit_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/users')
@login_required
@role_required('admin')
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    roles = Role.query.all()
    return render_template('admin/users.html', users=users, roles=roles)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('❌ You cannot disable your own administrator account.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    user.is_active = not user.is_active
    # If locking/unlocking, clear failed attempts
    if user.is_active:
        user.failed_attempts = 0
        user.locked_until = None
        
    db.session.commit()
    
    status_str = "Enabled" if user.is_active else "Disabled"
    log_audit_action("Modified User Status", current_user.id, f"User: {user.username}, New Status: {status_str}")
    flash(f"✅ User account status for {user.fullname} updated to: {status_str}.", 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@role_required('admin')
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('❌ You cannot change your own administrator role.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    role_name = request.form.get('role')
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        flash('❌ Selected role does not exist.', 'danger')
        return redirect(url_for('admin.list_users'))
        
    # Re-assign role (assuming single primary role matching many-to-many list)
    user.roles = [role]
    db.session.commit()
    
    log_audit_action("Modified User Role", current_user.id, f"User: {user.username}, New Role: {role_name}")
    flash(f"✅ Role for {user.fullname} updated to: {role_name.upper()}.", 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/audit-logs')
@login_required
@role_required('admin', 'auditor')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/audit_logs.html', logs=logs)

@admin_bp.route('/tamper-alerts')
@login_required
@role_required('admin')
def tamper_alerts():
    alerts = TamperAlert.query.order_by(TamperAlert.created_at.desc()).all()
    return render_template('admin/tamper_alerts.html', alerts=alerts)

@admin_bp.route('/tamper-alerts/<int:alert_id>/resolve', methods=['POST'])
@login_required
@role_required('admin')
def resolve_alert(alert_id):
    alert = TamperAlert.query.get_or_404(alert_id)
    alert.status = 'Resolved'
    
    # Update matching evidence status if resolved (e.g. restore verified status manually after database audit)
    resolution_note = request.form.get('note', 'Manually resolved by administrator.')
    alert.description = f"{alert.description} | RESOLUTION: {resolution_note}"
    
    db.session.commit()
    log_audit_action("Resolved Tamper Alert", current_user.id, f"Alert ID: {alert_id}, Resolution: {resolution_note}")
    flash('✅ Alert marked as resolved.', 'success')
    return redirect(url_for('admin.tamper_alerts'))

# ==================== USER APPROVAL MANAGEMENT ====================

@admin_bp.route('/pending-approvals')
@login_required
@role_required('admin')
def pending_approvals():
    """Display list of users pending approval"""
    pending_users = User.query.filter_by(approval_status='pending').order_by(User.created_at.desc()).all()
    approved_users = User.query.filter_by(approval_status='approved').order_by(User.created_at.desc()).all()
    rejected_users = User.query.filter_by(approval_status='rejected').order_by(User.created_at.desc()).all()
    
    return render_template('admin/pending_approvals.html', 
                          pending_users=pending_users,
                          approved_users=approved_users,
                          rejected_users=rejected_users)

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_user(user_id):
    """Approve a pending user"""
    user = User.query.get_or_404(user_id)
    
    if user.approval_status == 'approved':
        flash(f'⚠️ User {user.username} is already approved.', 'warning')
        return redirect(url_for('admin.pending_approvals'))
    
    from datetime import datetime
    user.is_approved = True
    user.approval_status = 'approved'
    user.approval_date = datetime.utcnow()
    user.approved_by_id = current_user.id
    
    db.session.commit()
    
    # Notify the user
    from app.models.notification import Notification
    notification = Notification(
        user_id=user.id,
        title="✅ Account Approved",
        message=f"Your account has been approved by admin. You can now log in.",
        type="user"
    )
    db.session.add(notification)
    db.session.commit()
    
    log_audit_action("User Approved", current_user.id, f"User: {user.username}, Role: {user.primary_role}")
    flash(f'✅ User {user.username} has been APPROVED and can now login.', 'success')
    return redirect(url_for('admin.pending_approvals'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('❌ You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.list_users'))
    
    # Delete associated notifications to avoid foreign‑key constraint errors
    Notification.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.delete(user)
    db.session.commit()
    
    log_audit_action("User Deleted", current_user.id, f"User: {user.username} (ID: {user_id})")
    flash(f'✅ User {user.username} has been deleted.', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_user(user_id):
    """Reject a pending user"""
    user = User.query.get_or_404(user_id)
    
    if user.approval_status in ['rejected', 'approved']:
        flash(f'⚠️ User {user.username} has already been processed.', 'warning')
        return redirect(url_for('admin.pending_approvals'))
    
    rejection_reason = request.form.get('reason', 'No reason provided')
    
    from datetime import datetime
    user.approval_status = 'rejected'
    user.approval_date = datetime.utcnow()
    user.approved_by_id = current_user.id
    user.is_active = False
    
    db.session.commit()
    
    # Notify the user
    from app.models.notification import Notification
    notification = Notification(
        user_id=user.id,
        title="❌ Account Rejected",
        message=f"Your account registration has been rejected. Reason: {rejection_reason}",
        type="user"
    )
    db.session.add(notification)
    db.session.commit()
    
    log_audit_action("User Rejected", current_user.id, f"User: {user.username}, Reason: {rejection_reason}")
    flash(f'✅ User {user.username} has been REJECTED. They cannot login.', 'warning')
    return redirect(url_for('admin.pending_approvals'))
