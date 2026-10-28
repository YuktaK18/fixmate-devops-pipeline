import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.extensions import db


class Booking(db.Model):
    """Core booking record managing scheduling, execution lifecycle, and transitions."""
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    booking_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id', ondelete='RESTRICT'), nullable=False, index=True)

    # Date and Time slot
    scheduled_date = db.Column(db.Date, nullable=False, index=True)
    scheduled_time_slot = db.Column(db.String(30), nullable=False, index=True)  # e.g., '10:00 - 12:00'
    
    service_address = db.Column(db.Text, nullable=False)
    pincode = db.Column(db.String(10), nullable=False, index=True)
    special_instructions = db.Column(db.Text, nullable=True)

    # Booking Status Lifecycle (SRS 4.4 & Core Booking Workflow)
    status = db.Column(
        db.Enum(
            'PENDING',
            'ACCEPTED',
            'REJECTED',
            'IN_PROGRESS',
            'COMPLETED',
            'CANCELLED',
            'RESCHEDULED',
            name='booking_status_enum'
        ),
        default='PENDING',
        nullable=False,
        index=True
    )

    # Pricing
    quoted_amount = db.Column(db.Numeric(10, 2), nullable=False)
    final_amount = db.Column(db.Numeric(10, 2), nullable=True)

    # Provider Response Timer (SRS 4.4.3: 5 minutes to accept/decline)
    response_deadline = db.Column(db.DateTime, nullable=True)

    # Cancellation fields
    cancellation_reason = db.Column(db.Text, nullable=True)
    cancellation_fee = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    cancelled_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Rescheduling fields (SRS 4.4.3: mutual agreement required)
    reschedule_proposed_date = db.Column(db.Date, nullable=True)
    reschedule_proposed_time_slot = db.Column(db.String(30), nullable=True)
    reschedule_requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    customer = db.relationship('User', foreign_keys=[customer_id], backref=db.backref('customer_bookings', lazy='dynamic'))
    provider = db.relationship('User', foreign_keys=[provider_id], backref=db.backref('provider_jobs', lazy='dynamic'))
    status_history = db.relationship('BookingStatusHistory', backref='booking', cascade='all, delete-orphan', order_by='BookingStatusHistory.created_at.desc()')
    payment = db.relationship('Payment', backref='booking', uselist=False, cascade='all, delete-orphan')
    review = db.relationship('Review', backref='booking', uselist=False, cascade='all, delete-orphan')
    complaints = db.relationship('Complaint', backref='booking', cascade='all, delete-orphan')

    @staticmethod
    def generate_booking_code() -> str:
        """Generates a memorable unique reference: FIX-YYYYMMDD-XXXX."""
        now_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"FIX-{now_str}-{random_suffix}"

    @property
    def is_pending(self) -> bool:
        return self.status == 'PENDING'

    @property
    def is_active(self) -> bool:
        return self.status in ('ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED')

    @property
    def is_completed(self) -> bool:
        return self.status == 'COMPLETED'

    @property
    def is_cancelled(self) -> bool:
        return self.status in ('CANCELLED', 'REJECTED')

    @property
    def has_expired_window(self) -> bool:
        """Checks if the 5-minute response window expired while pending."""
        if self.status == 'PENDING' and self.response_deadline:
            now = datetime.now(timezone.utc)
            deadline = self.response_deadline.replace(tzinfo=timezone.utc) if self.response_deadline.tzinfo is None else self.response_deadline
            return now > deadline
        return False

    def __repr__(self):
        return f"<Booking {self.booking_code} [{self.status}] Cust:{self.customer_id} Prov:{self.provider_id}>"


class BookingStatusHistory(db.Model):
    """Audit trail tracking every single status change in a booking's life cycle."""
    __tablename__ = 'booking_status_history'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False, index=True)
    
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=False)
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<BookingStatusHistory booking={self.booking_id} {self.previous_status}->{self.new_status}>"
