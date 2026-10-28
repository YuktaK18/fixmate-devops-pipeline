from datetime import datetime, timezone
from decimal import Decimal
from app.extensions import db


class ServiceCategory(db.Model):
    """Admin-managed service categories with mandated price boundaries."""
    __tablename__ = 'service_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    icon = db.Column(db.String(100), default='bi-wrench', nullable=False)
    
    # Admin-defined price boundaries (SRS 4.2.3)
    min_base_price = db.Column(db.Numeric(10, 2), default=Decimal('199.00'), nullable=False)
    max_base_price = db.Column(db.Numeric(10, 2), default=Decimal('5000.00'), nullable=False)
    
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    provider_services = db.relationship('ProviderService', backref='category', cascade='all, delete-orphan', lazy='dynamic')
    bookings = db.relationship('Booking', backref='category', lazy='dynamic')

    def __repr__(self):
        return f"<ServiceCategory id={self.id} name='{self.name}' range={self.min_base_price}-{self.max_base_price}>"


class ProviderService(db.Model):
    """Specific category offered by a provider with their personalized price."""
    __tablename__ = 'provider_services'
    __table_args__ = (
        db.UniqueConstraint('provider_profile_id', 'category_id', name='uq_provider_category'),
    )

    id = db.Column(db.Integer, primary_key=True)
    provider_profile_id = db.Column(db.Integer, db.ForeignKey('provider_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    
    custom_price = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<ProviderService provider_id={self.provider_profile_id} cat_id={self.category_id} price={self.custom_price}>"
