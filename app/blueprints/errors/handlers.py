from flask import render_template
from app.blueprints.errors import errors_bp
from app.extensions import db


@errors_bp.app_errorhandler(400)
def bad_request_error(error):
    return render_template('errors/400.html'), 400


@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403


@errors_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@errors_bp.app_errorhandler(429)
def ratelimit_handler(error):
    return render_template('errors/429.html'), 429


@errors_bp.app_errorhandler(500)
def internal_server_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500
