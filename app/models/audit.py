from datetime import datetime, timezone
from app.extensions import db


class AdminAuditLog(db.Model):
    """Immutable accountability log recording all administrator activities."""
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    admin_email = db.Column(db.String(120), nullable=True)
    
    action = db.Column(db.String(100), nullable=False, index=True)
    target_entity = db.Column(db.String(50), nullable=True)
    target_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def __repr__(self):
        return f"<AdminAuditLog id={self.id} action='{self.action}' admin='{self.admin_email}'>"
