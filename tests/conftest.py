import os
import sys
import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date

# Ensure root folder is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.provider import ProviderProfile, ProviderDocument
from app.models.service import ServiceCategory, ProviderService
from app.models.booking import Booking, BookingStatusHistory
from app.models.payment import Payment, Invoice
from app.models.review import Review
from app.models.complaint import Complaint
from app.models.settings import SystemSetting


@pytest.fixture(scope='session')
def app():
    """Create and configure Flask application instance for testing."""
    _app = create_app('testing')
    with _app.app_context():
        db.create_all()
        yield _app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def db_session(app):
    """Provides a transactional database session rolled back or cleared after each test."""
    with app.app_context():
        # Clear database tables cleanly
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            db.session.execute(table.delete())
        
        # Seed system settings
        SystemSetting.set_value('commission_percentage', '10.0')
        SystemSetting.set_value('cancellation_fee_percentage', '10.0')
        SystemSetting.set_value('cancellation_window_minutes', '15')
        SystemSetting.set_value('gst_percentage', '18.0')
        db.session.commit()

        yield db.session
        db.session.rollback()


@pytest.fixture
def client(app, db_session):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def customer_user(db_session):
    """Sample Customer fixture."""
    user = User(
        name='Test Customer',
        email='customer.test@fixmate.local',
        phone='9811111111',
        role='customer',
        terms_accepted=True
    )
    user.set_password('Customer@123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def approved_provider(db_session, sample_category):
    """Sample Approved Provider fixture."""
    user = User(
        name='Approved Provider',
        email='provider.approved@fixmate.local',
        phone='9822222222',
        role='provider',
        terms_accepted=True
    )
    user.set_password('Provider@123')
    db.session.add(user)
    db.session.flush()

    profile = ProviderProfile(
        user_id=user.id,
        bio='Master technician with 5 years experience.',
        experience_years=5,
        service_pincode='400071',
        service_area_name='Chembur, Mumbai',
        service_radius_km=15,
        verification_status='APPROVED',
        availability_status='AVAILABLE',
        rating_avg=Decimal('4.80'),
        completed_jobs_count=10
    )
    db.session.add(profile)
    db.session.flush()

    svc = ProviderService(
        provider_profile_id=profile.id,
        category_id=sample_category.id,
        custom_price=Decimal('350.00'),
        description='Standard inspection and repair service.'
    )
    db.session.add(svc)
    db.session.commit()
    return user


@pytest.fixture
def pending_provider(db_session):
    """Sample Pending Provider fixture (Unapproved)."""
    user = User(
        name='Pending Provider',
        email='provider.pending@fixmate.local',
        phone='9833333333',
        role='provider',
        terms_accepted=True
    )
    user.set_password('Provider@123')
    db.session.add(user)
    db.session.flush()

    profile = ProviderProfile(
        user_id=user.id,
        bio='Unverified applicant.',
        experience_years=2,
        service_pincode='400071',
        service_area_name='Chembur',
        verification_status='PENDING',
        availability_status='AVAILABLE'
    )
    db.session.add(profile)
    db.session.commit()
    return user


@pytest.fixture
def admin_user(db_session):
    """Sample Administrator fixture."""
    user = User(
        name='Super Admin',
        email='admin.test@fixmate.local',
        phone='9899999999',
        role='admin',
        terms_accepted=True
    )
    user.set_password('Admin@FixMate2026!')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_category(db_session):
    """Sample Service Category fixture."""
    cat = ServiceCategory(
        name='Plumbing Test',
        slug='plumbing-test',
        description='Water pipes, leaks, and sanitary fittings.',
        icon='bi-droplet-half',
        min_base_price=Decimal('200.00'),
        max_base_price=Decimal('2500.00'),
        is_active=True
    )
    db.session.add(cat)
    db.session.commit()
    return cat

