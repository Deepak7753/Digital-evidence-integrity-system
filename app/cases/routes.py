from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models.case import Case
from app.models.user import User
from app.cases.forms import CaseForm
from app.auth.decorators import role_required
from app.utils.audit_logger import log_audit_action

cases_bp = Blueprint('cases', __name__, url_prefix='/cases')

# Closure report route
@cases_bp.route('/closure_report')
@login_required
def closure_report():
    """Render the case closure report page"""
    return render_template('cases/closure_report.html')

@cases_bp.route('/')
@login_required
def list_cases():
    # Show all cases for admin/auditor, show assigned cases for investigator
    if current_user.has_role('admin') or current_user.has_role('auditor'):
        all_cases = Case.query.order_by(Case.created_at.desc()).all()
    else:
        all_cases = Case.query.filter_by(investigator_id=current_user.id).order_by(Case.created_at.desc()).all()
        
    return render_template('cases/list.html', cases=all_cases)

@cases_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator')
def create():
    form = CaseForm()
    
    # If request is GET and user is investigator, preselect them
    if request.method == 'GET' and current_user.has_role('investigator'):
        form.investigator_id.data = current_user.id

    if form.validate_on_submit():
        # Check duplicate case number
        existing_case = Case.query.filter_by(case_number=form.case_number.data).first()
        if existing_case:
            flash(f"❌ Case ID '{form.case_number.data}' already exists. Please choose a unique identifier.", "danger")
            return render_template('cases/create.html', form=form)

        new_case = Case(
            case_number=form.case_number.data.upper(),
            name=form.name.data,
            description=form.description.data,
            status=form.status.data,
            investigator_id=form.investigator_id.data
        )
        try:
            db.session.add(new_case)
            db.session.commit()
            log_audit_action("Case Created", current_user.id, f"Case ID: {new_case.case_number}")
            flash('✅ Case successfully initialized.', 'success')
            return redirect(url_for('cases.list_cases'))
        except Exception as e:
            db.session.rollback()
            flash('❌ Error creating case. Please check values.', 'danger')
            
    return render_template('cases/create.html', form=form)

@cases_bp.route('/<int:id>')
@login_required
def detail(id):
    case = Case.query.get_or_404(id)
    
    # Check permission for investigator
    if not (current_user.has_role('admin') or current_user.has_role('auditor')) and case.investigator_id != current_user.id:
        abort(403)
        
    return render_template('cases/detail.html', case=case)

@cases_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'investigator')
def edit(id):
    case = Case.query.get_or_404(id)
    
    # Check permission for investigator
    if not current_user.has_role('admin') and case.investigator_id != current_user.id:
        abort(403)
        
    form = CaseForm(obj=case)
    if form.validate_on_submit():
        case.case_number = form.case_number.data.upper()
        case.name = form.name.data
        case.description = form.description.data
        case.status = form.status.data
        case.investigator_id = form.investigator_id.data
        
        try:
            db.session.commit()
            log_audit_action("Case Updated", current_user.id, f"Case ID: {case.case_number}")
            flash('✅ Case metadata updated successfully.', 'success')
            return redirect(url_for('cases.detail', id=case.id))
        except Exception as e:
            db.session.rollback()
            flash('❌ Error updating case.', 'danger')
            
    return render_template('cases/edit.html', form=form, case=case)

@cases_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete(id):
    case = Case.query.get_or_404(id)
    case_no = case.case_number
    try:
        db.session.delete(case)
        db.session.commit()
        log_audit_action("Case Deleted", current_user.id, f"Case ID: {case_no}")
        flash('🗑️ Case and all references deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('❌ Error deleting case.', 'danger')
        
    return redirect(url_for('cases.list_cases'))


# Change case status (Pending / Complete)
@cases_bp.route('/<int:id>/status', methods=['POST'])
@login_required
@role_required('admin', 'investigator')
def change_status(id):
    case = Case.query.get_or_404(id)
    if not (current_user.has_role('admin') or case.investigator_id == current_user.id):
        abort(403)
    new_status = request.form.get('status')
    allowed = ['Open', 'Active', 'Pending', 'Complete', 'Closed', 'Archived']
    if new_status not in allowed:
        flash('Invalid status selected.', 'danger')
        return redirect(url_for('cases.detail', id=id))
    case.status = new_status
    db.session.commit()
    flash('Case status updated successfully.', 'success')
    return redirect(request.referrer or url_for('cases.detail', id=id))
