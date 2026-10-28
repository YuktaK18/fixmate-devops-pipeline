# FixMate — Viva & Project Defense Guide (25+ Questions & Answers)

> **Student Guide (Yukta Karwa, VESIT):** These questions are curated based on standard Computer Engineering final year / semester viva panels. Read and understand these concise answers before your presentation.

---

### Q1. What is the core problem FixMate solves?
**Answer:** The unorganized home services sector suffers from opaque pricing, unverified technicians, lack of scheduling reliability, and absence of formal dispute mechanisms. FixMate provides a structured platform with mandatory KYC verification, admin-governed pricing boundaries, double-booking prevention, automated commission/tax calculations, and time-bound dispute arbitration.

---

### Q2. Why did you choose Python Flask instead of Django or Node.js/React?
**Answer:** 
1. Flask's lightweight, micro-framework architecture allows explicit design using modular Blueprints (`auth`, `customer`, `provider`, `admin`, `payments`), avoiding the unnecessary boilerplate of Django.
2. Building with Flask, Jinja2, and Bootstrap 5 keeps the frontend server-rendered without the overhead of client-side React hydration or Node runtime dependencies.
3. It integrates cleanly with SQLAlchemy ORM and Flask-Migrate for normalized MySQL database operations.

---

### Q3. Explain the architecture of your application.
**Answer:** FixMate follows a classic 3-Tier Architecture:
1. **Presentation Tier:** Responsive Bootstrap 5 HTML5 templates rendered via Jinja2 with role-specific navigation and vanilla JavaScript.
2. **Application Tier:** Python Flask with an Application Factory (`create_app`), modular Blueprints, and an encapsulated **Service Layer** (`BookingService`, `PaymentService`, `KYCService`, `InvoiceService`, `AuditService`).
3. **Data Tier:** Normalized MySQL Server 26.7 running on port 3307 with 14 relational tables in Third Normal Form (3NF).

---

### Q4. How do you prevent double-booking for the same provider and time slot?
**Answer:** We prevent double-booking using a two-layer safeguard:
1. **Application / Transaction Layer:** In `BookingService.create_booking()`, we query active bookings (`PENDING`, `ACCEPTED`, `IN_PROGRESS`, `RESCHEDULED`) for that provider, date, and slot using database row-level locking (`with_for_update()`). If an active booking exists, a `DoubleBookingError` is raised.
2. **Database Layer:** A composite index on `(provider_id, scheduled_date, scheduled_time_slot)` ensures fast lookup and physical enforcement.

---

### Q5. What is the Booking State Machine and why is it important?
**Answer:** The booking lifecycle moves through distinct states: `PENDING` → `ACCEPTED` → `IN_PROGRESS` → `COMPLETED` (or `REJECTED`, `CANCELLED`, `RESCHEDULED`). We implemented an explicit transition dictionary in `BookingService.ALLOWED_TRANSITIONS`. If anyone attempts an illegal jump (e.g., trying to mark a `PENDING` booking as `COMPLETED` or cancelling a finished job), the system throws a `BookingTransitionError` and rolls back the transaction.

---

### Q6. How does your KYC document verification system ensure security?
**Answer:**
1. **Storage Location:** Files are stored in `var/uploads/documents`, completely outside the public `app/static/` directory so they cannot be accessed directly via URL.
2. **File Sanitization:** Uploaded files are validated against allowed MIME types (`application/pdf`, `image/png`, `image/jpeg`) and a 5 MB file size limit. The filename is replaced with a randomized UUID4 hex token to prevent directory traversal or name collision attacks.
3. **Access Control:** Documents can only be viewed via a protected route (`/admin/documents/<id>`) guarded by `@admin_required` or the document owner.

---

### Q7. How does the 5-minute provider response window work?
**Answer:** When a booking is submitted, `response_deadline` is calculated as `now() + 5 minutes`. When a provider opens their dashboard or attempts to accept, the backend evaluates `booking.has_expired_window`. If expired, the booking is automatically marked `UNASSIGNED` and offered to the next available provider, or cancelled safely.

---

### Q8. What is the cancellation policy and fee calculation?
**Answer:**
- If a customer cancels while the booking is `PENDING`: Fee is ₹0.00.
- If a customer cancels an `ACCEPTED` booking on the scheduled day: A 10% cancellation fee is calculated against the quoted price and recorded.

---

### Q9. Explain your payment flow. Why is it simulated?
**Answer:** In an academic environment, real payment gateways (Razorpay, Stripe) require commercial business documentation and live banking credentials. We implemented a realistic **Simulated Payment Engine**:
- The customer selects UPI, Card, Net Banking, or Wallet.
- The engine calculates the financial split: Base Service Amount + 18% GST = Total Payable.
- It deducts a 10% platform commission and places the remaining payout into an **escrow** (`payout_status = 'HELD'`) until the service is confirmed or 24 hours elapse.
- A unique transaction reference (`TXN-YYYYMMDD-HEX`) is generated and an official tax invoice is created.

---

### Q10. How are official PDF invoices generated?
**Answer:** We use the Python **ReportLab** library in `InvoiceService.generate_pdf_invoice()`. It programmatically builds a two-page capable vector PDF in memory (`io.BytesIO`) containing the FixMate company header, GST registration number, customer address, provider details, itemized base charge, 18% GST breakdown, and transaction reference, streamed directly to the customer's browser.

---

### Q11. How do you protect user passwords?
**Answer:** Passwords are never stored in plain text. We use `werkzeug.security.generate_password_hash()` which employs the **Scrypt / PBKDF2 with SHA-256** key derivation function with unique cryptographic salt. Authentication is verified using constant-time comparison `check_password_hash()` to prevent timing attacks.

