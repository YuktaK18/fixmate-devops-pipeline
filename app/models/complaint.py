import uuid
from datetime import datetime, timezone
from app.extensions import db


class Complaint(db.Model):
    """Customer dispute ticket submitted within 7 days of job completion."""
    __tablename__ = 'complaints'

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    photo_filename = db.Column(db.String(255), nullable=True)

    # Lifecycle: OPEN -> IN_REVIEW -> RESOLVED / REJECTED (SRS 4.7.3)
    status = db.Column(
        db.Enum('OPEN', 'IN_REVIEW', 'RESOLVED', 'REJECTED', name='complaint_status_enum'),
        default='OPEN',
        nullable=False,
        index=True
    )
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @staticmethod
    def generate_ticket_number() -> str:
        """Generates ticket code: CMP-YYYYMMDD-XXXX."""
        date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"CMP-{date_str}-{suffix}"

    def __repr__(self):
        return f"<Complaint ticket={self.ticket_number} status='{self.status}'>"
