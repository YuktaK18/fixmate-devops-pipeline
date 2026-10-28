# FixMate — System Architecture & Design Documentation

## 1. System Overview
**FixMate** is a robust, responsive web-based Home Service Management System built for academic demonstration at **VESIT (Department of Computer Engineering)**. It connects residential customers with verified service professionals (electricians, plumbers, carpenters, technicians) while offering administrative governance over verification, pricing limits, commission collection, and dispute arbitration.

---

## 2. Three-Tier Architectural Pattern

FixMate adheres to a strict 3-tier architectural model:

```mermaid
flowchart TD
    subgraph Presentation_Tier ["Presentation Tier (Client / Browser)"]
        UI_Customer["Customer Portal\n(Bootstrap 5 + Jinja2 Templates)"]
        UI_Provider["Provider Portal\n(Dashboard, KYC Uploads, Job Tracker)"]
        UI_Admin["Admin Operations Portal\n(Analytics, Verification, Dispute Center)"]
        Vanilla_JS["Vanilla JavaScript\n(No React / No Node Dependencies)"]
    end

    subgraph Application_Tier ["Application Tier (Python Flask Backend)"]
        WSGI["WSGI Gateway / Gunicorn / Flask Development Server"]
        AppFactory["Flask Application Factory (create_app)"]
        
        subgraph Blueprints ["Modular Blueprints"]
            BP_Auth["auth_bp (/auth)"]
            BP_Customer["customer_bp (/customer)"]
            BP_Provider["provider_bp (/provider)"]
            BP_Admin["admin_bp (/admin)"]
            BP_Payments["payments_bp (/payments)"]
            BP_API["api_bp (/api/v1)"]
            BP_Main["main_bp (/)"]
            BP_Errors["errors_bp (400, 403, 404, 429, 500)"]
        end

        subgraph Service_Layer ["Encapsulated Service Layer"]
            Svc_Booking["BookingService\n(State Machine, Double Booking Row Lock)"]
            Svc_KYC["KYCService\n(MIME Whitelist, Randomized UUID Storage)"]
            Svc_Payment["PaymentService\n(GST 18%, Commission 10%, Escrow Payout)"]
            Svc_Invoice["InvoiceService\n(ReportLab Dynamic PDF Generator)"]
            Svc_Audit["AuditService\n(Admin Action Audit Trail)"]
            Svc_Notif["NotificationService\n(In-App System Notification Engine)"]
        end

        Security["Security Controls:\nFlask-Login Session Auth\nFlask-WTF CSRF Protection\nFlask-Limiter Rate Throttling\nRole Decorators (@admin_required, etc.)"]
    end

    subgraph Data_Tier ["Data Tier (Relational Storage)"]
        ORM["SQLAlchemy ORM + Flask-Migrate"]
        MySQL_DB[("MySQL Database Server 26.7\nPort 3307 / fixmate_db\n(14 Normalized Tables)")]
        File_Store[("Secure File Storage\nvar/uploads/documents\n(Outside Webroot)")]
    end

    UI_Customer --> WSGI
    UI_Provider --> WSGI
    UI_Admin --> WSGI
    Vanilla_JS --> WSGI

    WSGI --> AppFactory
    AppFactory --> Blueprints
    Blueprints --> Security
    Blueprints --> Service_Layer
    Service_Layer --> ORM
    ORM --> MySQL_DB
    Svc_KYC --> File_Store
```

---

## 3. Use Case Diagram

```mermaid
flowchart LR
    Customer((Customer))
    Provider((Provider))
    Admin((Administrator))

    subgraph FixMate_System ["FixMate System Boundaries"]
        UC1["Register & Authenticate"]
        UC2["Browse Catalog & Approved Providers"]
        UC3["Create Service Booking"]
        UC4["Simulated Payment (UPI/Card)"]
        UC5["Download Tax PDF Invoice"]
        UC6["Submit Rating & Review"]
        UC7["Lodge Dispute Complaint"]

        UC8["Submit KYC ID & Address Proof"]
        UC9["Set Custom Prices within Admin Bounds"]
        UC10["Accept/Reject Job (5-Min Timeout)"]
        UC11["Execute & Complete Job with Final Bill"]
        UC12["Track Earnings & Commission Deductions"]

        UC13["Review KYC & Approve/Reject Applications"]
        UC14["Category CRUD & Price Boundaries"]
        UC15["User Suspension & Deactivation"]
        UC16["Dispute Arbitration & Refund Processing"]
        UC17["Inspect System Audit Trail"]
    end

    Customer --> UC1
    Customer --> UC2
    Customer --> UC3
    Customer --> UC4
    Customer --> UC5
    Customer --> UC6
    Customer --> UC7

    Provider --> UC1
    Provider --> UC8
    Provider --> UC9
    Provider --> UC10
    Provider --> UC11
    Provider --> UC12

    Admin --> UC13
    Admin --> UC14
    Admin --> UC15
    Admin --> UC16
    Admin --> UC17
```

---

## 4. Software Design Patterns Applied

### 1. Application Factory Pattern
- **Implementation:** `app.create_app(config_name)` in `app/__init__.py`.
- **Academic Benefit:** Allows seamless environment switching between `development` (uses local development database) and `testing` (instantiates isolated `fixmate_test_db` for pytest runs with CSRF disabled).

### 2. Service Layer Pattern
- **Implementation:** Directory `app/services/`.
- **Reasoning:** Keeps controllers/blueprints lightweight. Complex business rules—such as state transition graphs, double-booking row locks, 7-day complaint windows, and 18% GST splits—are housed strictly in service classes (`BookingService`, `PaymentService`, `KYCService`), maximizing reusability and testability.

### 3. Repository / ORM Pattern
- **Implementation:** SQLAlchemy Declarative Models in `app/models/`.
- **Reasoning:** Abstracts raw SQL into object-oriented entities while enforcing database constraints (foreign keys, cascading deletions, unique constraints, and check bounds) natively in MySQL.

### 4. Adapter / Strategy Pattern for Payments
- **Implementation:** `PaymentService.process_simulated_payment()` with an extensible payment interface.
- **Reasoning:** Simulates real UPI, Debit/Credit Card, Net Banking, and Mobile Wallet flows for the live academic demo without requiring external paid gateway credentials. Structured so real Razorpay or Stripe webhooks can be plugged in without changing booking lifecycle logic.

### 5. Decorator Pattern for Access Control
- **Implementation:** `app/utils/decorators.py` (`@customer_required`, `@provider_required`, `@approved_provider_required`, `@admin_required`).
- **Reasoning:** Declarative role enforcement at the route level. Prevents privilege escalation and blocks unverified providers from accepting bookings.

