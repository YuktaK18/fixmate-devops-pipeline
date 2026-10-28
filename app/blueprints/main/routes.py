from flask import render_template
from app.blueprints.main import main_bp
from app.models.service import ServiceCategory
from app.models.provider import ProviderProfile
from app.models.review import Review


@main_bp.route('/')
def index():
    """Home landing page showcasing verified categories, top providers, and reviews."""
    categories = ServiceCategory.query.filter_by(is_active=True).all()
    
    # Top rated approved providers
    top_providers = ProviderProfile.query.filter_by(
        verification_status='APPROVED'
    ).order_by(ProviderProfile.rating_avg.desc()).limit(4).all()

    # Recent customer reviews
    featured_reviews = Review.query.filter(Review.rating >= 4)\
        .order_by(Review.created_at.desc()).limit(3).all()

    return render_template(
        'main/index.html',
        categories=categories,
        top_providers=top_providers,
        featured_reviews=featured_reviews
    )


@main_bp.route('/terms')
def terms():
    """Terms of Service page (SRS 6.0)."""
    return render_template('main/terms.html')


@main_bp.route('/privacy')
def privacy():
    """Privacy Policy page (SRS 2.5 & 6.0)."""
    return render_template('main/privacy.html')


@main_bp.route('/faq')
def faq():
    """Frequently Asked Questions and Help Guide (SRS 2.6)."""
    return render_template('main/faq.html')
