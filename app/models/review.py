from datetime import datetime, timezone
from app.extensions import db


class Review(db.Model):
    """Customer ratings and feedback submitted strictly after job completion."""
    __tablename__ = 'reviews'
    __table_args__ = (
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='chk_review_rating_range'),
    )

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    provider_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    provider_profile_id = db.Column(db.Integer, db.ForeignKey('provider_profiles.id', ondelete='CASCADE'), nullable=False, index=True)
    
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5 stars
    comment = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<Review id={self.id} booking={self.booking_id} stars={self.rating}>"
