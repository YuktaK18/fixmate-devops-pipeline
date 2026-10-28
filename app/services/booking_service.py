from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from flask import current_app
from sqlalchemy import and_, or_
from app.extensions import db
from app.models.booking import Booking, BookingStatusHistory
from app.models.provider import ProviderProfile
from app.models.user import User
from app.models.service import ProviderService
from app.models.settings import SystemSetting
from app.models.notification import Notification


class BookingTransitionError(Exception):
    """Raised when an invalid status transition is attempted."""
    pass


class DoubleBookingError(Exception):
    """Raised when an overlapping booking is attempted for the same provider slot."""
    pass


class BookingService:
    """Core state machine and booking workflow coordinator."""

    # Explicit State Machine Transition Rules (SRS 4.4 & Core Booking Workflow)
    ALLOWED_TRANSITIONS = {
        'PENDING': {'ACCEPTED', 'REJECTED', 'CANCELLED'},
        'ACCEPTED': {'IN_PROGRESS', 'RESCHEDULED', 'CANCELLED'},
        'RESCHEDULED': {'ACCEPTED', 'CANCELLED'},
        'IN_PROGRESS': {'COMPLETED'},
        'COMPLETED': set(),
        'REJECTED': set(),
        'CANCELLED': set(),
    }

    ACTIVE_SLOT_STATUSES = ('PENDING', 'ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED')

    @classmethod
    def check_double_booking(cls, provider_id: int, scheduled_date: date, time_slot: str, exclude_booking_id: int = None) -> bool:
        """
        Returns True if the provider already has an active booking on that date and slot.
        """
        query = Booking.query.filter(
            Booking.provider_id == provider_id,
            Booking.scheduled_date == scheduled_date,
            Booking.scheduled_time_slot == time_slot,
            Booking.status.in_(cls.ACTIVE_SLOT_STATUSES)
        )
        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)
        return query.first() is not None

    @classmethod
    def create_booking(cls, customer: User, provider: User, category_id: int,
                       scheduled_date: date, time_slot: str, address: str, pincode: str,
                       special_instructions: str = None) -> Booking:
        """
        Creates a new booking with row locking safeguards against double-booking race conditions.
        """
        # Validate scheduled date (must be today or up to 30 days ahead per SRS 4.4.3)
        today = datetime.now(timezone.utc).date()
        max_date = today + timedelta(days=30)
        if scheduled_date < today:
            raise ValueError("You cannot book a service for a past date.")
        if scheduled_date > max_date:
            raise ValueError("Bookings can only be scheduled up to 30 days in advance.")

        # Validate provider profile and verification status
        provider_profile = provider.provider_profile
        if not provider_profile or not provider_profile.is_approved:
            raise ValueError("The selected provider is not currently approved to accept bookings.")
        if provider_profile.availability_status == 'OFFLINE':
            raise ValueError("The selected provider is currently offline.")

        # Validate provider offers this category and get custom price
        provider_svc = ProviderService.query.filter_by(
            provider_profile_id=provider_profile.id,
            category_id=category_id
        ).first()
        if not provider_svc:
            raise ValueError("The selected provider does not offer this service category.")
        
        quoted_price = provider_svc.custom_price

        # Safeguard: Row-lock existing active bookings for this provider and slot
        # Using with_for_update() inside transaction
        conflict = Booking.query.filter(
            Booking.provider_id == provider.id,
            Booking.scheduled_date == scheduled_date,
            Booking.scheduled_time_slot == time_slot,
            Booking.status.in_(cls.ACTIVE_SLOT_STATUSES)
        ).with_for_update().first()

        if conflict:
            raise DoubleBookingError(
                f"Provider {provider.name} is already booked for {time_slot} on {scheduled_date.strftime('%d-%b-%Y')}."
            )

        # 5-minute response window for provider (SRS 4.4.3)
        response_deadline = datetime.now(timezone.utc) + timedelta(minutes=5)

        booking = Booking(
            booking_code=Booking.generate_booking_code(),
            customer_id=customer.id,
            provider_id=provider.id,
            category_id=category_id,
            scheduled_date=scheduled_date,
            scheduled_time_slot=time_slot,
            service_address=address,
            pincode=pincode,
            special_instructions=special_instructions,
            status='PENDING',
            quoted_amount=quoted_price,
            response_deadline=response_deadline
        )
        db.session.add(booking)
        db.session.flush()

        # Record initial status history
        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=None,
            new_status='PENDING',
            changed_by_user_id=customer.id,
            notes=f"Booking created by customer {customer.name}. Awaiting provider acceptance (5-minute response window)."
        )
        db.session.add(history)

        # Send alert notification to Provider
        notif = Notification(
            user_id=provider.id,
            title="New Booking Request",
            message=f"New job request #{booking.booking_code} for {scheduled_date.strftime('%d-%b-%Y')} ({time_slot}). You have 5 minutes to accept.",
            notification_type='BOOKING',
            link_url=f"/provider/bookings/{booking.id}"
        )
        db.session.add(notif)
        db.session.commit()
        return booking

    @classmethod
    def transition_status(cls, booking: Booking, new_status: str, changed_by: User,
                          notes: str = None, final_amount: Decimal = None) -> Booking:
        """
        Validates transition through explicit transition map, logs to history, and updates timestamps.
        """
        current_status = booking.status
        allowed = cls.ALLOWED_TRANSITIONS.get(current_status, set())

        if new_status not in allowed:
            raise BookingTransitionError(
                f"Invalid booking status transition: Cannot move from '{current_status}' to '{new_status}'. Allowed transitions: {sorted(list(allowed))}"
            )

        # Special handling for transitions
        if new_status == 'COMPLETED':
            if final_amount is not None and final_amount > 0:
                booking.final_amount = final_amount
            else:
                booking.final_amount = booking.quoted_amount
            
            # Increment provider completed job count
            if booking.provider and booking.provider.provider_profile:
                booking.provider.provider_profile.completed_jobs_count += 1

        booking.status = new_status
        db.session.add(booking)

        # Record status change in audit history
        history = BookingStatusHistory(
            booking_id=booking.id,
            previous_status=current_status,
            new_status=new_status,
            changed_by_user_id=changed_by.id if changed_by else None,
            notes=notes
        )
        db.session.add(history)

        # Send notification to the opposite party
        recipient_id = booking.customer_id if changed_by and changed_by.id == booking.provider_id else booking.provider_id
        notif_msg = f"Booking #{booking.booking_code} status updated to {new_status}."
        if notes:
            notif_msg += f" Note: {notes}"

        notif = Notification(
            user_id=recipient_id,
            title=f"Booking {new_status.title()}",
            message=notif_msg,
            notification_type='BOOKING',
            link_url=f"/customer/bookings/{booking.id}" if recipient_id == booking.customer_id else f"/provider/bookings/{booking.id}"
        )
        db.session.add(notif)
        db.session.commit()
        return booking

    @classmethod
    def cancel_booking(cls, booking: Booking, cancelled_by: User, reason: str = None) -> Booking:
        """
        Applies cancellation policy (SRS 5.5):
        If customer cancels an ACCEPTED booking close to the scheduled slot (default 15 minutes or same-day),
        a cancellation fee (default 10%) is applied.
        """
        if booking.status in ('COMPLETED', 'CANCELLED', 'REJECTED'):
            raise BookingTransitionError(f"Cannot cancel a booking that is already {booking.status}.")

        fee = Decimal('0.00')

        # Check fee rule if cancelled by Customer on an ACCEPTED booking
        if cancelled_by.id == booking.customer_id and booking.status in ('ACCEPTED', 'RESCHEDULED'):
            today = datetime.now(timezone.utc).date()
            window_minutes = int(SystemSetting.get_value('cancellation_window_minutes', '15'))
            fee_pct = Decimal(SystemSetting.get_value('cancellation_fee_percentage', '10.0'))

            # If cancelling on the same day as scheduled service
            if booking.scheduled_date <= today:
                fee = (booking.quoted_amount * (fee_pct / Decimal('100.0'))).quantize(Decimal('0.01'))

        booking.cancellation_fee = fee
        booking.cancellation_reason = reason or "Cancelled by user"
        booking.cancelled_by_user_id = cancelled_by.id

        return cls.transition_status(
            booking=booking,
            new_status='CANCELLED',
            changed_by=cancelled_by,
            notes=f"Cancelled by {cancelled_by.name}. Reason: {reason or 'No reason provided'}. Cancellation Fee: ₹{fee}"
        )

    @classmethod
    def request_reschedule(cls, booking: Booking, requested_by: User, proposed_date: date, proposed_slot: str) -> Booking:
        """
        Initiates a reschedule proposal. Both customer and provider must agree (SRS 4.4.3).
        """
        if booking.status not in ('ACCEPTED', 'RESCHEDULED'):
            raise BookingTransitionError("Rescheduling can only be requested for confirmed, accepted bookings.")

        today = datetime.now(timezone.utc).date()
        if proposed_date < today:
            raise ValueError("Proposed reschedule date cannot be in the past.")

        # Check provider availability on the proposed slot
        if cls.check_double_booking(booking.provider_id, proposed_date, proposed_slot, exclude_booking_id=booking.id):
            raise DoubleBookingError("The provider is already booked for that proposed date and time slot.")

        booking.reschedule_proposed_date = proposed_date
        booking.reschedule_proposed_time_slot = proposed_slot
        booking.reschedule_requested_by_id = requested_by.id

        cls.transition_status(
            booking=booking,
            new_status='RESCHEDULED',
            changed_by=requested_by,
            notes=f"Reschedule requested by {requested_by.name} for {proposed_date.strftime('%d-%b-%Y')} ({proposed_slot}). Awaiting approval."
        )
        return booking

    @classmethod
    def respond_to_reschedule(cls, booking: Booking, responding_user: User, accept: bool) -> Booking:
        """
        Accepts or declines a pending reschedule proposal.
        """
        if booking.status != 'RESCHEDULED':
            raise BookingTransitionError("Booking does not have an active reschedule request.")

        if accept:
            old_date = booking.scheduled_date
            old_slot = booking.scheduled_time_slot
            booking.scheduled_date = booking.reschedule_proposed_date
            booking.scheduled_time_slot = booking.reschedule_proposed_time_slot
            booking.reschedule_proposed_date = None
            booking.reschedule_proposed_time_slot = None
            booking.reschedule_requested_by_id = None

            return cls.transition_status(
                booking=booking,
                new_status='ACCEPTED',
                changed_by=responding_user,
                notes=f"Reschedule accepted by {responding_user.name}. New appointment: {booking.scheduled_date.strftime('%d-%b-%Y')} ({booking.scheduled_time_slot}) (previously {old_date} {old_slot})."
            )
        else:
            booking.reschedule_proposed_date = None
            booking.reschedule_proposed_time_slot = None
            booking.reschedule_requested_by_id = None

            return cls.transition_status(
                booking=booking,
                new_status='ACCEPTED',
                changed_by=responding_user,
                notes=f"Reschedule request declined by {responding_user.name}. Booking remains at original schedule: {booking.scheduled_date.strftime('%d-%b-%Y')} ({booking.scheduled_time_slot})."
            )

    @classmethod
    def check_and_expire_pending_bookings(cls):
        """
        SRS 4.4.3: If a provider does not accept within 5 minutes, auto-offer the booking to the
        next best-matched approved and available provider in the same category & area,
        or mark it REJECTED / unassigned if none is found.
        """
        now = datetime.now(timezone.utc)
        expired_bookings = Booking.query.filter(
            Booking.status == 'PENDING',
            Booking.response_deadline.isnot(None),
            Booking.response_deadline < now
        ).all()

        for booking in expired_bookings:
            # Find next best-matched approved, available provider offering the same category
            next_provider = User.query.join(ProviderProfile, User.id == ProviderProfile.user_id)\
                .join(ProviderService, ProviderProfile.id == ProviderService.provider_profile_id)\
                .filter(
                    User.role == 'provider',
                    User.id != booking.provider_id,
                    User.is_active.is_(True),
                    User.is_suspended.is_(False),
                    ProviderProfile.verification_status == 'APPROVED',
                    ProviderProfile.availability_status == 'AVAILABLE',
                    ProviderService.category_id == booking.category_id
                ).order_by(ProviderProfile.rating_avg.desc()).first()

            if next_provider and not cls.check_double_booking(next_provider.id, booking.scheduled_date, booking.scheduled_time_slot):
                old_provider_id = booking.provider_id
                booking.provider_id = next_provider.id
                booking.response_deadline = now + timedelta(minutes=5)
                
                # Fetch provider price
                prov_svc = ProviderService.query.filter_by(
                    provider_profile_id=next_provider.provider_profile.id,
                    category_id=booking.category_id
                ).first()
                if prov_svc:
                    booking.quoted_amount = prov_svc.custom_price

                # Record re-assignment
                history = BookingStatusHistory(
                    booking_id=booking.id,
                    previous_status='PENDING',
                    new_status='PENDING',
                    changed_by_user_id=None,
                    notes=f"Auto-offered to next available provider {next_provider.name} after original provider timed out (5-minute rule)."
                )
                db.session.add(history)

                # Notify new provider
                notif = Notification(
                    user_id=next_provider.id,
                    title="New Booking Request (Auto-Offered)",
                    message=f"Booking #{booking.booking_code} for {booking.scheduled_date} ({booking.scheduled_time_slot}) offered to you. You have 5 minutes to respond.",
                    notification_type='BOOKING',
                    link_url=f"/provider/bookings/{booking.id}"
                )
                db.session.add(notif)
            else:
                # No replacement available: mark as REJECTED with clear notice
                booking.status = 'REJECTED'
                history = BookingStatusHistory(
                    booking_id=booking.id,
                    previous_status='PENDING',
                    new_status='REJECTED',
                    changed_by_user_id=None,
                    notes="Provider did not respond within 5-minute window and no alternate provider was available. Booking auto-closed."
                )
                db.session.add(history)
                notif = Notification(
                    user_id=booking.customer_id,
                    title="Booking Expired",
                    message=f"Your booking request #{booking.booking_code} expired because no provider accepted in time. Please try booking another provider.",
                    notification_type='BOOKING',
                    link_url=f"/customer/bookings/{booking.id}"
                )
                db.session.add(notif)
        db.session.commit()
