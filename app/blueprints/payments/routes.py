from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from app.extensions import db
from app.blueprints.payments import payments_bp
from app.utils.decorators import customer_required
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.payment_service import PaymentService


@payments_bp.route('/checkout/<int:booking_id>')
@customer_required
def checkout(booking_id):
    """
    Simulated Payment Checkout Screen (SRS 4.6).
    Clearly labelled 'SIMULATED PAYMENT (Demo Mode)'.
    Allows selecting UPI, Card, Net Banking, or Wallet.
    """
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()

    if booking.status != 'COMPLETED':
        flash('Payments are processed only after the job is completed by the provider.', 'warning')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))

    if booking.payment:
        flash('This booking has already been paid for.', 'info')
        return redirect(url_for('customer.invoice_detail', invoice_id=booking.payment.invoice.id))

    subtotal = booking.final_amount if booking.final_amount else booking.quoted_amount
    breakdown = PaymentService.calculate_breakdown(subtotal)

    return render_template(
        'payments/checkout.html',
        booking=booking,
        breakdown=breakdown
    )


@payments_bp.route('/process/<int:booking_id>', methods=['POST'])
@customer_required
def process_payment(booking_id):
    """Processes simulated payment in Demo Mode and generates digital invoice."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    payment_method = request.form.get('payment_method', 'UPI')

    if payment_method not in ('UPI', 'CARD', 'NET_BANKING', 'WALLET'):
        flash('Invalid payment method selected.', 'danger')
        return redirect(url_for('payments.checkout', booking_id=booking.id))

    try:
        payment = PaymentService.process_simulated_payment(
            booking=booking,
            payment_method=payment_method
        )
        flash(f'Simulated Payment Successful! Transaction Ref: {payment.transaction_reference}. Digital invoice generated.', 'success')
        return redirect(url_for('customer.invoice_detail', invoice_id=payment.invoice.id))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))
