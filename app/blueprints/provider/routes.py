from datetime import datetime, timezone
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import current_user
from app.extensions import db
from app.blueprints.provider import provider_bp
from app.utils.decorators import provider_required, approved_provider_required
from app.models.provider import ProviderProfile, ProviderDocument
from app.models.service import ServiceCategory, ProviderService
from app.models.booking import Booking
from app.models.payment import Payment
from app.services.kyc_service import KYCService
from app.services.booking_service import BookingService, BookingTransitionError, DoubleBookingError
from app.forms.provider_forms import (
    ProviderProfileForm, DocumentUploadForm, ProviderServiceForm, JobCompleteForm
)
from app.forms.customer_forms import RescheduleRequestForm


@provider_bp.route('/')
@provider_bp.route('/dashboard')
@provider_required
def dashboard():
    """Provider dashboard: verification state, availability, pending requests, and key earnings metrics."""
    # Check for expired bookings automatically
    BookingService.check_and_expire_pending_bookings()

    profile = current_user.provider_profile
    if not profile:
        profile = ProviderProfile(user_id=current_user.id, service_pincode='400071', service_area_name='Chembur')
        db.session.add(profile)
        db.session.commit()

    # Active requests awaiting response
    pending_requests = Booking.query.filter_by(provider_id=current_user.id, status='PENDING')\
        .order_by(Booking.created_at.asc()).all()

    # Upcoming active jobs
    active_jobs = Booking.query.filter(
        Booking.provider_id == current_user.id,
        Booking.status.in_(['ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED'])
    ).order_by(Booking.scheduled_date.asc()).limit(5).all()

    # Earnings metrics
    completed_payments = Payment.query.join(Booking, Payment.booking_id == Booking.id)\
        .filter(Booking.provider_id == current_user.id, Payment.status == 'PAID').all()
    
    total_net_payout = sum(p.provider_payout_amount for p in completed_payments)
    total_commission_paid = sum(p.commission_amount for p in completed_payments)

    return render_template(
        'provider/dashboard.html',
        profile=profile,
        pending_requests=pending_requests,
        active_jobs=active_jobs,
        total_net_payout=total_net_payout,
        total_commission_paid=total_commission_paid
    )


@provider_bp.route('/profile', methods=['GET', 'POST'])
@provider_required
def profile():
    """Manage professional background, operating radius, and availability status."""
    profile = current_user.provider_profile
    form = ProviderProfileForm(obj=profile)

    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip()
        
        profile.bio = form.bio.data.strip() if form.bio.data else None
        profile.experience_years = form.experience_years.data
        profile.service_pincode = form.service_pincode.data.strip()
        profile.service_area_name = form.service_area_name.data.strip()
        profile.service_radius_km = form.service_radius_km.data
        profile.availability_status = form.availability_status.data

        db.session.commit()
        flash('Provider profile and availability updated successfully!', 'success')
        return redirect(url_for('provider.profile'))

    # Pre-populate user fields
    form.name.data = current_user.name
    form.phone.data = current_user.phone
    return render_template('provider/profile.html', form=form, profile=profile)


@provider_bp.route('/documents', methods=['GET', 'POST'])
@provider_required
def documents():
    """Upload ID Proof and Address Proof for KYC verification (SRS 4.2)."""
    profile = current_user.provider_profile
    form = DocumentUploadForm()

    if form.validate_on_submit():
        uploaded_count = 0
        error_messages = []

        if form.id_proof.data:
            try:
                KYCService.save_provider_document(profile, 'ID_PROOF', form.id_proof.data)
                uploaded_count += 1
            except ValueError as e:
                error_messages.append(f"ID Proof: {e}")

        if form.address_proof.data:
            try:
                KYCService.save_provider_document(profile, 'ADDRESS_PROOF', form.address_proof.data)
                uploaded_count += 1
            except ValueError as e:
                error_messages.append(f"Address Proof: {e}")

        if error_messages:
            for err in error_messages:
                flash(err, 'danger')
        elif uploaded_count > 0:
            flash('Document(s) uploaded successfully! Your verification application is under Admin review.', 'success')
            return redirect(url_for('provider.documents'))
        else:
            flash('Please select at least one document to upload.', 'warning')

    return render_template('provider/documents.html', form=form, profile=profile)


@provider_bp.route('/documents/<int:document_id>')
@provider_required
def view_document(document_id):
    """Securely stream uploaded document to the owner provider."""
    return KYCService.serve_document(document_id)


