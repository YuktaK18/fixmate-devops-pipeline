from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import current_user
from sqlalchemy import func
from app.extensions import db
from app.blueprints.admin import admin_bp
from app.utils.decorators import admin_required
from app.models.user import User
from app.models.provider import ProviderProfile, ProviderDocument
from app.models.service import ServiceCategory, ProviderService
from app.models.booking import Booking
from app.models.payment import Payment, Invoice
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.models.audit import AdminAuditLog
from app.models.settings import SystemSetting
from app.services.kyc_service import KYCService
from app.services.payment_service import PaymentService
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService
from app.forms.admin_forms import (
    ProviderVerificationForm, CategoryForm, ComplaintResolutionForm, SystemSettingsForm, RefundForm
)


@admin_bp.route('/')
@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Administrator dashboard with real MySQL statistics (SRS 4.8 & 5.5):
    Daily, weekly, and monthly bookings, revenue aggregations, and platform alerts.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    # Real MySQL Booking Aggregations
    daily_bookings = Booking.query.filter(Booking.created_at >= today_start).count()
    weekly_bookings = Booking.query.filter(Booking.created_at >= week_start).count()
    monthly_bookings = Booking.query.filter(Booking.created_at >= month_start).count()
    total_bookings = Booking.query.count()

    # Financial Aggregations from MySQL
    total_revenue_result = db.session.query(func.coalesce(func.sum(Payment.amount), Decimal('0.00')))\
        .filter(Payment.status.in_(['PAID', 'REFUNDED'])).scalar()
    
    total_commission_result = db.session.query(func.coalesce(func.sum(Payment.commission_amount), Decimal('0.00')))\
        .filter(Payment.status == 'PAID').scalar()

    total_refunds_result = db.session.query(func.coalesce(func.sum(Payment.refund_amount), Decimal('0.00'))).scalar()

    # User Metrics
    total_customers = User.query.filter_by(role='customer', is_active=True).count()
    total_providers = User.query.filter_by(role='provider', is_active=True).count()
    
    # Operational Action Counters
    pending_kyc_count = ProviderProfile.query.filter_by(verification_status='PENDING').count()
    open_complaints_count = Complaint.query.filter(Complaint.status.in_(['OPEN', 'IN_REVIEW'])).count()
    flagged_providers_count = ProviderProfile.query.filter_by(is_flagged_for_review=True).count()

    # Recent Audit Log preview
    recent_logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(8).all()

    return render_template(
        'admin/dashboard.html',
        daily_bookings=daily_bookings,
        weekly_bookings=weekly_bookings,
        monthly_bookings=monthly_bookings,
        total_bookings=total_bookings,
        total_revenue=total_revenue_result,
        total_commission=total_commission_result,
        total_refunds=total_refunds_result,
        total_customers=total_customers,
        total_providers=total_providers,
        pending_kyc_count=pending_kyc_count,
        open_complaints_count=open_complaints_count,
        flagged_providers_count=flagged_providers_count,
        recent_logs=recent_logs
    )


@admin_bp.route('/providers')
@admin_required
def providers():
    """List service providers with status filtering (PENDING, APPROVED, REJECTED, FLAGGED)."""
    filter_status = request.args.get('status', 'ALL')
    query = ProviderProfile.query.join(User, ProviderProfile.user_id == User.id)

    if filter_status == 'PENDING':
        query = query.filter(ProviderProfile.verification_status == 'PENDING')
    elif filter_status == 'APPROVED':
        query = query.filter(ProviderProfile.verification_status == 'APPROVED')
    elif filter_status == 'REJECTED':
        query = query.filter(ProviderProfile.verification_status == 'REJECTED')
    elif filter_status == 'FLAGGED':
        query = query.filter(ProviderProfile.is_flagged_for_review.is_(True))

    provider_list = query.order_by(ProviderProfile.created_at.desc()).all()
    return render_template('admin/providers.html', providers=provider_list, current_filter=filter_status)


