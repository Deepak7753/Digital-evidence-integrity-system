from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models.user import User
from app.models.evidence import Evidence
from app.models.case import Case
from app.models.custody import CustodyRecord
from app.models.audit import AuditLog
from app.extensions import db
from sqlalchemy import func
from datetime import datetime, timedelta

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    # Gather counts for dashboard cards
    total_users = User.query.count()
    total_evidence = Evidence.query.count()
    total_cases = Case.query.count()
    active_cases = Case.query.filter(Case.status.in_(['Open', 'Active'])).count()
    complete_cases = Case.query.filter_by(status='Complete').count()
    pending_cases = Case.query.filter_by(status='Pending').count()
    
    tampered_files = Evidence.query.filter_by(status='Tampered').count()
    verified_files = Evidence.query.filter_by(status='Verified').count()
    pending_verification = Evidence.query.filter_by(status='Warning').count()
    
    # Recent items to show in dashboards
    recent_evidence = Evidence.query.order_by(Evidence.upload_date.desc()).limit(5).all()
    recent_custody = CustodyRecord.query.order_by(CustodyRecord.timestamp.desc()).limit(5).all()
    recent_audit = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    # Alerts/tampering events
    tamper_alerts = Evidence.query.filter(Evidence.status.in_(['Tampered', 'Warning'])).all()
    
    return render_template(
        'dashboard/index.html',
        total_users=total_users,
        total_evidence=total_evidence,
        total_cases=total_cases,
        active_cases=active_cases,
        complete_cases=complete_cases,
        pending_cases=pending_cases,
        tampered_files=tampered_files,
        verified_files=verified_files,
        pending_verification=pending_verification,
        recent_evidence=recent_evidence,
        recent_custody=recent_custody,
        recent_audit=recent_audit,
        tamper_alerts=tamper_alerts
    )

@dashboard_bp.route('/dashboard/chart-data')
@login_required
def chart_data():
    """
    Returns JSON data for Chart.js.
    """
    # 1. Evidence Categories
    categories_query = db.session.query(
        Evidence.category, func.count(Evidence.id)
    ).group_by(Evidence.category).all()
    categories_data = {cat: count for cat, count in categories_query}
    
    # 2. Upload Trends (last 7 days)
    today = datetime.utcnow().date()
    trends_labels = []
    trends_values = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        trends_labels.append(day.strftime('%b %d'))
        
        # Count uploads on this day
        count = Evidence.query.filter(
            func.date(Evidence.upload_date) == day
        ).count()
        trends_values.append(count)
        
    # 3. Custody Transfers Action breakdown
    custody_query = db.session.query(
        CustodyRecord.action, func.count(CustodyRecord.id)
    ).group_by(CustodyRecord.action).all()
    custody_data = {action: count for action, count in custody_query}
    
    # 4. User Activity Trends (Audit logs in last 7 days grouped by user)
    user_activity_query = db.session.query(
        User.username, func.count(AuditLog.id)
    ).join(AuditLog, User.id == AuditLog.user_id).group_by(User.username).all()
    user_activity = {user: count for user, count in user_activity_query}

    return jsonify({
        'categories': {
            'labels': list(categories_data.keys()),
            'values': list(categories_data.values())
        },
        'trends': {
            'labels': trends_labels,
            'values': trends_values
        },
        'custody': {
            'labels': list(custody_data.keys()),
            'values': list(custody_data.values())
        },
        'activity': {
            'labels': list(user_activity.keys()),
            'values': list(user_activity.values())
        }
    })
