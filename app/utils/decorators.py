from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def customer_required(f):
    """Decorator ensuring that the authenticated user is an active Customer."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_suspended or not current_user.is_active:
            flash('Your account has been deactivated or suspended. Please contact support.', 'danger')
            return redirect(url_for('auth.logout'))
        if current_user.role != 'customer':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def provider_required(f):
    """Decorator ensuring that the authenticated user is an active Service Provider."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_suspended or not current_user.is_active:
            flash('Your account has been deactivated or suspended. Please contact support.', 'danger')
            return redirect(url_for('auth.logout'))
        if current_user.role != 'provider':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def approved_provider_required(f):
    """Decorator ensuring that the Service Provider is verified and APPROVED by admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.role != 'provider':
            abort(403)
        profile = current_user.provider_profile
        if not profile or profile.verification_status != 'APPROVED':
            flash('Access restricted: Your profile must be approved by an administrator before performing this action.', 'warning')
            return redirect(url_for('provider.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator ensuring that the authenticated user is an Administrator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.is_suspended or not current_user.is_active:
            flash('Admin account inactive.', 'danger')
            return redirect(url_for('auth.logout'))
        if current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function
