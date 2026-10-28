from flask import request
from flask_login import current_user
from app.extensions import db
from app.models.audit import AdminAuditLog


class AuditService:
    """Records administrator operations and audit logs."""

    @staticmethod
    def log(action: str, target_entity: str = None, target_id: str = None, details: str = None):
        """Records an admin activity in the immutable audit log."""
        admin_id = current_user.id if current_user and current_user.is_authenticated else None
        admin_email = current_user.email if current_user and current_user.is_authenticated else 'system'
        
        try:
            ip = request.remote_addr
        except RuntimeError:
            ip = '127.0.0.1'

        entry = AdminAuditLog(
            admin_id=admin_id,
            admin_email=admin_email,
            action=action,
            target_entity=target_entity,
            target_id=str(target_id) if target_id is not None else None,
            details=details,
            ip_address=ip
        )
        db.session.add(entry)
        db.session.commit()