@admin_bp.route('/providers/<int:profile_id>', methods=['GET', 'POST'])
@admin_required
def provider_review(profile_id):
    """Review provider KYC application, inspect documents securely, approve/reject with mandatory reason."""
    profile = ProviderProfile.query.get_or_404(profile_id)
    form = ProviderVerificationForm()

    if form.validate_on_submit():
        action = form.action.data
        reason = form.rejection_reason.data.strip() if form.rejection_reason.data else None

        if action == 'REJECT' and not reason:
            flash('A mandatory rejection reason is required when rejecting a provider.', 'danger')
            return render_template('admin/provider_review.html', profile=profile, form=form)

        if action == 'APPROVE':
            profile.verification_status = 'APPROVED'
            profile.rejection_reason = None
            profile.verified_at = datetime.now(timezone.utc)
            profile.verified_by_admin_id = current_user.id
            flash_msg = f"Provider {profile.user.name} approved successfully!"
            notif_msg = "Congratulations! Your FixMate provider account has been approved by admin. You can now accept customer bookings."
        else:
            profile.verification_status = 'REJECTED'
            profile.rejection_reason = reason
            profile.verified_at = datetime.now(timezone.utc)
            profile.verified_by_admin_id = current_user.id
            flash_msg = f"Provider {profile.user.name} rejected."
            notif_msg = f"Your provider verification application was rejected. Reason: {reason}. You may re-upload corrected documents."

        db.session.commit()

        # Record audit log
        AuditService.log(
            action=f"{action}_PROVIDER",
            target_entity='ProviderProfile',
            target_id=str(profile.id),
            details=f"Provider {profile.user.email} marked as {profile.verification_status}. Notes: {reason or 'Approved'}"
        )

        # Notify Provider
        NotificationService.send(
            user_id=profile.user_id,
            title=f"Verification Application {profile.verification_status.title()}",
            message=notif_msg,
            notification_type='ACCOUNT',
            link_url='/provider/dashboard'
        )

        flash(flash_msg, 'success' if action == 'APPROVE' else 'warning')
        return redirect(url_for('admin.providers'))

    return render_template('admin/provider_review.html', profile=profile, form=form)


@admin_bp.route('/documents/<int:document_id>')
@admin_required
def view_document(document_id):
    """Secure endpoint for admins to inspect uploaded KYC files."""
    return KYCService.serve_document(document_id)


@admin_bp.route('/users')
@admin_required
def users():
    """Platform user management (view accounts, suspension toggle)."""
    role_filter = request.args.get('role', 'ALL')
    search_query = request.args.get('q', '').strip()

    query = User.query.filter(User.role != 'admin')
    if role_filter in ('customer', 'provider'):
        query = query.filter_by(role=role_filter)
    if search_query:
        query = query.filter(
            (User.name.ilike(f"%{search_query}%")) | (User.email.ilike(f"%{search_query}%")) | (User.phone.ilike(f"%{search_query}%"))
        )

    user_list = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=user_list, role_filter=role_filter, search_query=search_query)


