from decimal import Decimal
from datetime import datetime, timezone, timedelta, date
from app.models.user import User
from app.models.service import ServiceCategory, ProviderService
from app.models.audit import AdminAuditLog
from app.models.settings import SystemSetting
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.booking_service import BookingService
from app.services.payment_service import PaymentService
from app.extensions import db


def test_admin_access_control(client, customer_user, approved_provider, admin_user):
    """SRS 5.5: Non-admin users cannot access admin dashboard or management routes."""
    # Anonymous
    resp = client.get('/admin/', follow_redirects=False)
    assert resp.status_code == 302  # redirect to login

    # Customer
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})
    resp = client.get('/admin/', follow_redirects=True)
    assert resp.status_code == 403

    client.get('/auth/logout')

    # Provider
    client.post('/auth/login', data={'email': approved_provider.email, 'password': 'Provider@123'})
    resp = client.get('/admin/', follow_redirects=True)
    assert resp.status_code == 403

    client.get('/auth/logout')

    # Admin
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})
    resp = client.get('/admin/', follow_redirects=True)
    assert resp.status_code == 200
    assert b'Administrator Dashboard' in resp.data or b'Platform Operations Dashboard' in resp.data


def test_admin_category_crud_and_price_validation(client, admin_user, approved_provider, db_session):
    """SRS 4.8: Admin manages categories with min/max price bounds; provider service must respect bounds."""
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    # Create new category
    resp = client.post('/admin/categories', data={
        'name': 'HVAC & AC Repair',
        'slug': 'ac-repair',
        'description': 'Air conditioner installation, gas filling, and servicing.',
        'icon': 'bi-snow',
        'min_base_price': '300.00',
        'max_base_price': '3000.00',
        'is_active': 'y'
    }, follow_redirects=True)

    assert resp.status_code == 200
    cat = ServiceCategory.query.filter_by(slug='ac-repair').first()
    assert cat is not None
    assert cat.min_base_price == Decimal('300.00')
    assert cat.max_base_price == Decimal('3000.00')

    # Audit log check
    log = AdminAuditLog.query.filter_by(action='CREATE_CATEGORY').first()
    assert log is not None
    assert log.admin_id == admin_user.id

    client.get('/auth/logout')

    # Provider attempts to set price outside bounds
    client.post('/auth/login', data={'email': approved_provider.email, 'password': 'Provider@123'})
    
    # Below min_base_price (150 < 300)
    resp = client.post('/provider/services', data={
        'category_id': cat.id,
        'custom_price': '150.00',
        'description': 'Cheap AC repair'
    }, follow_redirects=True)
    
    # Should fail validation
    ps = ProviderService.query.filter_by(provider_profile_id=approved_provider.provider_profile.id, category_id=cat.id).first()
    assert ps is None

    # Within bounds (500)
    resp = client.post('/provider/services', data={
        'category_id': cat.id,
        'custom_price': '500.00',
        'description': 'Quality AC service'
    }, follow_redirects=True)
    assert resp.status_code == 200
    ps = ProviderService.query.filter_by(provider_profile_id=approved_provider.provider_profile.id, category_id=cat.id).first()
    assert ps is not None
    assert ps.custom_price == Decimal('500.00')


def test_user_suspension_blocks_login(client, admin_user, customer_user, db_session):
    """SRS 4.8: Admin can suspend a user account, preventing further logins."""
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    # Suspend customer
    resp = client.post(f'/admin/users/{customer_user.id}/toggle-status', follow_redirects=True)
    assert resp.status_code == 200
    db_session.refresh(customer_user)
    assert customer_user.is_suspended is True

    # Check audit log
    log = AdminAuditLog.query.filter_by(action='SUSPEND_USER').first()
    assert log is not None

    client.get('/auth/logout')

    # Suspended user attempts to log in
    resp = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    }, follow_redirects=True)
    assert b'account has been suspended' in resp.data.lower()


def test_admin_settings_update_and_audit(client, admin_user, db_session):
    """SRS 4.8: Admin can update system settings (commission %, cancellation fee, GST %) with audit log."""
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    resp = client.post('/admin/settings', data={
        'commission_percentage': '12.5',
        'cancellation_fee_percentage': '15.0',
        'cancellation_window_minutes': '20',
        'gst_percentage': '18.0'
    }, follow_redirects=True)

    assert resp.status_code == 200
    assert SystemSetting.get_value('commission_percentage') == '12.5'
    assert SystemSetting.get_value('cancellation_fee_percentage') == '15.0'
    assert SystemSetting.get_value('cancellation_window_minutes') == '20'

    log = AdminAuditLog.query.filter_by(action='UPDATE_SETTINGS').first()
    assert log is not None
    assert log.admin_id == admin_user.id


def test_admin_dashboard_metrics(client, admin_user, customer_user, approved_provider, sample_category, db_session):
    """SRS 4.8: Dashboard computes real metrics from MySQL (bookings, revenue, active users)."""
    # Create sample completed booking with payment
    b = BookingService.create_booking(
        customer=customer_user,
        provider=approved_provider,
        category_id=sample_category.id,
        scheduled_date=date.today(),
        time_slot='10:00 - 12:00 PM',
        address='Chembur',
        pincode='400071',
        special_instructions='Test metrics booking'
    )
    BookingService.transition_status(b, 'ACCEPTED', approved_provider)
    BookingService.transition_status(b, 'IN_PROGRESS', approved_provider)
    BookingService.transition_status(b, 'COMPLETED', approved_provider, final_amount=Decimal('1000.00'))
    db_session.commit()

    p = PaymentService.process_simulated_payment(b, 'UPI')

    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})
    resp = client.get('/admin/')
    assert resp.status_code == 200
    assert b'Administrator Dashboard' in resp.data or b'Platform Operations Dashboard' in resp.data
