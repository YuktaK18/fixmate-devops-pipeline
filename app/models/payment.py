import uuid
from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class Payment(db.Model):
    """Simulated payment record tracking transaction reference, GST, commission, and payout."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    transaction_reference = db.Column(db.String(64), unique=True, nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    # Financial breakdown
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('18.00'), nullable=False)
    gst_amount = db.Column(db.Numeric(10, 2), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # Total collected (subtotal + GST)
    
    # Commission and Provider Earnings split
    commission_rate = db.Column(db.Numeric(5, 2), default=Decimal('10.00'), nullable=False)
    commission_amount = db.Column(db.Numeric(10, 2), nullable=False)
    provider_payout_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payout Status (SRS 4.6.3: hold provider's payout until confirmed or 24h)
    payout_status = db.Column(
        db.Enum('HELD', 'RELEASED', name='payout_status_enum'),
        default='HELD',
        nullable=False,
        index=True
    )
    
    # Payment Method & State
    payment_method = db.Column(
        db.Enum('UPI', 'CARD', 'NET_BANKING', 'WALLET', name='payment_method_enum'),
        nullable=False
    )
    status = db.Column(
        db.Enum('PENDING', 'PAID', 'FAILED', 'REFUNDED', name='payment_status_enum'),
        default='PAID',
        nullable=False,
        index=True
    )
    
    # Dispute Refund fields (SRS 4.6.3 & Admin Refund)
    refund_amount = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), nullable=False)
    refund_reason = db.Column(db.Text, nullable=True)
    refunded_at = db.Column(db.DateTime, nullable=True)

    paid_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    invoice = db.relationship('Invoice', backref='payment', uselist=False, cascade='all, delete-orphan')

    @staticmethod
    def generate_transaction_ref() -> str:
        """Generates realistic transaction reference: TXN-YYYYMMDD-HEX."""
        date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
        hex_token = uuid.uuid4().hex[:8].upper()
        return f"TXN-{date_str}-{hex_token}"

    def __repr__(self):
        return f"<Payment ref={self.transaction_reference} amt={self.amount} status='{self.status}'>"


class Invoice(db.Model):
    """Digital tax invoice with GST breakdown and verifiable reference."""
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    payment_id = db.Column(db.Integer, db.ForeignKey('payments.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    customer_name = db.Column(db.String(100), nullable=False)
    provider_name = db.Column(db.String(100), nullable=False)
    service_title = db.Column(db.String(100), nullable=False)
    
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    gst_rate = db.Column(db.Numeric(5, 2), default=Decimal('18.00'), nullable=False)
    gst_amount = db.Column(db.Numeric(10, 2), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    pdf_filename = db.Column(db.String(255), nullable=True)
    generated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    booking = db.relationship('Booking', backref=db.backref('invoice', uselist=False))

    @staticmethod
    def generate_invoice_number() -> str:
        """Generates invoice number: INV-YYYY-XXXXXX."""
        year_str = datetime.now(timezone.utc).strftime('%Y')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"INV-{year_str}-{suffix}"

    def __repr__(self):
        return f"<Invoice {self.invoice_number} Total={self.total_amount}>"
