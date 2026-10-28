import io
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from app.models.booking import Booking
from app.models.review import Review
from app.models.complaint import Complaint
from app.services.booking_service import BookingService
from app.extensions import db


def test_review_submission_after_completed_job(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.7: Customer can submit a review (1-5 rating + comment) after booking is COMPLETED."""
    booking_date = date.today() + timedelta(days=2)
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=booking_date,
        time_slot='10:00 - 12:00 PM',
        address='123 Test Road, Chembur',
        pincode='400071',
        special_instructions='Fix pipe leak'
    )
    
    # Fast-forward to COMPLETED
    booking.status = 'COMPLETED'
    booking.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    # Login customer
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    # Post review
    resp = client.post(f'/customer/bookings/{booking.id}/review', data={
        'rating': '5',
        'comment': 'Exceptional plumbing work, very polite and on time!'
    }, follow_redirects=True)

    assert resp.status_code == 200
    rev = Review.query.filter_by(booking_id=booking.id).first()
    assert rev is not None
    assert rev.rating == 5
    assert 'Exceptional plumbing' in rev.comment
    assert rev.customer_id == customer_user.id
    assert rev.provider_id == approved_provider.id


def test_review_prevented_on_non_completed_booking(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.7: Review cannot be submitted on PENDING, ACCEPTED, or CANCELLED bookings."""
    booking_date = date.today() + timedelta(days=2)
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=booking_date,
        time_slot='02:00 - 04:00 PM',
        address='123 Test Road, Chembur',
        pincode='400071',
        special_instructions='Check switchboard'
    )
    assert booking.status == 'PENDING'

    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    resp = client.post(f'/customer/bookings/{booking.id}/review', data={
        'rating': '4',
        'comment': 'Premature review attempt'
    }, follow_redirects=True)

    # Must be rejected
    rev = Review.query.filter_by(booking_id=booking.id).first()
    assert rev is None


def test_duplicate_review_prevented(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.7: Only one review per booking is permitted."""
    booking_date = date.today() + timedelta(days=2)
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=booking_date,
        time_slot='10:00 - 12:00 PM',
        address='123 Test Road, Chembur',
        pincode='400071',
        special_instructions='Fix pipe'
    )
    booking.status = 'COMPLETED'
    booking.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    # First review
    client.post(f'/customer/bookings/{booking.id}/review', data={
        'rating': '4',
        'comment': 'Good service.'
    }, follow_redirects=True)

    # Second review attempt on same booking
    client.post(f'/customer/bookings/{booking.id}/review', data={
        'rating': '2',
        'comment': 'Changed my mind.'
    }, follow_redirects=True)

    # Only 1 review in database
    reviews = Review.query.filter_by(booking_id=booking.id).all()
    assert len(reviews) == 1
    assert reviews[0].rating == 4


def test_rating_recalculation_and_flagging_below_3(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.8: Auto-flag provider for admin review if average rating drops below 3.0."""
    profile = approved_provider.provider_profile
    profile.rating_avg = Decimal('0.00')
    profile.completed_jobs_count = 0
    db_session.commit()

    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    # Create and complete a booking
    b1 = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today() + timedelta(days=1),
        time_slot='10:00 - 12:00 PM',
        address='Chembur',
        pincode='400071',
        special_instructions='Job 1'
    )
    b1.status = 'COMPLETED'
    b1.completed_at = datetime.now(timezone.utc)
    db_session.commit()

    # Submit a 2-star review
    client.post(f'/customer/bookings/{b1.id}/review', data={
        'rating': '2',
        'comment': 'Substandard work'
    }, follow_redirects=True)

    db_session.refresh(profile)
    assert profile.rating_avg == Decimal('2.00')
    assert profile.is_flagged_for_review is True
    assert 'below required 3.0 standard' in (profile.flagged_reason or '')


def test_complaint_within_7_days(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.7: Customer can lodge a complaint within 7 days of booking completion."""
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='10:00 - 12:00 PM',
        address='Chembur',
        pincode='400071',
        special_instructions='Job to complain about'
    )
    booking.status = 'COMPLETED'
    booking.completed_at = datetime.now(timezone.utc) - timedelta(days=2)
    db_session.commit()

    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    resp = client.post(f'/customer/bookings/{booking.id}/complaint', data={
        'subject': 'Water leakage persisted',
        'description': 'The pipe started leaking again just 2 days after the provider claimed it was fixed.'
    }, follow_redirects=True)

    assert resp.status_code == 200
    comp = Complaint.query.filter_by(booking_id=booking.id).first()
    assert comp is not None
    assert comp.status == 'OPEN'
    assert comp.subject == 'Water leakage persisted'


def test_complaint_rejected_after_7_days(client, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.7: Complaint cannot be lodged after 7 days from completion."""
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='10:00 - 12:00 PM',
        address='Chembur',
        pincode='400071',
        special_instructions='Old job'
    )
    booking.status = 'COMPLETED'
    booking.completed_at = datetime.now(timezone.utc) - timedelta(days=8)
    db_session.commit()

    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    client.post(f'/customer/bookings/{booking.id}/complaint', data={
        'subject': 'Too late complaint',
        'description': 'Trying to complain 8 days later.'
    }, follow_redirects=True)

    comp = Complaint.query.filter_by(booking_id=booking.id).first()
    assert comp is None


def test_admin_complaint_resolution(client, admin_user, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.8: Admin manages complaints through status workflow OPEN -> IN_REVIEW -> RESOLVED/REJECTED."""
    booking = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='10:00 - 12:00 PM',
        address='Chembur',
        pincode='400071',
        special_instructions='Complaint job'
    )
    booking.status = 'COMPLETED'
    booking.completed_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    comp = Complaint(
        ticket_number=Complaint.generate_ticket_number(),
        booking_id=booking.id,
        customer_id=customer_user.id,
        subject='Damage caused during installation',
        description='Tile cracked near switchboard.',
        status='OPEN'
    )
    db_session.add(comp)
    db_session.commit()

    # Login as admin
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    # Update complaint to RESOLVED with notes
    resp = client.post(f'/admin/complaints/{comp.id}', data={
        'update_ticket': '1',
        'status': 'RESOLVED',
        'resolution_notes': 'Provider agreed to pay repair cost to customer. Dispute closed amicably.'
    }, follow_redirects=True)

    assert resp.status_code == 200
    db_session.refresh(comp)
    assert comp.status == 'RESOLVED'
    assert 'dispute closed' in comp.resolution_notes.lower()