@provider_bp.route('/services', methods=['GET', 'POST'])
@provider_required
def services():
    """Manage service categories and customized pricing within admin bounds."""
    profile = current_user.provider_profile
    form = ProviderServiceForm()

    # Populate category choices
    all_categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.name.asc()).all()
    form.category_id.choices = [(c.id, f"{c.name} (Admin Range: ₹{c.min_base_price} - ₹{c.max_base_price})") for c in all_categories]

    if form.validate_on_submit():
        selected_cat = db.session.get(ServiceCategory, form.category_id.data)
        if not selected_cat:
            flash('Invalid category selected.', 'danger')
            return redirect(url_for('provider.services'))

        # Enforce Admin Price Limits (SRS 4.2.3)
        price = form.custom_price.data
        if price < selected_cat.min_base_price or price > selected_cat.max_base_price:
            flash(f"Price ₹{price} is out of permitted range (₹{selected_cat.min_base_price} to ₹{selected_cat.max_base_price}) for {selected_cat.name}.", 'danger')
            return redirect(url_for('provider.services'))

        existing_svc = ProviderService.query.filter_by(
            provider_profile_id=profile.id,
            category_id=selected_cat.id
        ).first()

        if existing_svc:
            existing_svc.custom_price = price
            existing_svc.description = form.description.data.strip() if form.description.data else None
            flash(f"Updated pricing for {selected_cat.name} to ₹{price}.", 'success')
        else:
            new_svc = ProviderService(
                provider_profile_id=profile.id,
                category_id=selected_cat.id,
                custom_price=price,
                description=form.description.data.strip() if form.description.data else None
            )
            db.session.add(new_svc)
            flash(f"Added {selected_cat.name} service offering at ₹{price}.", 'success')

        db.session.commit()
        return redirect(url_for('provider.services'))

    my_services = ProviderService.query.filter_by(provider_profile_id=profile.id).all()
    return render_template('provider/services.html', form=form, my_services=my_services, categories=all_categories)


@provider_bp.route('/services/<int:service_id>/delete', methods=['POST'])
@provider_required
def delete_service(service_id):
    """Remove a service offering from provider profile."""
    profile = current_user.provider_profile
    svc = ProviderService.query.filter_by(id=service_id, provider_profile_id=profile.id).first_or_404()
    cat_name = svc.category.name
    db.session.delete(svc)
    db.session.commit()
    flash(f"Service offering '{cat_name}' removed.", 'info')
    return redirect(url_for('provider.services'))


@provider_bp.route('/bookings')
@provider_required
def bookings():
    """Provider jobs filtered by status (Requests, In-Progress, Completed)."""
    BookingService.check_and_expire_pending_bookings()

    tab = request.args.get('tab', 'requests')
    query = Booking.query.filter_by(provider_id=current_user.id)

    if tab == 'requests':
        query = query.filter(Booking.status == 'PENDING')
    elif tab == 'active':
        query = query.filter(Booking.status.in_(['ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED']))
    elif tab == 'completed':
        query = query.filter(Booking.status == 'COMPLETED')
    elif tab == 'all':
        pass
    else:
        query = query.filter(Booking.status.in_(['PENDING', 'ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED']))

    job_list = query.order_by(Booking.scheduled_date.asc(), Booking.created_at.desc()).all()
    return render_template('provider/bookings.html', jobs=job_list, current_tab=tab)


@provider_bp.route('/bookings/<int:booking_id>')
@provider_required
def booking_detail(booking_id):
    """Detailed view for a specific job."""
    booking = Booking.query.filter_by(id=booking_id, provider_id=current_user.id).first_or_404()
    complete_form = JobCompleteForm()
    reschedule_form = RescheduleRequestForm()
    return render_template(
        'provider/booking_detail.html',
        booking=booking,
        complete_form=complete_form,
        reschedule_form=reschedule_form
    )


