from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db
from app.models.user import User, Role
from app.auth.forms import LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm
from app.utils.audit_logger import log_audit_action
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = RegisterForm()
    if form.validate_on_submit():
        # Create user
        user = User(
            username=form.username.data,
            email=form.email.data,
            fullname=form.fullname.data,
            created_at=datetime.utcnow()
        )
        user.set_password(form.password.data)
        
        # Resolve user role
        selected_role = form.role.data
        role = Role.query.filter_by(name=selected_role).first()
        if not role:
            # Create role if missing on startup
            role = Role(name=selected_role, description=f"Default {selected_role} role")
            db.session.add(role)
            db.session.commit()
            
        user.roles.append(role)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Send verification notification or write log
            log_audit_action("User Registration", user.id, f"Username: {user.username}, Role: {selected_role}, PENDING APPROVAL")
            
            # Notify admins of pending approval
            from app.models.notification import Notification
            system_admins = User.query.filter(User.roles.any(name='admin')).all()
            for admin in system_admins:
                new_notif = Notification(
                    user_id=admin.id,
                    title="⚠️ New Account Pending Approval",
                    message=f"User {user.username} ({selected_role}) requires your approval to login.",
                    type="user"
                )
                db.session.add(new_notif)
            db.session.commit()
                
            flash('✅ Registration successful! Your account is pending admin approval. You will be notified once approved.', 'info')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('❌ Error saving account. Please try again.', 'danger')
            current_app.logger.error(f"Registration Error: {str(e)}")
            
    return render_template('auth/register.html', form=form)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user:
            # Check if account is approved
            if not user.is_approved or user.approval_status != 'approved':
                flash('🚫 Your account is not approved yet. Please wait for admin approval.', 'danger')
                log_audit_action("Login Denied - Not Approved", user.id, f"Approval Status: {user.approval_status}")
                return render_template('auth/login.html', form=form)
            
            # Check lockout
            if user.locked_until and user.locked_until > datetime.utcnow():
                time_left = user.locked_until - datetime.utcnow()
                minutes_left = int(time_left.total_seconds() / 60) + 1
                flash(f'🔒 Account temporarily locked. Try again in {minutes_left} minutes.', 'danger')
                return render_template('auth/login.html', form=form)
                
            if user.check_password(form.password.data):
                # Reset counters
                user.failed_attempts = 0
                user.locked_until = None
                db.session.commit()
                
                login_user(user, remember=form.remember_me.data)
                log_audit_action("Successful Login", user.id)
                
                flash(f'Welcome back, {user.fullname}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
            else:
                user.failed_attempts += 1
                if user.failed_attempts >= 5:
                    user.locked_until = datetime.utcnow() + timedelta(minutes=10)
                    log_audit_action("Account Locked Out", user.id, "5 failed login attempts. Locked for 10 minutes.")
                    flash('🔒 Account locked for 10 minutes due to 5 consecutive failed login attempts.', 'danger')
                else:
                    flash('❌ Invalid username or password.', 'danger')
                db.session.commit()
        else:
            flash('❌ Invalid username or password.', 'danger')
            
    return render_template('auth/login.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    log_audit_action("Successful Logout", current_user.id)
    logout_user()
    flash('👋 You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
        
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Demo simulation or log creation
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            log_audit_action("Password Reset Requested", user.id)
            # Simulated Reset URL: In production send via Flask-Mail
            reset_token = "demo-reset-token-valid-for-this-session"
            flash(f'📧 Password reset link sent to {form.email.data}. (Simulated for demo)', 'info')
        else:
            flash('❌ If the email exists, a reset link will be sent.', 'info')
        return redirect(url_for('auth.login'))
        
    return render_template('auth/forgot_password.html', form=form)
