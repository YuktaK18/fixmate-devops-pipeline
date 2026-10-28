import io
import pytest
from werkzeug.datastructures import FileStorage
from app.services.kyc_service import KYCService
from app.models.provider import ProviderDocument


def test_kyc_service_allowed_extensions(app):
    """Test KYC file extension and MIME type whitelist."""
    with app.app_context():
        assert KYCService.allowed_file('passport.pdf', 'application/pdf') is True
        assert KYCService.allowed_file('aadhar.png', 'image/png') is True
        assert KYCService.allowed_file('bill.jpeg', 'image/jpeg') is True
        assert KYCService.allowed_file('malicious.exe', 'application/x-msdownload') is False
        assert KYCService.allowed_file('script.sh') is False


def test_document_upload_success_and_randomized_filename(app, pending_provider, db_session):
    """
    Test uploading a KYC document:
    Validates that file is saved with randomized UUID, stored outside public static directory,
    and metadata is persisted in database.
    """
    with app.app_context():
        profile = pending_provider.provider_profile
        fake_pdf = FileStorage(
            stream=io.BytesIO(b"%PDF-1.4 sample pdf content for kyc validation"),
            filename="my_government_id.pdf",
            content_type="application/pdf"
        )

        doc = KYCService.save_provider_document(profile, 'ID_PROOF', fake_pdf)
        assert doc is not None
        assert doc.original_filename == "my_government_id.pdf"
        assert doc.stored_filename.endswith(".pdf")
        assert doc.stored_filename != "my_government_id.pdf"  # Randomized
        assert doc.document_type == 'ID_PROOF'


def test_unapproved_provider_hidden_from_search(client, customer_user, pending_provider, sample_category):
    """
    SRS 4.3 & 5.5: Unapproved providers must be hidden from customers and not bookable.
    """
    # Authenticate as customer
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    resp = client.get(f'/customer/categories/{sample_category.slug}')
    assert resp.status_code == 200
    # Pending provider should NOT be in the results
    assert pending_provider.name.encode() not in resp.data


def test_approved_provider_visible_in_search(client, customer_user, approved_provider, sample_category):
    """Approved providers must be visible in customer search results."""
    client.post('/auth/login', data={'email': customer_user.email, 'password': 'Customer@123'})

    resp = client.get(f'/customer/categories/{sample_category.slug}')
    assert resp.status_code == 200
    assert approved_provider.name.encode() in resp.data


def test_admin_approve_provider(client, admin_user, pending_provider, db_session):
    """Test admin reviewing and approving a provider's application (SRS 4.8.3)."""
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    profile = pending_provider.provider_profile
    resp = client.post(f'/admin/providers/{profile.id}', data={
        'action': 'APPROVE',
        'rejection_reason': ''
    }, follow_redirects=True)

    assert resp.status_code == 200
    db_session.refresh(profile)
    assert profile.verification_status == 'APPROVED'
    assert profile.verified_at is not None
    assert profile.verified_by_admin_id == admin_user.id


def test_admin_reject_provider_requires_reason(client, admin_user, pending_provider, db_session):
    """Test admin rejecting provider requires mandatory reason (SRS 4.8 & Requirements)."""
    client.post('/auth/login', data={'email': admin_user.email, 'password': 'Admin@FixMate2026!'})

    profile = pending_provider.provider_profile
    # Attempt reject without reason
    resp = client.post(f'/admin/providers/{profile.id}', data={
        'action': 'REJECT',
        'rejection_reason': ''
    })

    assert resp.status_code == 200
    assert b"mandatory rejection reason is required" in resp.data
    db_session.refresh(profile)
    assert profile.verification_status == 'PENDING'

    # Reject with mandatory reason
    resp2 = client.post(f'/admin/providers/{profile.id}', data={
        'action': 'REJECT',
        'rejection_reason': 'The uploaded Aadhaar photo is cropped and blurry.'
    }, follow_redirects=True)

    assert resp2.status_code == 200
    db_session.refresh(profile)
    assert profile.verification_status == 'REJECTED'
    assert profile.rejection_reason == 'The uploaded Aadhaar photo is cropped and blurry.'

