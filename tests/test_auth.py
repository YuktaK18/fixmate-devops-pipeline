import pytest
from datetime import datetime, timezone, timedelta
from app.models.user import User


def test_customer_registration_success(client, db_session):
    """Test successful customer registration via public form."""
    resp = client.post('/auth/register', data={
        'name': 'New Customer',
        'email': 'new.customer@fixmate.local',
        'phone': '9812345678',
        'role': 'customer',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'terms_accepted': 'y'
    }, follow_redirects=True)

    assert resp.status_code == 200
    user = User.query.filter_by(email='new.customer@fixmate.local').first()
    assert user is not None
    assert user.role == 'customer'
    assert user.check_password('Password@123') is True
    assert user.provider_profile is None


def test_provider_registration_creates_profile(client, db_session):
    """Test provider registration initializes a PENDING provider profile (SRS 4.1 & 4.2)."""
    resp = client.post('/auth/register', data={
        'name': 'New Provider',
        'email': 'new.provider@fixmate.local',
        'phone': '9812345679',
        'role': 'provider',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'terms_accepted': 'y'
    }, follow_redirects=True)

    assert resp.status_code == 200
    user = User.query.filter_by(email='new.provider@fixmate.local').first()
    assert user is not None
    assert user.role == 'provider'
    assert user.provider_profile is not None
    assert user.provider_profile.verification_status == 'PENDING'


def test_public_registration_cannot_create_admin(client, db_session):
    """Security Test: Public registration must never allow creation of admin accounts."""
    resp = client.post('/auth/register', data={
        'name': 'Hacker Admin',
        'email': 'hacker@fixmate.local',
        'phone': '9812345680',
        'role': 'admin',
        'password': 'Password@123',
        'confirm_password': 'Password@123',
        'terms_accepted': 'y'
    }, follow_redirects=True)

    user = User.query.filter_by(email='hacker@fixmate.local').first()
    assert user is None


def test_user_login_success_and_logout(client, customer_user):
    """Test login and session termination."""
    login_resp = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    }, follow_redirects=True)

    assert login_resp.status_code == 200
    assert b"Welcome back, Test Customer" in login_resp.data

    logout_resp = client.get('/auth/logout', follow_redirects=True)
    assert logout_resp.status_code == 200
    assert b"signed out" in logout_resp.data


def test_five_failed_logins_triggers_15_minute_lockout(client, customer_user):
    """
    SRS 4.1.3: The system shall lock an account for 15 minutes after 5 failed login attempts in a row.
    """
    assert customer_user.failed_login_attempts == 0
    assert customer_user.is_account_locked() is False

    # Attempt 4 failed logins
    for attempt in range(1, 5):
        resp = client.post('/auth/login', data={
            'email': customer_user.email,
            'password': 'WrongPassword123'
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert customer_user.failed_login_attempts == attempt
        assert customer_user.is_account_locked() is False

    # 5th failed attempt triggers lock
    resp5 = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'WrongPassword123'
    }, follow_redirects=True)

    assert customer_user.failed_login_attempts == 5
    assert customer_user.locked_until is not None
    assert customer_user.is_account_locked() is True

    # Attempt with correct password while locked must still be rejected
    resp_locked = client.post('/auth/login', data={
        'email': customer_user.email,
        'password': 'Customer@123'
    }, follow_redirects=True)

    assert b"Account locked due to 5 consecutive failed login attempts" in resp_locked.data


def test_password_reset_token_generation_and_verification(customer_user):
    """Test cryptographic reset token issuance and expiry validation."""
    token = customer_user.generate_reset_token()
    assert token is not None
    assert customer_user.verify_reset_token(token) is True

    # Expired token test
    customer_user.reset_token_expiry = datetime.now(timezone.utc) - timedelta(minutes=5)
    assert customer_user.verify_reset_token(token) is False

