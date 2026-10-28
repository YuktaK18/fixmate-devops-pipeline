from flask import jsonify, abort
from flask_login import current_user
from sqlalchemy import text
from app.extensions import db
from app.blueprints.api import api_bp
from app.models.booking import Booking
from app.services.notification_service import NotificationService


@api_bp.route('/health')
def health_check():
    """
    Health check endpoint verifying application runtime and MySQL database connectivity.
    Essential for production health monitoring (Render / Railway / AWS).
    """
    try:
        # Ping MySQL server via raw query
        db.session.execute(text('SELECT 1'))
        db_status = 'connected'
        status_code = 200
    except Exception as e:
        db_status = f'disconnected: {str(e)}'
        status_code = 503

    return jsonify({
        'status': 'healthy' if status_code == 200 else 'degraded',
        'database': db_status,
        'app': 'FixMate Home Service Management System',
        'version': '1.0.0'
    }), status_code


@api_bp.route('/tracking/<int:booking_id>')
def tracking_status(booking_id):
    """
    Simulated live ETA and provider location status (SRS 4.5).
    Dynamically responds based on booking state without requiring external GPS credentials.
    """
    booking = db.session.get(Booking, booking_id)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    # Authorization: Customer, Provider, or Admin only
    is_authorized = (current_user.is_authenticated and (
        current_user.id == booking.customer_id or
        current_user.id == booking.provider_id or
        current_user.is_admin
    ))
    if not is_authorized:
        return jsonify({'error': 'Unauthorized'}), 403

    # Dynamic simulated ETA calculation
    if booking.status == 'ACCEPTED':
        eta_minutes = 25
        status_text = f"Provider {booking.provider.name} has accepted and is preparing travel."
        stage = 'PREPARING'
    elif booking.status == 'IN_PROGRESS':
        eta_minutes = 0
        status_text = f"Provider {booking.provider.name} is on site. Job is currently IN PROGRESS."
        stage = 'ON_SITE'
    elif booking.status == 'COMPLETED':
        eta_minutes = 0
        status_text = "Service completed."
        stage = 'COMPLETED'
    else:
        eta_minutes = None
        status_text = f"Booking is currently {booking.status}."
        stage = booking.status

    return jsonify({
        'booking_code': booking.booking_code,
        'status': booking.status,
        'stage': stage,
        'eta_minutes': eta_minutes,
        'status_text': status_text,
        'provider_name': booking.provider.name,
        'provider_phone': booking.provider.phone,
        'service_address': booking.service_address,
        'pincode': booking.pincode
    })


@api_bp.route('/notifications/unread-count')
def unread_notifications_count():
    """Returns number of unread notifications for active user."""
    if not current_user.is_authenticated:
        return jsonify({'unread_count': 0})
    count = NotificationService.get_unread_count(current_user.id)
    return jsonify({'unread_count': count})
