from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.evidence import Evidence
from app.models.custody import CustodyRecord
from app.models.user import User
from app.models.notification import Notification
from app.custody.forms import TransferCustodyForm
from app.auth.decorators import role_required
from app.utils.audit_logger import log_audit_action

custody_bp = Blueprint('custody', __name__, url_prefix='/custody')

@custody_bp.route('/history/<int:evidence_id>')
@login_required
def history(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    records = CustodyRecord.query.filter_by(evidence_id=evidence_id).order_by(CustodyRecord.timestamp.asc()).all()
    return render_template('custody/history.html', evidence=evidence, records=records)

@custody_bp.route('/transfer/<int:evidence_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator')
def transfer(evidence_id):
    evidence = Evidence.query.get_or_404(evidence_id)
    
    # If the investigator is transferring custody, verify they are allowed (e.g. they own it or link to case)
    if current_user.has_role('investigator') and evidence.current_case:
        if evidence.current_case.investigator_id != current_user.id:
            abort(403)
            
    form = TransferCustodyForm()
    if form.validate_on_submit():
        to_user = User.query.get(form.to_user_id.data)
        if not to_user:
            flash('❌ Recipient user not found.', 'danger')
            return redirect(url_for('custody.transfer', evidence_id=evidence_id))
            
        record = CustodyRecord(
            evidence_id=evidence.id,
            from_user_id=current_user.id,
            to_user_id=to_user.id,
            action='Transferred Custody',
            remarks=form.remarks.data
        )
        
        # Add Notification to the recipient
        notification = Notification(
            user_id=to_user.id,
            title="📥 Custody Transferred to You",
            message=f"Forensic custody of file '{evidence.file_name}' has been transferred to you by {current_user.fullname}. Remarks: {form.remarks.data}",
            type="custody"
        )
        
        try:
            db.session.add(record)
            db.session.add(notification)
            db.session.commit()
            
            log_audit_action("Custody Transferred", current_user.id, f"Evidence ID: {evidence.id}, Transferred to: {to_user.username}")
            flash(f"✅ Custody of evidence transferred successfully to {to_user.fullname}.", "success")
            return redirect(url_for('evidence.detail', id=evidence.id))
        except Exception as e:
            db.session.rollback()
            flash('❌ Error executing custody transfer.', 'danger')
            
    return render_template('custody/transfer.html', form=form, evidence=evidence)
