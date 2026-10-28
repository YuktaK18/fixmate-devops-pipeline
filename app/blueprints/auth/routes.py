from datetime import datetime, timezone
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, current_user, login_required
from app.extensions import db, limiter
from app.blueprints.auth import auth_bp
from app.models.user import User
from app.models.provider import ProviderProfile
from app.forms.auth_forms import RegistrationForm, LoginForm, PasswordResetRequestForm, PasswordResetForm


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("20 per hour")
def register():
    """Customer and Provider registration (Admin registration is strictly prohibited)."""
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    form = RegistrationForm()
    if form.validate_on_submit():
        # Security safeguard: Prevent public creation of Admin accounts
        selected_role = form.role.data
        if selected_role not in ('customer', 'provider'):
            flash('Invalid user role selected.', 'danger')
            return render_template('auth/register.html', form=form)

        user = User(
            name=form.name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip(),
            role=selected_role,
            terms_accepted=form.terms_accepted.data,
            terms_accepted_at=datetime.now(timezone.utc)
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        # If registering as a provider, create an initial provider profile
        if selected_role == 'provider':
            profile = ProviderProfile(
                user_id=user.id,
                service_pincode='400071',  # Default Chembur / VESIT area
                service_area_name='Chembur / Central Mumbai',
                verification_status='PENDING'
            )
            db.session.add(profile)

        db.session.commit()
        flash(f'Account created successfully! Welcome to FixMate, {user.name}. Please sign in to continue.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("15 per minute")
def login():
    """User authentication with 5-strike lockout protection (SRS 4.1.3)."""
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    form = LoginForm()
    demo_reset_link = session.pop('demo_reset_link', None)

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()

        if not user:
            flash('Invalid email address or password.', 'danger')
            return render_template('auth/login.html', form=form, demo_reset_link=demo_reset_link)

        # Check account suspension
        if user.is_suspended:
            flash('This account has been suspended by an administrator. Please contact FixMate support.', 'danger')
            return render_template('auth/login.html', form=form, demo_reset_link=demo_reset_link)

        # Check account lockout policy (5 failed attempts -> 15 min lock)
        if user.is_account_locked():
            remaining_mins = int((user.locked_until.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds() // 60) + 1
            flash(f'Account locked due to 5 consecutive failed login attempts. Please try again in {remaining_mins} minutes or reset your password.', 'danger')
            return render_template('auth/login.html', form=form, demo_reset_link=demo_reset_link)

        # Verify password
        if not user.check_password(form.password.data):
            user.record_failed_login()
            remaining_strikes = 5 - user.failed_login_attempts
            if remaining_strikes > 0:
                flash(f'Invalid email address or password. ({remaining_strikes} attempt(s) remaining before a 15-minute lockout).', 'warning')
            else:
                flash('Account has been locked for 15 minutes due to 5 consecutive failed attempts.', 'danger')
            return render_template('auth/login.html', form=form, demo_reset_link=demo_reset_link)

        # Successful login: reset failed counters and start session
        user.reset_failed_logins()
        login_user(user, remember=form.remember_me.data)

        flash(f'Welcome back, {user.name}!', 'success')
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect_user_by_role(user)

    return render_template('auth/login.html', form=form, demo_reset_link=demo_reset_link)


@auth_bp.route('/logout')
@login_required
def logout():
    """Destroys user session and redirects to home."""
    logout_user()
    flash('You have been securely signed out.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@limiter.limit("5 per hour")
def reset_password_request():
    """Initiates password recovery via token."""
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.generate_reset_token()
            reset_url = url_for('auth.reset_password_token', token=token, _external=True)

            # In Demo Mode, display reset URL in flash / console
            if current_app.config.get('DEMO_MODE', True):
                session['demo_reset_link'] = reset_url
                flash(f'Demo Mode: Password reset link generated! Click the link in the banner below to reset your password.', 'info')
                print(f"[FIXMATE DEMO] Password reset link for {user.email}: {reset_url}")
            else:
                flash('If an account with that email exists, password reset instructions have been sent.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('If an account with that email exists, password reset instructions have been sent.', 'info')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_request.html', form=form)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_token(token):
    """Verifies token and sets a new password."""
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    user = User.query.filter_by(reset_token=token).first()
    if not user or not user.verify_reset_token(token):
        flash('The password reset link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.reset_password_request'))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.clear_reset_token()
        user.reset_failed_logins()
        flash('Your password has been successfully reset! You can now sign in with your new password.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/reset_token.html', form=form, token=token)


def redirect_user_by_role(user: User):
    """Directs authenticated users to their corresponding dashboard."""
    if user.is_admin:
        return redirect(url_for('admin.dashboard'))
    elif user.is_provider:
        return redirect(url_for('provider.dashboard'))
    return redirect(url_for('customer.dashboard'))
