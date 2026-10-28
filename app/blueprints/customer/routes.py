import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from flask import render_template, redirect, url_for, flash, request, abort, send_file, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.extensions import db
from app.blueprints.customer import customer_bp
from app.utils.decorators import customer_required
from app.models.user import User
from app.models.provider import ProviderProfile
from app.models.service import ServiceCategory, ProviderService
from app.models.booking import Booking
from app.models.payment import Payment, Invoice
from app.models.review import Review
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.services.booking_service import BookingService, BookingTransitionError, DoubleBookingError
from app.services.invoice_service import InvoiceService
from app.forms.customer_forms import (
    CustomerProfileForm, BookingCreateForm, RescheduleRequestForm, ReviewForm, ComplaintForm
)


@customer_bp.route('/')
@customer_bp.route('/dashboard')
@customer_required
def dashboard():
    """Customer overview: quick statistics, active bookings, and category shortcuts."""
    # Check for expired bookings automatically
    BookingService.check_and_expire_pending_bookings()

    upcoming_bookings = Booking.query.filter(
        Booking.customer_id == current_user.id,
        Booking.status.in_(['PENDING', 'ACCEPTED', 'RESCHEDULED', 'IN_PROGRESS'])
    ).order_by(Booking.scheduled_date.asc()).limit(5).all()

    completed_count = Booking.query.filter_by(customer_id=current_user.id, status='COMPLETED').count()
    active_count = Booking.query.filter(
        Booking.customer_id == current_user.id,
        Booking.status.in_(['ACCEPTED', 'IN_PROGRESS'])
    ).count()

    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.name.asc()).all()

    return render_template(
        'customer/dashboard.html',
        upcoming_bookings=upcoming_bookings,
        completed_count=completed_count,
        active_count=active_count,
        categories=categories
    )


@customer_bp.route('/profile', methods=['GET', 'POST'])
@customer_required
def profile():
    """Customer profile management."""
    form = CustomerProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.phone = form.phone.data.strip()
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('customer.profile'))
    return render_template('customer/profile.html', form=form)


@customer_bp.route('/categories')
@customer_required
def categories():
    """Browse all available service categories."""
    all_categories = ServiceCategory.query.filter_by(is_active=True).all()
    return render_template('customer/categories.html', categories=all_categories)


