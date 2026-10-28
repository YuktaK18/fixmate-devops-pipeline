from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    """In-app alerts and notifications with promotional preferences support."""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.Enum('BOOKING', 'PAYMENT', 'ACCOUNT', 'PROMO', 'DISPUTE', name='notification_type_enum'),
        default='BOOKING',
        nullable=False,
        index=True
    )
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_promotional = db.Column(db.Boolean, default=False, nullable=False, index=True)
    link_url = db.Column(db.String(255), nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def mark_as_read(self):
        """Marks notification as read."""
        self.is_read = True
        db.session.commit()

    def __repr__(self):
        return f"<Notification id={self.id} user={self.user_id} read={self.is_read}>"
