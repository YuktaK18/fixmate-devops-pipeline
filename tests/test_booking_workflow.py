import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from app.services.booking_service import BookingService, BookingTransitionError, DoubleBookingError
from app.models.booking import Booking


def test_create_booking_success(customer_user, approved_provider, sample_category):
    """Test standard booking creation within 30-day window."""
    target_date = date.today() + timedelta(days=3)
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=target_date,
        time_slot='02:00 - 04:00 PM',
        address='Flat 101, Green View, Chembur',
        pincode='400071',
        special_instructions='Please call when nearby.'
    )

    assert booking.id is not None
    assert booking.booking_code.startswith('FIX-')
    assert booking.status == 'PENDING'
    assert booking.quoted_amount == Decimal('350.00')
    assert booking.response_deadline is not None


def test_booking_creation_rejects_past_or_too_distant_dates(customer_user, approved_provider, sample_category):
    """SRS 4.4.3: Disallow past dates and dates beyond 30 days."""
    # Past date
    with pytest.raises(ValueError, match="past date"):
        BookingService.create_booking(
            customer=customer_user,
            provider=approved_provider,
            category_id=sample_category.id,
            scheduled_date=date.today() - timedelta(days=1),
            time_slot='09:00 - 11:00 AM',
            address='123 Test St',
            pincode='400071'
        )

    # 35 days ahead
    with pytest.raises(ValueError, match="up to 30 days"):
        BookingService.create_booking(
            customer=customer_user,
            provider=approved_provider,
            category_id=sample_category.id,
            scheduled_date=date.today() + timedelta(days=35),
            time_slot='09:00 - 11:00 AM',
            address='123 Test St',
            pincode='400071'
        )


def test_double_booking_prevention(customer_user, approved_provider, sample_category):
    """
    Core Safeguard: Prevent overlapping bookings for the same provider and time slot.
    """
    target_date = date.today() + timedelta(days=2)
    slot = '11:00 - 01:00 PM'

    # First booking succeeds
    b1 = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=target_date,
        time_slot=slot,
        address='Customer A Address',
        pincode='400071'
    )
    assert b1.status == 'PENDING'

    # Second booking for the same slot must fail
    with pytest.raises(DoubleBookingError, match="already booked"):
        BookingService.create_booking(
            customer=customer_user,
            provider=approved_provider,
            category_id=sample_category.id,
            scheduled_date=target_date,
            time_slot=slot,
            address='Customer B Address',
            pincode='400071'
        )


def test_valid_and_invalid_status_transitions(customer_user, approved_provider, sample_category):
    """
    State Machine Verification:
    Valid: PENDING -> ACCEPTED -> IN_PROGRESS -> COMPLETED
    Invalid: PENDING -> COMPLETED (must raise BookingTransitionError)
    """
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today() + timedelta(days=1),
        time_slot='04:00 - 06:00 PM',
        address='123 Main St',
        pincode='400071'
    )

    # Attempt illegal jump: PENDING -> COMPLETED
    with pytest.raises(BookingTransitionError):
        BookingService.transition_status(booking, 'COMPLETED', approved_provider)

    # Valid step 1: PENDING -> ACCEPTED
    BookingService.transition_status(booking, 'ACCEPTED', approved_provider)
    assert booking.status == 'ACCEPTED'

    # Valid step 2: ACCEPTED -> IN_PROGRESS
    BookingService.transition_status(booking, 'IN_PROGRESS', approved_provider)
    assert booking.status == 'IN_PROGRESS'

    # Valid step 3: IN_PROGRESS -> COMPLETED with final amount
    BookingService.transition_status(booking, 'COMPLETED', approved_provider, final_amount=Decimal('400.00'))
    assert booking.status == 'COMPLETED'
    assert booking.final_amount == Decimal('400.00')

    # Cannot cancel after completion
    with pytest.raises(BookingTransitionError):
        BookingService.cancel_booking(booking, customer_user)


def test_cancellation_fee_rules(customer_user, approved_provider, sample_category):
    """
    SRS 5.5 Business Rules:
    - Cancelling while PENDING: Fee is ₹0.
    - Cancelling an ACCEPTED booking on the same scheduled day: 10% fee applied.
    """
    # 1. Cancel while PENDING
    b_pending = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today() + timedelta(days=5),
        time_slot='09:00 - 11:00 AM',
        address='Test St',
        pincode='400071'
    )
    BookingService.cancel_booking(b_pending, customer_user, "Changed mind")
    assert b_pending.status == 'CANCELLED'
    assert b_pending.cancellation_fee == Decimal('0.00')

    # 2. Cancel on the same day when ACCEPTED
    b_same_day = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='06:00 - 08:00 PM',
        address='Test St',
        pincode='400071'
    )
    BookingService.transition_status(b_same_day, 'ACCEPTED', approved_provider)
    BookingService.cancel_booking(b_same_day, customer_user, "Late cancellation")

    assert b_same_day.status == 'CANCELLED'
    # 10% of 350.00 = 35.00
    assert b_same_day.cancellation_fee == Decimal('35.00')


def test_reschedule_mutual_agreement(customer_user, approved_provider, sample_category):
    """
    SRS 4.4.3: Rescheduling confirmed appointment requires mutual acceptance.
    """
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today() + timedelta(days=2),
        time_slot='11:00 - 01:00 PM',
        address='Test St',
        pincode='400071'
    )
    BookingService.transition_status(booking, 'ACCEPTED', approved_provider)

    new_date = date.today() + timedelta(days=4)
    new_slot = '02:00 - 04:00 PM'

    # Customer proposes reschedule
    BookingService.request_reschedule(booking, customer_user, new_date, new_slot)
    assert booking.status == 'RESCHEDULED'
    assert booking.reschedule_proposed_date == new_date
    assert booking.reschedule_proposed_time_slot == new_slot

    # Provider accepts reschedule
    BookingService.respond_to_reschedule(booking, approved_provider, accept=True)
    assert booking.status == 'ACCEPTED'
    assert booking.scheduled_date == new_date
    assert booking.scheduled_time_slot == new_slot
    assert booking.reschedule_proposed_date is None

