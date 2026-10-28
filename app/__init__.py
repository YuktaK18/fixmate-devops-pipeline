import os
from datetime import datetime, timezone
import click
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf, limiter
from app.models import (
    User, ProviderProfile, ProviderDocument, ServiceCategory,
    ProviderService, Booking, BookingStatusHistory, Payment,
    Invoice, Review, Complaint, Notification, AdminAuditLog, SystemSetting
)


def create_app(config_name: str = None) -> Flask:
    """Application factory for FixMate Home Service Management System."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__)
    config_obj = config_by_name.get(config_name, config_by_name['default'])
    app.config.from_object(config_obj)

    # Ensure required runtime folders exist
    os.makedirs(app.config.get('DOCUMENTS_FOLDER', 'var/uploads/documents'), exist_ok=True)
    os.makedirs(app.config.get('COMPLAINTS_FOLDER', 'var/uploads/complaints'), exist_ok=True)
    os.makedirs(app.config.get('INVOICES_FOLDER', 'var/uploads/invoices'), exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    # Register modular blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.customer import customer_bp
    from app.blueprints.provider import provider_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.payments import payments_bp
    from app.blueprints.api import api_bp
    from app.blueprints.errors import errors_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(provider_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(errors_bp)

    # Global context processors available to all Jinja templates
    @app.context_processor
    def inject_global_data():
        from flask_login import current_user
        from app.services.notification_service import NotificationService
        
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = NotificationService.get_unread_count(current_user.id)
            
        return {
            'now': datetime.now(timezone.utc),
            'unread_notifications_count': unread_count,
            'demo_mode': app.config.get('DEMO_MODE', True),
            'app_name': 'FixMate',
        }

    # Custom CLI Command: flask create-admin
    @app.cli.command('create-admin')
    @click.option('--name', prompt='Admin Full Name', default=lambda: os.getenv('FIRST_ADMIN_NAME', 'FixMate Admin'))
    @click.option('--email', prompt='Admin Email Address', default=lambda: os.getenv('FIRST_ADMIN_EMAIL', 'admin@fixmate.local'))
    @click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, default=lambda: os.getenv('FIRST_ADMIN_PASSWORD', 'Admin@FixMate2026!'))
    @click.option('--phone', prompt='Admin Phone Number', default=lambda: os.getenv('FIRST_ADMIN_PHONE', '9876543210'))
    def create_admin_command(name, email, password, phone):
        """Creates the initial Administrator account without hardcoding credentials."""
        email_clean = email.lower().strip()
        existing = User.query.filter_by(email=email_clean).first()
        if existing:
            click.echo(click.style(f"Error: An account with email '{email_clean}' already exists.", fg='red'))
            return

        admin = User(
            name=name.strip(),
            email=email_clean,
            phone=phone.strip(),
            role='admin',
            terms_accepted=True,
            terms_accepted_at=datetime.now(timezone.utc)
        )
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(click.style(f"Success: Administrator '{admin.name}' ({admin.email}) created successfully!", fg='green'))

    # Custom CLI Command: flask seed-db
    @app.cli.command('seed-db')
    def seed_db_command():
        """Seeds database with realistic initial categories, providers, and test users."""
        from scripts.seed_data import seed_all
        seed_all()
        click.echo(click.style("Database seeded successfully!", fg='green'))

    return app