---

### Q12. How does the 5-strike account lockout mechanism work?
**Answer:** In compliance with SRS 4.1.3, each failed login attempt increments `User.failed_login_attempts`. Upon the 5th consecutive failure, `User.locked_until` is set to `now() + 15 minutes`. Any subsequent login attempt during this window is blocked, even if the correct password is provided, mitigating brute-force dictionary attacks.

---

### Q13. How is CSRF (Cross-Site Request Forgery) mitigated?
**Answer:** We use **Flask-WTF** CSRF protection. Every form includes `{{ form.csrf_token }}` or `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. When a POST request is submitted, Flask-WTF validates that the token matches the user's encrypted session cookie.

---

### Q14. What are the roles in your system and how is authorization enforced?
**Answer:** We have three distinct roles: `customer`, `provider`, and `admin`. We enforce access via custom Python decorators in `app/utils/decorators.py`:
- `@customer_required`: Blocks non-customers.
- `@provider_required`: Blocks non-providers.
- `@approved_provider_required`: Blocks providers whose verification is still `PENDING` or `REJECTED`.
- `@admin_required`: Restricts sensitive operations exclusively to administrators (returns HTTP 403 Forbidden).

---

### Q15. Can a public user register as an Admin?
**Answer:** No. In `RegistrationForm` and `auth_bp.register`, the role choices are strictly limited to `customer` and `provider`. The initial administrator can only be provisioned via the secure CLI command:
```bash
flask create-admin
```
which reads credentials interactively from the terminal or `.env`.

---

### Q16. How does provider rating and auto-flagging work?
**Answer:** Customers can submit a 1 to 5 star review only after a booking is marked `COMPLETED` (limited to 1 review per booking). When a review is posted, `ProviderProfile.update_rating_stats()` recalculates the average rating and completed job count. If the provider's average drops below 3.0, the backend sets `is_flagged_for_review = True`, generating an alert on the admin dashboard.

---

### Q17. How is the 7-day dispute window enforced?
**Answer:** In `customer_bp.file_complaint`, the backend checks `(now() - booking.completed_at).days <= 7`. If more than 7 days have elapsed since job completion, the complaint submission is rejected.

---

### Q18. What is the Admin Audit Trail?
**Answer:** Every critical administrative intervention (approving a provider, rejecting KYC, updating platform commission, suspending a user account, resolving a dispute, or issuing a refund) is logged to the `admin_audit_logs` table via `AuditService.log()`. It records the admin ID, action enum, target entity ID, IP address, and timestamp.

---

### Q19. How do you handle database migrations?
**Answer:** We use **Flask-Migrate** (built on **Alembic**). Instead of dropping tables and losing data, schema changes are tracked in version-controlled migration scripts in `migrations/versions/`. Migrations are applied using `flask db upgrade`.

---

### Q20. What database constraints did you configure in SQLAlchemy?
**Answer:**
1. `ondelete='CASCADE'` on dependent child records (such as deleting services when a profile is removed).
2. `unique=True` on emails, phone numbers, booking codes, and invoice numbers.
3. `index=True` on frequently filtered fields (`status`, `scheduled_date`, `pincode`, `email`).
4. Strict `db.Enum` types for statuses (`verification_status`, `booking_status`, `payment_method`, etc.).

---

### Q21. How do you test your code?
**Answer:** We use **pytest** with the Flask test client and an isolated test database (`fixmate_test_db`). Our test suite contains **35 automated test cases** covering:
- Authentication, registration, and 5-strike lockouts (`test_auth.py`).
- KYC upload sanitization and admin approval/rejection (`test_provider_kyc.py`).
- Double booking prevention, state machine transitions, and rescheduling (`test_booking_workflow.py`).
- 18% GST splits, commission deductions, and ReportLab PDF invoice generation (`test_payments_invoices.py`).
- Review constraints, rating recalculations, and 7-day dispute complaints (`test_reviews_complaints.py`).
- Admin analytics, category price limits, user suspension, and audit logs (`test_admin_and_audit.py`).
All 35 tests pass with a 100% success rate against live MySQL.

---

### Q22. What happens if the provider rejects a booking request?
**Answer:** The booking status transitions to `REJECTED`, the slot lock on the provider's schedule is released, and an in-app notification is sent to the customer so they can choose another provider.

---

### Q23. Why did you isolate MySQL to port 3307 instead of default 3306?
**Answer:** Windows development machines frequently have conflicting MySQL services or unknown root passwords. To guarantee isolation and zero data contamination, we initialized a dedicated, self-contained MySQL 26.7 instance with custom configuration (`var/my_fixmate.ini`) bound to `127.0.0.1:3307`.

---

### Q24. What are the key limitations of your current implementation?
**Answer:**
1. Live GPS turn-by-turn tracking is simulated with ETA milestones rather than live telematics.
2. Payment is simulated in Demo Mode rather than connected to live bank APIs.
3. SMS and Push Notifications are simulated via in-app notifications and console logging rather than paid Twilio/Firebase gateways.
These are documented in our Scope & Limitations section as appropriate for an academic capstone.

---

### Q25. What would be the next steps to take this to production?
**Answer:**
1. Containerize the application with Docker and Docker Compose.
2. Integrate Razorpay / Stripe live webhook listeners.
3. Deploy behind Nginx with Gunicorn workers on an AWS EC2 instance with automated Let's Encrypt SSL/TLS certificates.
4. Set up Celery with Redis for asynchronous background tasks (such as sending emails and scheduled cron jobs).

