import os
import sys
from decimal import Decimal
from datetime import datetime, timezone, timedelta, date

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.provider import ProviderProfile, ProviderDocument
from app.models.service import ServiceCategory, ProviderService
from app.models.booking import Booking, BookingStatusHistory
from app.models.payment import Payment, Invoice
from app.models.review import Review
from app.models.complaint import Complaint
from app.models.notification import Notification
from app.models.settings import SystemSetting
from app.services.payment_service import PaymentService


def seed_all():
    """Seeds database idempotently with realistic production-ready demo data."""
    print("Starting FixMate database seeding...")

    # 1. System Settings Defaults
    SystemSetting.set_value('commission_percentage', '10.0', 'Platform Commission percentage deducted from provider payment')
    SystemSetting.set_value('cancellation_fee_percentage', '10.0', 'Cancellation penalty fee percentage for late customer cancellation')
    SystemSetting.set_value('cancellation_window_minutes', '15', 'Penalty time window in minutes prior to scheduled slot')
    SystemSetting.set_value('gst_percentage', '18.0', 'Standard Goods & Services Tax percentage')

    # 2. Service Categories (8 realistic categories per SRS)
    categories_data = [
        {
            'name': 'Plumbing Services',
            'slug': 'plumbing',
            'description': 'Tap repairs, drain cleaning, pipeline leaks, water tank fittings & bathroom fixtures.',
            'icon': 'bi-droplet-half',
            'min': Decimal('199.00'),
            'max': Decimal('3000.00'),
        },
        {
            'name': 'Electrical Repairs',
            'slug': 'electrical',
            'description': 'Short-circuit fixes, switchboard repairs, wiring installation, lighting & fan setups.',
            'icon': 'bi-lightning-charge',
            'min': Decimal('199.00'),
            'max': Decimal('3500.00'),
        },
        {
            'name': 'Carpentry & Woodwork',
            'slug': 'carpentry',
            'description': 'Door hinge repairs, wooden furniture assembly, lock replacement & custom cabinetry.',
            'icon': 'bi-hammer',
            'min': Decimal('299.00'),
            'max': Decimal('5000.00'),
        },
        {
            'name': 'House Painting',
            'slug': 'painting',
            'description': 'Interior & exterior wall painting, waterproof coating, touch-ups & texture designs.',
            'icon': 'bi-paint-bucket',
            'min': Decimal('499.00'),
            'max': Decimal('12000.00'),
        },
        {
            'name': 'Home Deep Cleaning',
            'slug': 'cleaning',
            'description': 'Full home deep sanitization, kitchen & bathroom degreasing, sofa & carpet shampooing.',
            'icon': 'bi-stars',
            'min': Decimal('399.00'),
            'max': Decimal('7500.00'),
        },
        {
            'name': 'Appliance Repair',
            'slug': 'appliance-repair',
            'description': 'Washing machine repair, refrigerator diagnostics, microwave & TV wall-mounting.',
            'icon': 'bi-cpu',
            'min': Decimal('249.00'),
            'max': Decimal('4500.00'),
        },
        {
            'name': 'Pest Control',
            'slug': 'pest-control',
            'description': 'Herbal pest management, cockroach gel treatment, termite control & bedbug removal.',
            'icon': 'bi-bug',
            'min': Decimal('399.00'),
            'max': Decimal('5000.00'),
        },
        {
            'name': 'AC Service & Repair',
            'slug': 'ac-service',
            'description': 'Split & window AC jet wash, refrigerant gas refill, PCB repair & installation.',
            'icon': 'bi-snow',
            'min': Decimal('299.00'),
            'max': Decimal('5500.00'),
        },
    ]

    categories_map = {}
    for cat_info in categories_data:
        cat = ServiceCategory.query.filter_by(slug=cat_info['slug']).first()
        if not cat:
            cat = ServiceCategory(
                name=cat_info['name'],
                slug=cat_info['slug'],
                description=cat_info['description'],
                icon=cat_info['icon'],
                min_base_price=cat_info['min'],
                max_base_price=cat_info['max'],
                is_active=True
            )
            db.session.add(cat)
            db.session.flush()
        categories_map[cat.slug] = cat

    # 3. Super Administrator
    admin_email = os.getenv('FIRST_ADMIN_EMAIL', 'admin@fixmate.local')
    admin_user = User.query.filter_by(email=admin_email).first()
    if not admin_user:
        admin_user = User(
            name=os.getenv('FIRST_ADMIN_NAME', 'Yukta Admin'),
            email=admin_email,
            phone='9876543210',
            role='admin',
            terms_accepted=True,
            terms_accepted_at=datetime.now(timezone.utc)
        )
        admin_user.set_password(os.getenv('FIRST_ADMIN_PASSWORD', 'Admin@FixMate2026!'))
        db.session.add(admin_user)
        db.session.flush()

    # 4. Sample Customers
    customers_data = [
        {
            'name': 'Rahul Sharma',
            'email': 'rahul@fixmate.local',
            'phone': '9820011111',
            'pass': 'Customer@123'
        },
        {
            'name': 'Priya Patel',
            'email': 'priya@fixmate.local',
            'phone': '9820022222',
            'pass': 'Customer@123'
        }
    ]
    customers_map = {}
    for c_info in customers_data:
        cust = User.query.filter_by(email=c_info['email']).first()
        if not cust:
            cust = User(
                name=c_info['name'],
                email=c_info['email'],
                phone=c_info['phone'],
                role='customer',
                terms_accepted=True
            )
            cust.set_password(c_info['pass'])
            db.session.add(cust)
            db.session.flush()
        customers_map[cust.email] = cust

    # 5. Sample Providers
    providers_data = [
        {
            'name': 'Ramesh Verma',
            'email': 'ramesh.plumber@fixmate.local',
            'phone': '9820033333',
            'pass': 'Provider@123',
            'status': 'APPROVED',
            'pincode': '400071',
            'area': 'Chembur, Mumbai',
            'bio': 'Certified master plumber with 7+ years of experience in high-rise plumbing and leakage repair.',
            'exp': 7,
            'rating': Decimal('4.85'),
            'jobs': 24,
            'cat_slug': 'plumbing',
            'rate': Decimal('349.00')
        },
        {
            'name': 'Suresh Patil',
            'email': 'suresh.electric@fixmate.local',
            'phone': '9820044444',
            'pass': 'Provider@123',
            'status': 'APPROVED',
            'pincode': '400022',
            'area': 'Sion / Chunabhatti',
            'bio': 'Licensed electrician specialized in domestic wiring, smart lighting, and fuse box replacements.',
            'exp': 9,
            'rating': Decimal('4.90'),
            'jobs': 38,
            'cat_slug': 'electrical',
            'rate': Decimal('299.00')
        },
        {
            'name': 'Amit Kumar',
            'email': 'amit.carpenter@fixmate.local',
            'phone': '9820055555',
            'pass': 'Provider@123',
            'status': 'APPROVED',
            'pincode': '400077',
            'area': 'Ghatkopar East',
            'bio': 'Skilled carpenter with fine woodwork, modular kitchen installation, and lock repair expertise.',
            'exp': 5,
            'rating': Decimal('4.70'),
            'jobs': 15,
            'cat_slug': 'carpentry',
            'rate': Decimal('449.00')
        },
        {
            'name': 'Sunita Shinde',
            'email': 'sunita.clean@fixmate.local',
            'phone': '9820066666',
            'pass': 'Provider@123',
            'status': 'APPROVED',
            'pincode': '400071',
            'area': 'Chembur / Kurla',
            'bio': 'Professional deep cleaner leading a dedicated team using eco-friendly European cleaning agents.',
            'exp': 4,
            'rating': Decimal('4.60'),
            'jobs': 19,
            'cat_slug': 'cleaning',
            'rate': Decimal('699.00')
        },
        {
            'name': 'Vikas Jadhav',
            'email': 'vikas.appliance@fixmate.local',
            'phone': '9820077777',
            'pass': 'Provider@123',
            'status': 'PENDING',
            'pincode': '400074',
            'area': 'Chembur East',
            'bio': 'Technician experienced with all major refrigerator and microwave brands.',
            'exp': 3,
            'rating': Decimal('0.00'),
            'jobs': 0,
            'cat_slug': 'appliance-repair',
            'rate': Decimal('399.00')
        },
        {
            'name': 'Rajesh Badkar',
            'email': 'rajesh.flagged@fixmate.local',
            'phone': '9820088888',
            'pass': 'Provider@123',
            'status': 'APPROVED',
            'pincode': '400071',
            'area': 'Tilak Nagar, Chembur',
            'bio': 'General handyman and painter.',
            'exp': 2,
            'rating': Decimal('2.40'),
            'jobs': 5,
            'cat_slug': 'painting',
            'rate': Decimal('599.00'),
            'flagged': True,
            'flag_reason': 'Average rating dropped to 2.40 (below required 3.0 threshold).'
        }
    ]

    providers_map = {}
    for p_info in providers_data:
        prov = User.query.filter_by(email=p_info['email']).first()
        if not prov:
            prov = User(
                name=p_info['name'],
                email=p_info['email'],
                phone=p_info['phone'],
                role='provider',
                terms_accepted=True
            )
            prov.set_password(p_info['pass'])
            db.session.add(prov)
            db.session.flush()

            profile = ProviderProfile(
                user_id=prov.id,
                bio=p_info['bio'],
                experience_years=p_info['exp'],
                service_pincode=p_info['pincode'],
                service_area_name=p_info['area'],
                service_radius_km=15,
                verification_status=p_info['status'],
                availability_status='AVAILABLE',
                rating_avg=p_info['rating'],
                completed_jobs_count=p_info['jobs'],
                is_flagged_for_review=p_info.get('flagged', False),
                flagged_reason=p_info.get('flag_reason')
            )
            if p_info['status'] == 'APPROVED':
                profile.verified_at = datetime.now(timezone.utc)
                profile.verified_by_admin_id = admin_user.id
            db.session.add(profile)
            db.session.flush()

            # Add Service offering
            cat = categories_map.get(p_info['cat_slug'])
            if cat:
                prov_svc = ProviderService(
                    provider_profile_id=profile.id,
                    category_id=cat.id,
                    custom_price=p_info['rate'],
                    description=f"Standard service inspection and repair by {p_info['name']}."
                )
                db.session.add(prov_svc)

        providers_map[p_info['email']] = prov

    # 6. Sample Bookings & Workflow Instances
    rahul = customers_map['rahul@fixmate.local']
    ramesh = providers_map['ramesh.plumber@fixmate.local']
    suresh = providers_map['suresh.electric@fixmate.local']
    plumbing_cat = categories_map['plumbing']
    electrical_cat = categories_map['electrical']

    # Completed booking with payment & invoice
    completed_booking = Booking.query.filter_by(booking_code='FIX-20261025-SEED01').first()
    if not completed_booking:
        past_date = date.today() - timedelta(days=2)
        completed_booking = Booking(
            booking_code='FIX-20261025-SEED01',
            customer_id=rahul.id,
            provider_id=ramesh.id,
            category_id=plumbing_cat.id,
            scheduled_date=past_date,
            scheduled_time_slot='11:00 - 01:00 PM',
            service_address='Flat 402, Lotus Tower, Collector Colony, Chembur',
            pincode='400074',
            special_instructions='Kitchen sink tap leaking persistently.',
            status='COMPLETED',
            quoted_amount=Decimal('349.00'),
            final_amount=Decimal('349.00')
        )
        db.session.add(completed_booking)
        db.session.flush()

        # Add payment
        payment = PaymentService.process_simulated_payment(
            booking=completed_booking,
            payment_method='UPI'
        )

        # Add customer review
        review = Review(
            booking_id=completed_booking.id,
            customer_id=rahul.id,
            provider_id=ramesh.id,
            provider_profile_id=ramesh.provider_profile.id,
            rating=5,
            comment="Excellent work! Ramesh fixed the leak quickly and was very polite."
        )
        db.session.add(review)

    # Active Accepted booking
    active_booking = Booking.query.filter_by(booking_code='FIX-20261027-SEED02').first()
    if not active_booking:
        today_date = date.today()
        active_booking = Booking(
            booking_code='FIX-20261027-SEED02',
            customer_id=rahul.id,
            provider_id=suresh.id,
            category_id=electrical_cat.id,
            scheduled_date=today_date,
            scheduled_time_slot='04:00 - 06:00 PM',
            service_address='Flat 402, Lotus Tower, Collector Colony, Chembur',
            pincode='400074',
            special_instructions='Master bedroom ceiling fan regulator sparking.',
            status='ACCEPTED',
            quoted_amount=Decimal('299.00')
        )
        db.session.add(active_booking)

    db.session.commit()
    print("Database seeding completed successfully!")
    print(f"Super Admin Login: {admin_email} | Password: {os.getenv('FIRST_ADMIN_PASSWORD', 'Admin@FixMate2026!')}")
    print("Customer Login: rahul@fixmate.local | Password: Customer@123")
    print("Provider Login: ramesh.plumber@fixmate.local | Password: Provider@123")


if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        seed_all()