@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Suspend or reactivate a user account (SRS 4.8.3)."""
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Administrator accounts cannot be suspended.', 'danger')
        return redirect(url_for('admin.users'))

    user.is_suspended = not user.is_suspended
    db.session.commit()

    action_label = "SUSPEND_USER" if user.is_suspended else "REACTIVATE_USER"
    AuditService.log(
        action=action_label,
        target_entity='User',
        target_id=str(user.id),
        details=f"User {user.email} (Role: {user.role}) was {'suspended' if user.is_suspended else 'reactivated'}."
    )

    flash(f"User {user.name} ({user.email}) has been {'suspended' if user.is_suspended else 'reactivated'}.", 'info')
    return redirect(url_for('admin.users'))


@admin_bp.route('/categories', methods=['GET', 'POST'])
@admin_required
def categories():
    """Category CRUD operations with min/max price boundaries (SRS 4.2.3)."""
    form = CategoryForm()

    if form.validate_on_submit():
        if form.min_base_price.data > form.max_base_price.data:
            flash('Minimum base price cannot be greater than maximum base price.', 'danger')
            return redirect(url_for('admin.categories'))

        # Check existing slug or name
        if ServiceCategory.query.filter_by(slug=form.slug.data).first():
            flash('A category with this URL slug already exists.', 'danger')
            return redirect(url_for('admin.categories'))

        cat = ServiceCategory(
            name=form.name.data.strip(),
            slug=form.slug.data.strip().lower(),
            description=form.description.data.strip() if form.description.data else None,
            icon=form.icon.data.strip(),
            min_base_price=form.min_base_price.data,
            max_base_price=form.max_base_price.data,
            is_active=form.is_active.data
        )
        db.session.add(cat)
        db.session.commit()

        AuditService.log(
            action='CREATE_CATEGORY',
            target_entity='ServiceCategory',
            target_id=str(cat.id),
            details=f"Created service category '{cat.name}' with price range ₹{cat.min_base_price}-₹{cat.max_base_price}"
        )
        flash(f"Category '{cat.name}' created successfully!", 'success')
        return redirect(url_for('admin.categories'))

    all_categories = ServiceCategory.query.order_by(ServiceCategory.name.asc()).all()
    return render_template('admin/categories.html', form=form, categories=all_categories)


@admin_bp.route('/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """Edit existing service category."""
    cat = ServiceCategory.query.get_or_404(category_id)
    form = CategoryForm(obj=cat)

    if form.validate_on_submit():
        if form.min_base_price.data > form.max_base_price.data:
            flash('Minimum base price cannot be greater than maximum base price.', 'danger')
            return render_template('admin/category_edit.html', form=form, category=cat)

        cat.name = form.name.data.strip()
        cat.slug = form.slug.data.strip().lower()
        cat.description = form.description.data.strip() if form.description.data else None
        cat.icon = form.icon.data.strip()
        cat.min_base_price = form.min_base_price.data
        cat.max_base_price = form.max_base_price.data
        cat.is_active = form.is_active.data

        db.session.commit()
        AuditService.log(
            action='UPDATE_CATEGORY',
            target_entity='ServiceCategory',
            target_id=str(cat.id),
            details=f"Updated category '{cat.name}'"
        )
        flash(f"Category '{cat.name}' updated successfully!", 'success')
        return redirect(url_for('admin.categories'))

    return render_template('admin/category_edit.html', form=form, category=cat)


@admin_bp.route('/bookings')
@admin_required
def bookings():
    """View and search all platform bookings across all states."""
    status_filter = request.args.get('status', 'ALL')
    search = request.args.get('q', '').strip()

    query = Booking.query
    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)
    if search:
        query = query.filter(
            (Booking.booking_code.ilike(f"%{search}%")) |
            (Booking.service_address.ilike(f"%{search}%"))
        )

    all_bookings = query.order_by(Booking.created_at.desc()).all()
    return render_template('admin/bookings.html', bookings=all_bookings, current_filter=status_filter, search=search)


@admin_bp.route('/complaints')
@admin_required
def complaints():
    """Complaints and disputes workflow: OPEN -> IN_REVIEW -> RESOLVED / REJECTED (SRS 4.7.3)."""
    status_filter = request.args.get('status', 'ALL')
    query = Complaint.query

    if status_filter != 'ALL':
        query = query.filter_by(status=status_filter)

    all_complaints = query.order_by(Complaint.created_at.desc()).all()
    return render_template('admin/complaints.html', complaints=all_complaints, current_filter=status_filter)


@admin_bp.route('/complaints/<int:complaint_id>', methods=['GET', 'POST'])
@admin_required
def complaint_detail(complaint_id):
    """View and resolve a specific customer dispute ticket."""
    complaint = Complaint.query.get_or_404(complaint_id)
    form = ComplaintResolutionForm(obj=complaint)
    refund_form = RefundForm()

    if form.validate_on_submit() and 'update_ticket' in request.form:
        new_status = form.status.data
        notes = form.resolution_notes.data.strip()

        complaint.status = new_status
        complaint.resolution_notes = notes
        complaint.resolved_by_admin_id = current_user.id
        complaint.resolved_at = datetime.now(timezone.utc)
        db.session.commit()

        AuditService.log(
            action='RESOLVE_COMPLAINT',
            target_entity='Complaint',
            target_id=str(complaint.id),
            details=f"Ticket #{complaint.ticket_number} marked as {new_status}. Notes: {notes}"
        )

        NotificationService.send(
            user_id=complaint.customer_id,
            title=f"Dispute Ticket #{complaint.ticket_number} Updated",
            message=f"Your complaint ticket status has been updated to {new_status}. Admin Resolution: {notes}",
            notification_type='DISPUTE',
            link_url='/customer/complaints'
        )

        flash(f"Complaint ticket #{complaint.ticket_number} updated to {new_status}.", 'success')
        return redirect(url_for('admin.complaints'))

    return render_template(
        'admin/complaint_detail.html',
        complaint=complaint,
        form=form,
        refund_form=refund_form
    )


@admin_bp.route('/payments')
@admin_required
def payments():
    """Platform revenue ledger, commission calculations, and dispute refunds."""
    all_payments = Payment.query.order_by(Payment.paid_at.desc()).all()
    return render_template('admin/payments.html', payments=all_payments)


@admin_bp.route('/payments/<int:payment_id>/release-payout', methods=['POST'])
@admin_required
def release_payout(payment_id):
    """Releases held payout to provider account."""
    payment = Payment.query.get_or_404(payment_id)
    if payment.payout_status == 'RELEASED':
        flash('Payout has already been released.', 'info')
    else:
        PaymentService.release_payout(payment, current_user)
        flash(f'Payout of ₹{payment.provider_payout_amount} released to provider {payment.booking.provider.name}.', 'success')
    return redirect(url_for('admin.payments'))


@admin_bp.route('/payments/<int:payment_id>/refund', methods=['POST'])
@admin_required
def refund_payment(payment_id):
    """Processes dispute refund for a customer (SRS 4.6.3)."""
    payment = Payment.query.get_or_404(payment_id)
    form = RefundForm()

    if form.validate_on_submit():
        amt = form.refund_amount.data
        reason = form.refund_reason.data.strip()
        try:
            PaymentService.issue_refund(payment=payment, refund_amount=amt, reason=reason, admin_user=current_user)
            flash(f"Refund of ₹{amt} processed successfully for transaction {payment.transaction_reference}.", 'success')
        except ValueError as e:
            flash(str(e), 'danger')
    else:
        flash('Invalid refund submission.', 'danger')

    return redirect(url_for('admin.payments'))


@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def settings():
    """Admin-configurable platform settings (Commission, GST, Cancellation Fee & Window)."""
    form = SystemSettingsForm()

    if form.validate_on_submit():
        SystemSetting.set_value('commission_percentage', str(form.commission_percentage.data), 'Platform commission %')
        SystemSetting.set_value('cancellation_fee_percentage', str(form.cancellation_fee_percentage.data), 'Cancellation penalty %')
        SystemSetting.set_value('cancellation_window_minutes', str(form.cancellation_window_minutes.data), 'Cancellation window in minutes')
        SystemSetting.set_value('gst_percentage', str(form.gst_percentage.data), 'GST tax %')

        AuditService.log(
            action='UPDATE_SETTINGS',
            target_entity='SystemSetting',
            details=f"Updated: Comm={form.commission_percentage.data}%, Fee={form.cancellation_fee_percentage.data}%, Window={form.cancellation_window_minutes.data}min, GST={form.gst_percentage.data}%"
        )
        flash('Platform configuration settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    # Load initial values
    form.commission_percentage.data = Decimal(SystemSetting.get_value('commission_percentage', '10.0'))
    form.cancellation_fee_percentage.data = Decimal(SystemSetting.get_value('cancellation_fee_percentage', '10.0'))
    form.cancellation_window_minutes.data = int(SystemSetting.get_value('cancellation_window_minutes', '15'))
    form.gst_percentage.data = Decimal(SystemSetting.get_value('gst_percentage', '18.0'))

    return render_template('admin/settings.html', form=form)


@admin_bp.route('/audit-logs')
@admin_required
def audit_logs():
    """Immutable audit trail showing all admin activities."""
    logs = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(200).all()
    return render_template('admin/audit_logs.html', logs=logs)
