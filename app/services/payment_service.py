from decimal import Decimal
from datetime import datetime, timezone
from app.extensions import db
from app.models.payment import Payment, Invoice
from app.models.booking import Booking
from app.models.settings import SystemSetting
from app.models.notification import Notification
from app.models.audit import AdminAuditLog


class PaymentService:
    """Simulated payment provider interface and financial settlement coordinator."""

    @staticmethod
    def calculate_breakdown(subtotal: Decimal) -> dict:
        """
        Calculates 18% GST, 10% Platform Commission, and Provider Payout breakdown.
        """
        gst_pct = Decimal(SystemSetting.get_value('gst_percentage', '18.0'))
        comm_pct = Decimal(SystemSetting.get_value('commission_percentage', '10.0'))

        gst_amount = (subtotal * (gst_pct / Decimal('100.0'))).quantize(Decimal('0.01'))
        total_amount = subtotal + gst_amount
        commission_amount = (subtotal * (comm_pct / Decimal('100.0'))).quantize(Decimal('0.01'))
        provider_payout_amount = subtotal - commission_amount

        return {
            'subtotal': subtotal,
            'gst_rate': gst_pct,
            'gst_amount': gst_amount,
            'total_amount': total_amount,
            'commission_rate': comm_pct,
            'commission_amount': commission_amount,
            'provider_payout_amount': provider_payout_amount,
        }

    @classmethod
    def process_simulated_payment(cls, booking: Booking, payment_method: str) -> Payment:
        """
        Executes a simulated payment in Demo Mode.
        Records GST, Commission split, and generates a digital tax invoice.
        """
        if booking.status != 'COMPLETED':
            raise ValueError("Payment can only be processed once the job is marked COMPLETED by the provider.")
        
        if booking.payment:
            raise ValueError("Payment has already been recorded for this booking.")

        # Determine billing amount
        subtotal = booking.final_amount if booking.final_amount else booking.quoted_amount
        breakdown = cls.calculate_breakdown(subtotal)

        payment = Payment(
            transaction_reference=Payment.generate_transaction_ref(),
            booking_id=booking.id,
            subtotal=breakdown['subtotal'],
            gst_rate=breakdown['gst_rate'],
            gst_amount=breakdown['gst_amount'],
            amount=breakdown['total_amount'],
            commission_rate=breakdown['commission_rate'],
            commission_amount=breakdown['commission_amount'],
            provider_payout_amount=breakdown['provider_payout_amount'],
            payout_status='HELD',  # Held until customer confirms or 24h (SRS 4.6.3)
            payment_method=payment_method,
            status='PAID'
        )
        db.session.add(payment)
        db.session.flush()

        # Generate digital invoice
        invoice = Invoice(
            invoice_number=Invoice.generate_invoice_number(),
            booking_id=booking.id,
            payment_id=payment.id,
            customer_name=booking.customer.name,
            provider_name=booking.provider.name,
            service_title=booking.category.name,
            subtotal=breakdown['subtotal'],
            gst_rate=breakdown['gst_rate'],
            gst_amount=breakdown['gst_amount'],
            total_amount=breakdown['total_amount']
        )
        db.session.add(invoice)

        # Send notifications
        cust_notif = Notification(
            user_id=booking.customer_id,
            title="Payment Successful & Invoice Generated",
            message=f"Payment of ₹{payment.amount} via {payment_method} recorded for booking #{booking.booking_code}. Thank you for using FixMate!",
            notification_type='PAYMENT',
            link_url=f"/customer/invoices/{invoice.id}"
        )
        db.session.add(cust_notif)

        prov_notif = Notification(
            user_id=booking.provider_id,
            title="Payment Received (Held in Escrow)",
            message=f"Customer paid ₹{payment.amount} for booking #{booking.booking_code}. Your net earnings of ₹{payment.provider_payout_amount} (after 10% platform commission) are held and will be released within 24 hours.",
            notification_type='PAYMENT',
            link_url=f"/provider/earnings"
        )
        db.session.add(prov_notif)

        db.session.commit()
        return payment

    @classmethod
    def release_payout(cls, payment: Payment, admin_user) -> Payment:
        """Releases held payout to provider account."""
        payment.payout_status = 'RELEASED'
        
        # Log admin audit
        audit = AdminAuditLog(
            admin_id=admin_user.id if admin_user else None,
            admin_email=admin_user.email if admin_user else 'system@fixmate.local',
            action='RELEASE_PAYOUT',
            target_entity='Payment',
            target_id=str(payment.id),
            details=f"Released provider payout of ₹{payment.provider_payout_amount} for booking #{payment.booking.booking_code}"
        )
        db.session.add(audit)
        db.session.commit()
        return payment

    @classmethod
    def issue_refund(cls, payment: Payment, refund_amount: Decimal, reason: str, admin_user) -> Payment:
        """Admin dispute resolution: issues a full or partial refund (SRS 4.6.3)."""
        if refund_amount <= 0:
            raise ValueError("Refund amount must be greater than zero.")
        if refund_amount > payment.amount:
            raise ValueError(f"Refund amount (₹{refund_amount}) cannot exceed total payment (₹{payment.amount}).")

        payment.refund_amount = refund_amount
        payment.refund_reason = reason
        payment.refunded_at = datetime.now(timezone.utc)
        if refund_amount == payment.amount:
            payment.status = 'REFUNDED'
            payment.provider_payout_amount = Decimal('0.00')

        # Log admin action
        audit = AdminAuditLog(
            admin_id=admin_user.id,
            admin_email=admin_user.email,
            action='ISSUE_REFUND',
            target_entity='Payment',
            target_id=str(payment.id),
            details=f"Issued refund of ₹{refund_amount} for transaction {payment.transaction_reference}. Reason: {reason}"
        )
        db.session.add(audit)

        # Notify customer
        notif = Notification(
            user_id=payment.booking.customer_id,
            title="Refund Processed",
            message=f"A refund of ₹{refund_amount} has been processed for booking #{payment.booking.booking_code}. Reason: {reason}",
            notification_type='PAYMENT',
            link_url=f"/customer/bookings/{payment.booking_id}"
        )
        db.session.add(notif)
        db.session.commit()
        return payment