@provider_bp.route('/bookings/<int:booking_id>/accept', methods=['POST'])
@approved_provider_required
def accept_booking(booking_id):
    """Accept an incoming booking request within the 5-minute response window."""
    booking = Booking.query.filter_by(id=booking_id, provider_id=current_user.id).first_or_404()

    if booking.status != 'PENDING':
        flash('Booking is no longer pending acceptance.', 'warning')
        return redirect(url_for('provider.booking_detail', booking_id=booking.id))

    if booking.has_expired_window:
        flash('The 5-minute response window has expired for this booking.', 'danger')
        BookingService.check_and_expire_pending_bookings()
        return redirect(url_for('provider.bookings'))

    try:
        BookingService.transition_status(
            booking=booking,
            new_status='ACCEPTED',
            changed_by=current_user,
            notes=f"Provider {current_user.name} accepted the job request."
        )
        flash(f'Booking #{booking.booking_code} accepted! Customer has been notified.', 'success')
    except BookingTransitionError as e:
        flash(str(e), 'danger')

    return redirect(url_for('provider.booking_detail', booking_id=booking.id))


@provider_bp.route('/bookings/<int:booking_id>/reject', methods=['POST'])
@approved_provider_required
def reject_booking(booking_id):
    """Decline an incoming booking request."""
    booking = Booking.query.filter_by(id=booking_id, provider_id=current_user.id).first_or_404()

    if booking.status != 'PENDING':
        flash('Booking is no longer pending acceptance.', 'warning')
        return redirect(url_for('provider.booking_detail', booking_id=booking.id))

    try:
        BookingService.transition_status(
            booking=booking,
            new_status='REJECTED',
            changed_by=current_user,
            notes=f"Provider {current_user.name} declined the request."
        )
        flash(f'Booking #{booking.booking_code} declined.', 'info')
        # Check and auto-reassign to next candidate
        BookingService.check_and_expire_pending_bookings()
    except BookingTransitionError as e:
        flash(str(e), 'danger')

    return redirect(url_for('provider.bookings'))


@provider_bp.route('/bookings/<int:booking_id>/start', methods=['POST'])
@approved_provider_required
def start_job(booking_id):
    """Technician marks arrival and begins the job (IN_PROGRESS)."""
    booking = Booking.query.filter_by(id=booking_id, provider_id=current_user.id).first_or_404()

    try:
        BookingService.transition_status(
            booking=booking,
            new_status='IN_PROGRESS',
            changed_by=current_user,
            notes=f"Provider {current_user.name} arrived at site and commenced service."
        )
        flash(f'Job #{booking.booking_code} started! Customer has been notified.', 'success')
    except BookingTransitionError as e:
        flash(str(e), 'danger')

    return redirect(url_for('provider.booking_detail', booking_id=booking.id))


@provider_bp.route('/bookings/<int:booking_id>/complete', methods=['POST'])
@approved_provider_required
def complete_job(booking_id):
    """Mark job as complete with confirmed final billable amount (SRS 4.6.2)."""
    booking = Booking.query.filter_by(id=booking_id, provider_id=current_user.id).first_or_404()
    form = JobCompleteForm()

    if form.validate_on_submit():
        final_amt = form.final_amount.data
        notes = form.notes.data.strip() if form.notes.data else "Service completed."
        
        try:
            BookingService.transition_status(
                booking=booking,
                new_status='COMPLETED',
                changed_by=current_user,
                notes=f"Job marked completed. Final amount confirmed: ₹{final_amt}. Notes: {notes}",
                final_amount=final_amt
            )
            flash(f'Job #{booking.booking_code} marked completed! Final amount set to ₹{final_amt}. Customer can now proceed with payment.', 'success')
        except BookingTransitionError as e:
            flash(str(e), 'danger')
    else:
        flash('Please enter a valid final confirmed bill amount.', 'danger')

    return redirect(url_for('provider.booking_detail', booking_id=booking.id))


@provider_bp.route('/earnings')
@provider_required
def earnings():
    """Earnings ledger with platform commission breakdown and payout states."""
    payments = Payment.query.join(Booking, Payment.booking_id == Booking.id)\
        .filter(Booking.provider_id == current_user.id, Payment.status == 'PAID')\
        .order_by(Payment.paid_at.desc()).all()

    total_gross = sum(p.subtotal for p in payments)
    total_commission = sum(p.commission_amount for p in payments)
    total_payout = sum(p.provider_payout_amount for p in payments)
    held_payout = sum(p.provider_payout_amount for p in payments if p.payout_status == 'HELD')
    released_payout = sum(p.provider_payout_amount for p in payments if p.payout_status == 'RELEASED')

    return render_template(
        'provider/earnings.html',
        payments=payments,
        total_gross=total_gross,
        total_commission=total_commission,
        total_payout=total_payout,
        held_payout=held_payout,
        released_payout=released_payout
    )
