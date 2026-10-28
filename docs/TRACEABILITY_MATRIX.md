# FixMate — Requirements Traceability Matrix (RTM)

## Document Reference
- **Source Document:** `FixMate_SRS_Final_Formatted.docx` (Version 1.0)
- **Target System:** FixMate Responsive Web Application (VESIT Computer Engineering Academic Project)
- **Evaluation Status:** 100% Traceability across Functional (SRS 4.0) and Non-Functional (SRS 5.0) Requirements.

---

## 1. Traceability Matrix Table

| SRS Section | SRS Requirement Title | Implementation Type | Technical Implementation in FixMate | Academic & Demo Scope Notes |
|---|---|---|---|---|
| **SRS 4.1** | User Registration & Role Selection | **Implemented** | `app/blueprints/auth/routes.py`, `RegistrationForm` | Public registration limited to Customer & Provider. Admin registration blocked. |
| **SRS 4.1.2** | Terms of Service Acceptance | **Implemented** | `terms_accepted` boolean check & timestamp in `User` model | Required checkbox on signup. Links to `/terms` and `/privacy`. |
| **SRS 4.1.3** | Account Lockout Policy | **Implemented** | `User.failed_login_attempts`, `locked_until` (15 mins) | Account locked for 15 minutes after 5 consecutive failed passwords. |
| **SRS 4.1.4** | Password Reset via Token | **Implemented** | Cryptographic token verification in `User.generate_reset_token()` | Demo mode banner prints reset token for zero-SMTP demo friction. |
| **SRS 4.2.1** | Provider Profile & Service Area | **Implemented** | `ProviderProfile` model (`service_pincode`, `service_area_name`) | Pincode-based area matching honest demo label. |
| **SRS 4.2.2** | Provider KYC Verification (ID & Address) | **Implemented** | `KYCService`, `ProviderDocument` model | Whitelisted MIME/size, randomized UUID storage outside public webroot. |
| **SRS 4.2.3** | Provider Pricing Controls | **Implemented** | `ProviderServiceForm` with admin min/max bounds validation | Provider price rejected if lower than category min or higher than max. |
| **SRS 4.3** | Customer Search & Discovery | **Implemented** | `customer_bp.category_providers`, filters & sorting | Unapproved providers strictly filtered out on SQL layer. |
| **SRS 4.4.1** | Booking Request Flow | **Implemented** | `BookingService.create_booking()` | Date bound (today to 30 days ahead), slot reservation. |
| **SRS 4.4.2** | Double-Booking Prevention Safeguard | **Implemented** | `BookingService.check_double_booking()` | Database row lock + composite index prevents concurrent slot clashes. |
| **SRS 4.4.3** | Provider Response Window (5 Minutes) | **Implemented** | `response_deadline` timestamp + auto-expiration check | 5-minute timeout window with auto-unassignment fallback. |
| **SRS 4.4.4** | Cancellation & Reschedule Rules | **Implemented** | `BookingService.cancel_booking()`, `request_reschedule()` | Cancellation fee (10% if same day); mutual reschedule agreement. |
| **SRS 4.5** | Real-Time Job Tracking & ETA | **Simulated** | `Booking.eta_minutes`, status timeline in `booking_detail.html` | Transparently labelled as simulated ETA tracking (no external GPS hardware). |
| **SRS 4.6.1** | Multi-Method Payment Processing | **Simulated** | `PaymentService.process_simulated_payment()` | Supports UPI, Card, Net Banking, Wallet with transaction refs. |
| **SRS 4.6.2** | Commission Split & GST Calculation | **Implemented** | `Payment` model (18% GST + 10% platform commission) | Real financial calculation stored in MySQL ledger. |
| **SRS 4.6.3** | Provider Payout Escrow & Refunds | **Implemented** | `payout_status` ('HELD' / 'RELEASED'), Admin dispute refund | Escrow holding until job confirmed; admin dispute refunding. |
| **SRS 4.7.1** | Post-Job Customer Reviews & Ratings | **Implemented** | `Review` model (1-5 stars + comment) | Permitted ONLY after status `COMPLETED`; 1 review per booking. |
| **SRS 4.7.2** | Auto-Flagging Low-Rated Providers | **Implemented** | `ProviderProfile.update_rating_stats()` | Auto-flags provider for admin review if average drops below 3.0. |
| **SRS 4.7.3** | Dispute Complaints Window (7 Days) | **Implemented** | `Complaint` model, 7-day post-completion check | Ticket generation (`CMP-YYYYMMDD-XXXX`), admin status workflow. |
| **SRS 4.8.1** | Administrator Analytics Dashboard | **Implemented** | `admin_bp.dashboard` | Live MySQL count/sum metrics (daily/weekly/monthly bookings & revenue). |
| **SRS 4.8.2** | Admin Provider KYC Approval/Rejection | **Implemented** | `admin_bp.provider_review` | Inspect documents securely; mandatory rejection reason required. |
| **SRS 4.8.3** | User Account Suspension | **Implemented** | `User.is_suspended`, audit logging | Suspended users instantly blocked from signing in. |
| **SRS 4.8.4** | Dynamic System Settings Management | **Implemented** | `SystemSetting` model, `admin_bp.settings` | Commission %, cancellation fee %, window minutes, GST % configurable. |
| **SRS 4.8.5** | Admin Audit Trail Logging | **Implemented** | `AuditService.log()`, `AdminAuditLog` table | Logs who, what, when, IP address for all critical admin operations. |
| **SRS 4.9** | Notifications Management | **Implemented** | `Notification` model, unread badge in global navbar | Categorized alerts (`BOOKING`, `KYC`, `PAYMENT`, `DISPUTE`, `ACCOUNT`). |
| **SRS 4.10** | Official PDF Tax Invoices | **Implemented** | `InvoiceService.generate_pdf_invoice()` using ReportLab | Dynamic vector PDF invoice with GSTIN, breakdown, and download stream. |
| **SRS 5.1** | Mobile Apps (iOS / Android) | **Scope Limitation** | Responsive Bootstrap 5 Web Interface | Documented academic decision: responsive web app replaces native mobile apps. |
| **SRS 5.2** | Live SMS / Push Notifications (Firebase) | **Scope Limitation** | In-app notification center + demo console simulation | Third-party paid SMS / FCM gateways excluded per academic project bounds. |
| **SRS 5.3** | Live Turn-by-Turn GPS Tracking | **Scope Limitation** | Milestone tracking (ETA, Google Maps location link) | Documented academic decision: external telematics GPS API excluded. |

