import pytest
from decimal import Decimal
from datetime import date, timedelta
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.services.invoice_service import InvoiceService


@pytest.fixture
def completed_booking(customer_user, approved_provider, sample_category):
    """Fixture providing a completed booking ready for payment."""
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='11:00 - 01:00 PM',
        address='Test Address',
        pincode='400071'
    )
    BookingService.transition_status(booking, 'ACCEPTED', approved_provider)
    BookingService.transition_status(booking, 'IN_PROGRESS', approved_provider)
    BookingService.transition_status(booking, 'COMPLETED', approved_provider, final_amount=Decimal('500.00'))
    return booking


def test_payment_breakdown_calculation(app):
    """Test 18% GST and 10% commission calculations."""
    with app.app_context():
        breakdown = PaymentService.calculate_breakdown(Decimal('1000.00'))
        assert breakdown['subtotal'] == Decimal('1000.00')
        assert breakdown['gst_rate'] == Decimal('18.0')
        assert breakdown['gst_amount'] == Decimal('180.00')
        assert breakdown['total_amount'] == Decimal('1180.00')
        assert breakdown['commission_rate'] == Decimal('10.0')
        assert breakdown['commission_amount'] == Decimal('100.00')
        assert breakdown['provider_payout_amount'] == Decimal('900.00')


def test_process_simulated_payment_success(completed_booking):
    """Test processing payment: records transaction, generates invoice, holds escrow payout."""
    payment = PaymentService.process_simulated_payment(
        booking=completed_booking,
        payment_method='UPI'
    )

    assert payment.id is not None
    assert payment.transaction_reference.startswith('TXN-')
    assert payment.payment_method == 'UPI'
    assert payment.status == 'PAID'
    assert payment.subtotal == Decimal('500.00')
    assert payment.gst_amount == Decimal('90.00')
    assert payment.amount == Decimal('590.00')
    assert payment.commission_amount == Decimal('50.00')
    assert payment.provider_payout_amount == Decimal('450.00')
    assert payment.payout_status == 'HELD'  # Held in escrow (SRS 4.6.3)

    # Invoice generated
    assert payment.invoice is not None
    assert payment.invoice.invoice_number.startswith('INV-')
    assert payment.invoice.total_amount == Decimal('590.00')


def test_payment_rejected_if_not_completed(customer_user, approved_provider, sample_category):
    """Payment cannot be initiated before provider marks job COMPLETED."""
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='02:00 - 04:00 PM',
        address='Test',
        pincode='400071'
    )

    with pytest.raises(ValueError, match="marked COMPLETED"):
        PaymentService.process_simulated_payment(booking, 'CARD')


def test_reportlab_pdf_invoice_generation(completed_booking, app):
    """Test official PDF invoice generation returns a valid PDF stream."""
    with app.app_context():
        payment = PaymentService.process_simulated_payment(completed_booking, 'UPI')
        pdf_buffer = InvoiceService.generate_pdf_invoice(payment.invoice)

        assert pdf_buffer is not None
        pdf_bytes = pdf_buffer.getvalue()
        # Valid PDF header
        assert pdf_bytes.startswith(b'%PDF')
        assert len(pdf_bytes) > 1000


def test_admin_refund_handling(completed_booking, admin_user):
    """Test admin issuing partial dispute refund to customer (SRS 4.6.3)."""
    payment = PaymentService.process_simulated_payment(completed_booking, 'UPI')

    # Partial refund of ₹200
    PaymentService.issue_refund(
        payment=payment,
        refund_amount=Decimal('200.00'),
        reason="Technician arrived 45 minutes late.",
        admin_user=admin_user
    )

    assert payment.refund_amount == Decimal('200.00')
    assert payment.refund_reason == "Technician arrived 45 minutes late."
    assert payment.refunded_at is not None