@customer_bp.route('/categories/<slug>')
@customer_required
def category_providers(slug):
    """
    Lists ONLY APPROVED service providers offering the specified category.
    Includes sorting (price, rating, area/pincode) and filtering options.
    """
    category = ServiceCategory.query.filter_by(slug=slug, is_active=True).first_or_404()
    
    # Query ONLY approved and active providers
    query = ProviderProfile.query.join(User, ProviderProfile.user_id == User.id)\
        .join(ProviderService, ProviderProfile.id == ProviderService.provider_profile_id)\
        .filter(
            ProviderProfile.verification_status == 'APPROVED',
            User.is_active.is_(True),
            User.is_suspended.is_(False),
            ProviderService.category_id == category.id
        )

    # Filter by availability
    avail_filter = request.args.get('availability')
    if avail_filter in ('AVAILABLE', 'BUSY', 'OFFLINE'):
        query = query.filter(ProviderProfile.availability_status == avail_filter)

    # Filter by minimum rating
    min_rating = request.args.get('min_rating', type=float)
    if min_rating:
        query = query.filter(ProviderProfile.rating_avg >= Decimal(str(min_rating)))

    # Filter / Match by Pincode or Locality
    pincode_query = request.args.get('pincode', '').strip()
    if pincode_query:
        query = query.filter(ProviderProfile.service_pincode.ilike(f"%{pincode_query}%"))

    # Sorting
    sort_by = request.args.get('sort', 'rating_desc')
    if sort_by == 'price_asc':
        query = query.order_by(ProviderService.custom_price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(ProviderService.custom_price.desc())
    elif sort_by == 'jobs_desc':
        query = query.order_by(ProviderProfile.completed_jobs_count.desc())
    else:  # Default: highest rating
        query = query.order_by(ProviderProfile.rating_avg.desc(), ProviderProfile.completed_jobs_count.desc())

    providers = query.all()

    return render_template(
        'customer/category_providers.html',
        category=category,
        providers=providers,
        sort_by=sort_by,
        pincode_query=pincode_query
    )


@customer_bp.route('/providers/<int:provider_id>')
@customer_required
def provider_detail(provider_id):
    """Public detail page for an approved provider showing ratings, reviews, and services."""
    provider_user = User.query.filter_by(id=provider_id, role='provider').first_or_404()
    profile = provider_user.provider_profile
    if not profile or not profile.is_approved:
        flash('This service provider is currently unavailable.', 'warning')
        return redirect(url_for('customer.categories'))

    reviews = Review.query.filter_by(provider_id=provider_user.id).order_by(Review.created_at.desc()).limit(10).all()
    services = ProviderService.query.filter_by(provider_profile_id=profile.id).all()

    return render_template(
        'customer/provider_detail.html',
        provider=provider_user,
        profile=profile,
        reviews=reviews,
        services=services
    )


@customer_bp.route('/book/<int:provider_id>', methods=['GET', 'POST'])
@customer_required
def book_service(provider_id):
    """
    Creates a booking for an approved provider.
    Supports up to 30 days scheduling, slot selection, and instructions.
    """
    provider_user = User.query.filter_by(id=provider_id, role='provider').first_or_404()
    profile = provider_user.provider_profile
    if not profile or not profile.is_approved:
        flash('Provider is not approved to accept bookings.', 'danger')
        return redirect(url_for('customer.categories'))

    # Available services for this provider
    available_services = ProviderService.query.filter_by(provider_profile_id=profile.id).all()
    if not available_services:
        flash('This provider has not configured any service offerings yet.', 'warning')
        return redirect(url_for('customer.provider_detail', provider_id=provider_id))

    # Pre-select category if passed in query param
    cat_id = request.args.get('category_id', type=int) or available_services[0].category_id

    form = BookingCreateForm()
    form.provider_id.data = str(provider_id)
    form.category_id.data = str(cat_id)

    if form.validate_on_submit():
        try:
            booking = BookingService.create_booking(
                customer=current_user,
                provider=provider_user,
                category_id=int(form.category_id.data),
                scheduled_date=form.scheduled_date.data,
                time_slot=form.scheduled_time_slot.data,
                address=form.service_address.data.strip(),
                pincode=form.pincode.data.strip(),
                special_instructions=form.special_instructions.data.strip() if form.special_instructions.data else None
            )
            flash(f'Booking #{booking.booking_code} requested successfully! The provider has 5 minutes to accept.', 'success')
            return redirect(url_for('customer.booking_detail', booking_id=booking.id))
        except (ValueError, DoubleBookingError) as e:
            flash(str(e), 'danger')

    # Selected category object
    selected_category = db.session.get(ServiceCategory, cat_id)

    return render_template(
        'customer/book.html',
        form=form,
        provider=provider_user,
        profile=profile,
        services=available_services,
        selected_category=selected_category
    )


@customer_bp.route('/bookings')
@customer_required
def bookings():
    """Customer booking lists categorized into tabs (Upcoming, Completed, Cancelled)."""
    BookingService.check_and_expire_pending_bookings()

    status_filter = request.args.get('tab', 'upcoming')
    query = Booking.query.filter_by(customer_id=current_user.id)

    if status_filter == 'active':
        query = query.filter(Booking.status.in_(['ACCEPTED', 'IN_PROGRESS', 'RESCHEDULED']))
    elif status_filter == 'completed':
        query = query.filter(Booking.status == 'COMPLETED')
    elif status_filter == 'cancelled':
        query = query.filter(Booking.status.in_(['CANCELLED', 'REJECTED']))
    else:  # 'upcoming'
        query = query.filter(Booking.status.in_(['PENDING', 'ACCEPTED', 'RESCHEDULED', 'IN_PROGRESS']))

    booking_list = query.order_by(Booking.scheduled_date.desc(), Booking.created_at.desc()).all()

    return render_template(
        'customer/bookings.html',
        bookings=booking_list,
        current_tab=status_filter
    )


@customer_bp.route('/bookings/<int:booking_id>')
@customer_required
def booking_detail(booking_id):
    """Detailed booking view with status history, tracking simulation, actions, and review/complaint options."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    
    # Calculate if complaint window is open (SRS 4.7.3: within 7 days of completion)
    complaint_window_open = False
    if booking.status == 'COMPLETED':
        history_completed = next((h for h in booking.status_history if h.new_status == 'COMPLETED'), None)
        comp_date = history_completed.created_at if history_completed else booking.updated_at
        now = datetime.now(timezone.utc)
        comp_date_utc = comp_date.replace(tzinfo=timezone.utc) if comp_date.tzinfo is None else comp_date
        complaint_window_open = (now - comp_date_utc) <= timedelta(days=7)

    reschedule_form = RescheduleRequestForm()
    review_form = ReviewForm()
    complaint_form = ComplaintForm()

    return render_template(
        'customer/booking_detail.html',
        booking=booking,
        complaint_window_open=complaint_window_open,
        reschedule_form=reschedule_form,
        review_form=review_form,
        complaint_form=complaint_form
    )


@customer_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@customer_required
def cancel_booking(booking_id):
    """Cancels a booking with fee calculation rules (SRS 5.5)."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    reason = request.form.get('cancellation_reason', 'Cancelled by customer')

    try:
        BookingService.cancel_booking(booking=booking, cancelled_by=current_user, reason=reason)
        if booking.cancellation_fee > 0:
            flash(f'Booking #{booking.booking_code} cancelled. A late cancellation fee of ₹{booking.cancellation_fee} has been recorded per policy.', 'warning')
        else:
            flash(f'Booking #{booking.booking_code} cancelled successfully at no charge.', 'info')
    except (BookingTransitionError, ValueError) as e:
        flash(str(e), 'danger')

    return redirect(url_for('customer.booking_detail', booking_id=booking.id))


@customer_bp.route('/bookings/<int:booking_id>/reschedule', methods=['POST'])
@customer_required
def request_reschedule(booking_id):
    """Customer submits a reschedule proposal."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    form = RescheduleRequestForm()

    if form.validate_on_submit():
        try:
            BookingService.request_reschedule(
                booking=booking,
                requested_by=current_user,
                proposed_date=form.proposed_date.data,
                proposed_slot=form.proposed_time_slot.data
            )
            flash('Reschedule request sent to service provider for approval.', 'success')
        except (BookingTransitionError, DoubleBookingError, ValueError) as e:
            flash(str(e), 'danger')
    else:
        flash('Invalid date or time slot submitted for reschedule.', 'danger')

    return redirect(url_for('customer.booking_detail', booking_id=booking.id))


@customer_bp.route('/bookings/<int:booking_id>/reschedule-respond', methods=['POST'])
@customer_required
def respond_reschedule(booking_id):
    """Customer accepts or declines a reschedule proposed by the provider."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    action = request.form.get('action')  # 'accept' or 'decline'

    try:
        BookingService.respond_to_reschedule(
            booking=booking,
            responding_user=current_user,
            accept=(action == 'accept')
        )
        if action == 'accept':
            flash('Reschedule accepted! Your new appointment is confirmed.', 'success')
        else:
            flash('Reschedule declined. The original schedule remains in place.', 'info')
    except BookingTransitionError as e:
        flash(str(e), 'danger')

    return redirect(url_for('customer.booking_detail', booking_id=booking.id))


@customer_bp.route('/bookings/<int:booking_id>/book-again')
@customer_required
def book_again(booking_id):
    """SRS 4.10: One-click rebooking with the same provider and service."""
    past_booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    return redirect(url_for(
        'customer.book_service',
        provider_id=past_booking.provider_id,
        category_id=past_booking.category_id
    ))


@customer_bp.route('/bookings/<int:booking_id>/review', methods=['POST'])
@customer_required
def submit_review(booking_id):
    """Submits 1-to-5 star rating and comment for a completed job (SRS 4.7)."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    
    if booking.status != 'COMPLETED':
        flash('You can only review completed jobs.', 'warning')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))

    if booking.review:
        flash('You have already submitted a review for this booking.', 'info')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))

    form = ReviewForm()
    if form.validate_on_submit():
        rating = int(form.rating.data)
        comment = form.comment.data.strip() if form.comment.data else None

        review = Review(
            booking_id=booking.id,
            customer_id=current_user.id,
            provider_id=booking.provider_id,
            provider_profile_id=booking.provider.provider_profile.id,
            rating=rating,
            comment=comment
        )
        db.session.add(review)
        db.session.commit()

        # Recalculate provider average rating and trigger auto-flagging if necessary
        booking.provider.provider_profile.update_rating_stats()

        flash('Thank you for rating your service experience!', 'success')
    else:
        flash('Invalid rating submitted.', 'danger')

    return redirect(url_for('customer.booking_detail', booking_id=booking.id))


@customer_bp.route('/bookings/<int:booking_id>/complaint', methods=['POST'])
@customer_required
def file_complaint(booking_id):
    """Files a dispute complaint within 7 days of job completion (SRS 4.7.3)."""
    booking = Booking.query.filter_by(id=booking_id, customer_id=current_user.id).first_or_404()
    
    if booking.status != 'COMPLETED':
        flash('Complaints can only be filed against completed jobs.', 'warning')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))

    if booking.completed_at:
        comp_time = booking.completed_at if booking.completed_at.tzinfo else booking.completed_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - comp_time).total_seconds() > 7 * 86400:
            flash('Complaints can only be filed within 7 days of job completion.', 'warning')
            return redirect(url_for('customer.booking_detail', booking_id=booking.id))

    form = ComplaintForm()
    if form.validate_on_submit():
        photo_filename = None
        if form.photo.data:
            file = form.photo.data
            ext = secure_filename(file.filename).rsplit('.', 1)[-1].lower()
            photo_filename = f"cmp_{booking.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{ext}"
            complaints_folder = current_app.config.get('COMPLAINTS_FOLDER')
            os.makedirs(complaints_folder, exist_ok=True)
            file.save(os.path.join(complaints_folder, photo_filename))

        complaint = Complaint(
            ticket_number=Complaint.generate_ticket_number(),
            booking_id=booking.id,
            customer_id=current_user.id,
            subject=form.subject.data.strip(),
            description=form.description.data.strip(),
            photo_filename=photo_filename,
            status='OPEN'
        )
        db.session.add(complaint)
        db.session.commit()

        flash(f'Complaint ticket #{complaint.ticket_number} lodged successfully. An administrator will review your case.', 'success')
        return redirect(url_for('customer.complaints'))
    else:
        flash('Please fill in all required complaint fields.', 'danger')
        return redirect(url_for('customer.booking_detail', booking_id=booking.id))


@customer_bp.route('/complaints')
@customer_required
def complaints():
    """Lists all complaints filed by the customer."""
    all_complaints = Complaint.query.filter_by(customer_id=current_user.id).order_by(Complaint.created_at.desc()).all()
    return render_template('customer/complaints.html', complaints=all_complaints)


@customer_bp.route('/invoices/<int:invoice_id>')
@customer_required
def invoice_detail(invoice_id):
    """HTML digital invoice view."""
    invoice = Invoice.query.filter_by(id=invoice_id).first_or_404()
    if invoice.booking.customer_id != current_user.id and not current_user.is_admin:
        abort(403)
    return render_template('customer/invoice.html', invoice=invoice)


@customer_bp.route('/invoices/<int:invoice_id>/pdf')
@customer_required
def invoice_pdf(invoice_id):
    """Download official PDF invoice."""
    invoice = Invoice.query.filter_by(id=invoice_id).first_or_404()
    if invoice.booking.customer_id != current_user.id and not current_user.is_admin:
        abort(403)
    
    pdf_buffer = InvoiceService.generate_pdf_invoice(invoice)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{invoice.invoice_number}.pdf"
    )


@customer_bp.route('/notifications')
@customer_required
def notifications():
    """In-app notifications inbox with promotional toggle."""
    filter_promo = request.args.get('show_promo', '1') == '1'
    query = Notification.query.filter_by(user_id=current_user.id)
    if not filter_promo:
        query = query.filter_by(is_promotional=False)
    
    notifs = query.order_by(Notification.created_at.desc()).all()

    # Mark all currently unread notifications as read
    for n in notifs:
        if not n.is_read:
            n.is_read = True
    db.session.commit()

    return render_template(
        'customer/notifications.html',
        notifications=notifs,
        filter_promo=filter_promo
    )
