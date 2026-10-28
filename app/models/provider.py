from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class ProviderProfile(db.Model):
    """Extended profile information for Service Providers."""
    __tablename__ = 'provider_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    
    bio = db.Column(db.Text, nullable=True)
    experience_years = db.Column(db.Integer, default=1, nullable=False)
    service_pincode = db.Column(db.String(10), nullable=False, index=True)
    service_area_name = db.Column(db.String(100), nullable=False, default='Central Mumbai')
    service_radius_km = db.Column(db.Integer, default=15, nullable=False)
    
    # KYC & Verification Status (SRS 4.2: PENDING, APPROVED, REJECTED)
    verification_status = db.Column(
        db.Enum('PENDING', 'APPROVED', 'REJECTED', name='provider_verification_enum'),
        default='PENDING',
        nullable=False,
        index=True
    )
    rejection_reason = db.Column(db.Text, nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by_admin_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Availability Status (SRS 4.2.3: Available, Busy, Offline)
    availability_status = db.Column(
        db.Enum('AVAILABLE', 'BUSY', 'OFFLINE', name='provider_availability_enum'),
        default='AVAILABLE',
        nullable=False,
        index=True
    )

    # Performance & Quality Metrics
    rating_avg = db.Column(db.Numeric(3, 2), default=Decimal('0.00'), nullable=False)
    rating_count = db.Column(db.Integer, default=0, nullable=False)
    completed_jobs_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Auto-flagging for admin review (SRS 5.5: rating below 3.0)
    is_flagged_for_review = db.Column(db.Boolean, default=False, nullable=False)
    flagged_reason = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    documents = db.relationship('ProviderDocument', backref='provider_profile', cascade='all, delete-orphan', lazy='joined')
    services = db.relationship('ProviderService', backref='provider_profile', cascade='all, delete-orphan', lazy='selectin')
    reviews_received = db.relationship('Review', foreign_keys='Review.provider_profile_id', backref='provider_profile', lazy='dynamic')

    @property
    def is_approved(self) -> bool:
        """Determines if provider is approved and eligible to accept bookings."""
        return self.verification_status == 'APPROVED' and self.user.is_active and not self.user.is_suspended

    @property
    def has_uploaded_all_documents(self) -> bool:
        """Verifies that provider has uploaded both ID proof and address proof."""
        doc_types = {doc.document_type for doc in self.documents}
        return 'ID_PROOF' in doc_types and 'ADDRESS_PROOF' in doc_types

    @property
    def starting_price(self) -> float:
        """Returns the minimum base price across all services offered by provider."""
        if not self.services:
            return 0.0
        return float(min(s.custom_price for s in self.services))

    def update_rating_stats(self):
        """Recalculates average rating and triggers auto-flagging rule if rating < 3.0."""
        from app.models.review import Review
        reviews = Review.query.filter_by(provider_id=self.user_id).all()
        if not reviews:
            self.rating_avg = Decimal('0.00')
            self.rating_count = 0
            self.is_flagged_for_review = False
            self.flagged_reason = None
        else:
            total_stars = sum(r.rating for r in reviews)
            self.rating_count = len(reviews)
            self.rating_avg = Decimal(str(round(total_stars / self.rating_count, 2)))
            
            # SRS 5.5: Auto-flag if rating drops below 3.0
            if self.rating_count >= 1 and self.rating_avg < Decimal('3.00'):
                self.is_flagged_for_review = True
                self.flagged_reason = f"Average rating dropped to {self.rating_avg} (below required 3.0 standard)."
            else:
                self.is_flagged_for_review = False
                self.flagged_reason = None
        db.session.commit()

    def __repr__(self):
        return f"<ProviderProfile id={self.id} user_id={self.user_id} status='{self.verification_status}'>"


class ProviderDocument(db.Model):
    """Secure metadata record for uploaded verification documents."""
    __tablename__ = 'provider_documents'

    id = db.Column(db.Integer, primary_key=True)
    provider_profile_id = db.Column(db.Integer, db.ForeignKey('provider_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    document_type = db.Column(
        db.Enum('ID_PROOF', 'ADDRESS_PROOF', name='document_type_enum'),
        nullable=False
    )
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ProviderDocument id={self.id} type='{self.document_type}' filename='{self.stored_filename}'>"
