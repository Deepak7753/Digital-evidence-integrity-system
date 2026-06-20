import os
from flask import Flask, render_template, session
from app.config import Config
from app.extensions import db, migrate, login_manager, bcrypt, csrf, mail, limiter
from app.models import init_models
from app.models.user import User, Role

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize directories
    config_class.init_app(app)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    limiter.init_app(app)

    # Register models with metadata
    init_models()

    # User loader configuration
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from app.auth.routes import auth_bp
    from app.dashboard.routes import dashboard_bp
    from app.cases.routes import cases_bp
    from app.evidence.routes import evidence_bp
    from app.custody.routes import custody_bp
    from app.reports.routes import reports_bp
    from app.admin.routes import admin_bp
    from app.notifications.routes import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(cases_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(custody_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(notifications_bp)

    # Global variables injected into templates
    @app.context_processor
    def inject_notifications():
        from app.models.notification import Notification
        from flask_login import current_user
        if current_user and current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            recent_notifs = Notification.query.filter_by(user_id=current_user.id, is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
            return dict(unread_notifications_count=unread_count, unread_notifications=recent_notifs)
        return dict(unread_notifications_count=0, unread_notifications=[])

    # Error Handlers
    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template('errors/500.html'), 500

    # Auto Seed DB and System Users on startup (Convenient for first run)
    with app.app_context():
        try:
            # Create tables if they do not exist
            db.create_all()
            
            # 1. Seed Roles
            roles_to_seed = ['admin', 'investigator', 'auditor']
            seeded_roles = {}
            for role_name in roles_to_seed:
                role = Role.query.filter_by(name=role_name).first()
                if not role:
                    role = Role(name=role_name, description=f"System forensic {role_name} access role")
                    db.session.add(role)
                    db.session.commit()
                seeded_roles[role_name] = role

            # 2. Seed Default Admin User
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@deis-vault.local',
                    fullname='System Forensic Administrator',
                    email_verified=True,
                    is_approved=True,
                    approval_status='approved'
                )
                admin.set_password('admin123')
                admin.roles.append(seeded_roles['admin'])
                db.session.add(admin)
                
            # 3. Seed Default Investigator User
            if not User.query.filter_by(username='investigator').first():
                inv = User(
                    username='investigator',
                    email='investigator@deis-vault.local',
                    fullname='Special Agent Investigator',
                    email_verified=True,
                    is_approved=True,
                    approval_status='approved'
                )
                inv.set_password('investigator123')
                inv.roles.append(seeded_roles['investigator'])
                db.session.add(inv)

            # 4. Seed Default Auditor User
            if not User.query.filter_by(username='auditor').first():
                aud = User(
                    username='auditor',
                    email='auditor@deis-vault.local',
                    fullname='Senior Forensic Auditor',
                    email_verified=True,
                    is_approved=True,
                    approval_status='approved'
                )
                aud.set_password('auditor123')
                aud.roles.append(seeded_roles['auditor'])
                db.session.add(aud)

            db.session.commit()
            print("[DEIS Engine] [SUCCESS] Database initialized with approval system and default accounts seeded successfully.")
        except Exception as e:
            print(f"[DEIS Engine] [ERROR] Startup Database Seed Failure: {str(e)}")

    return app
