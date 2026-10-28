import secrets
from datetime import datetime, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """Core user model for Customers, Service Providers, and Administrators."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('customer', 'provider', 'admin', name='user_roles'), nullable=False, default='customer', index=True)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_suspended = db.Column(db.Boolean, default=False, nullable=False)
    
    # Account lockout policy (SRS 4.1.3: 5 failed attempts locks for 15 minutes)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Terms & Privacy Policy Acceptance
    terms_accepted = db.Column(db.Boolean, default=True, nullable=False)
    terms_accepted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Password Reset Token
    reset_token = db.Column(db.String(100), nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    provider_profile = db.relationship('ProviderProfile', foreign_keys='ProviderProfile.user_id', backref='user', uselist=False, cascade='all, delete-orphan')
    reviews_given = db.relationship('Review', foreign_keys='Review.customer_id', backref='customer', lazy='dynamic')
    complaints = db.relationship('Complaint', foreign_keys='Complaint.customer_id', backref='customer', lazy='dynamic')
    notifications = db.relationship('Notification', foreign_keys='Notification.user_id', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AdminAuditLog', foreign_keys='AdminAuditLog.admin_id', backref='admin', lazy='dynamic')

    def set_password(self, password: str):
        """Hashes and sets user password using Werkzeug security."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verifies a plain text password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_account_locked(self) -> bool:
        """Checks if the account is currently locked due to failed login attempts."""
        if self.locked_until:
            now = datetime.now(timezone.utc)
            locked_until_utc = self.locked_until.replace(tzinfo=timezone.utc) if self.locked_until.tzinfo is None else self.locked_until
            if now < locked_until_utc:
                return True
            # Lockout expired: reset attempts
            self.failed_login_attempts = 0
            self.locked_until = None
            db.session.commit()
        return False

    def record_failed_login(self):
        """Increments failed logins and locks account for 15 minutes upon reaching 5 strikes."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.session.commit()

    def reset_failed_logins(self):
        """Resets failed login counter on successful authentication."""
        if self.failed_login_attempts > 0 or self.locked_until is not None:
            self.failed_login_attempts = 0
            self.locked_until = None
            db.session.commit()

    def generate_reset_token(self) -> str:
        """Generates a secure URL-safe password reset token valid for 30 minutes."""
        token = secrets.token_urlsafe(32)
        self.reset_token = token
        self.reset_token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
        db.session.commit()
        return token

    def verify_reset_token(self, token: str) -> bool:
        """Validates a password reset token and ensures it has not expired."""
        if not self.reset_token or self.reset_token != token or not self.reset_token_expiry:
            return False
        now = datetime.now(timezone.utc)
        expiry_utc = self.reset_token_expiry.replace(tzinfo=timezone.utc) if self.reset_token_expiry.tzinfo is None else self.reset_token_expiry
        return now <= expiry_utc

    def clear_reset_token(self):
        """Clears password reset token after successful password update."""
        self.reset_token = None
        self.reset_token_expiry = None
        db.session.commit()

    @property
    def is_customer(self) -> bool:
        return self.role == 'customer'

    @property
    def is_provider(self) -> bool:
        return self.role == 'provider'

    @property
    def is_admin(self) -> bool:
        return self.role == 'admin'

    def __repr__(self):
        return f"<User id={self.id} email='{self.email}' role='{self.role}'>"


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login user loader callback."""
    return db.session.get(User, int(user_id))
