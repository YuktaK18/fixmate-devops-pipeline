# FixMate — Home Service Management System

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask_3.1-green.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/Database-MySQL_26.7-orange.svg)](https://www.mysql.com/)
[![Bootstrap](https://img.shields.io/badge/Frontend-Bootstrap_5.3-purple.svg)](https://getbootstrap.com/)
[![Tests](https://img.shields.io/badge/Tests-35%20Passed-brightgreen.svg)](https://docs.pytest.org/)

> **Academic Capstone Project**  
> **Student:** Yukta Karwa  
> **Department:** Computer Engineering  
> **Institution:** Vivekanand Education Society's Institute of Technology (VESIT), Chembur, Mumbai  
> **Source of Truth:** `FixMate_SRS_Final_Formatted.docx` (v1.0)

---

## 1. Project Overview

**FixMate** is a full-stack, enterprise-grade Home Service Management System built with a real **Python Flask + MySQL** backend. It connects homeowners and residents with verified, background-checked service professionals (electricians, plumbers, carpenters, appliance technicians, painters, cleaners) governed by an administrative back-office.

Unlike static prototypes or mock projects, FixMate has **zero dummy data** and **zero dead buttons**:
- Every booking is persisted in normalized MySQL 3NF tables with database row locks preventing double-booking.
- Every payment undergoes a real financial breakdown (18% GST calculation, 10% platform commission deduction, and provider escrow payout holding).
- Invoices are dynamically compiled in memory and streamed as official PDF documents using ReportLab.
- Provider KYC documents (Aadhaar/ID & Address proof) are verified with MIME-whitelist validation, randomized UUID storage outside the webroot, and secure authorized streaming.
- 35 automated tests execute live against MySQL with a 100% pass rate.

---

## 2. Technology Stack

- **Backend:** Python 3.12, Flask 3.1 (Application Factory pattern with modular Blueprints)
- **Database:** MySQL Server 26.7 via SQLAlchemy ORM & Flask-Migrate (Alembic)
- **Frontend:** HTML5, CSS3, JavaScript (Vanilla ES6), Bootstrap 5.3.3, Jinja2 template inheritance (No React / No Node dependencies)
- **Security:** Flask-Login session authentication, password hashing via PBKDF2/SHA-256, Flask-WTF CSRF tokens, Flask-Limiter rate throttling, role-based decorators
- **Document Generation:** ReportLab 4.4 dynamic vector PDF engine
- **Testing:** pytest 9.1 with Flask test client and isolated transactional MySQL database
- **Deployment & WSGI:** Gunicorn 25.1, `wsgi.py`, python-dotenv

---

## 3. System Architecture & Role Interfaces

FixMate implements three distinct role-based interfaces with separate navigation bars and capabilities:

```text
FixMate Architecture
├── Presentation Tier (Client)
│   ├── Customer Portal (Search, Book, Track ETA, Pay, Invoices, Reviews, Complaints)
│   ├── Provider Portal (KYC Upload, Pricing Limits, Accept/Reject, Complete, Earnings)
│   └── Admin Portal (MySQL Analytics, KYC Review, Price Bounds, Disputes, Audit Trail)
│
├── Application Tier (Flask Backend)
│   ├── Blueprints: auth, customer, provider, admin, payments, api, main, errors
│   └── Service Layer: BookingService, PaymentService, KYCService, InvoiceService, AuditService
│
└── Data Tier (Relational Storage)
    ├── MySQL Server 26.7 (Port 3307 / fixmate_db)
    └── Secure Document Vault (var/uploads/documents/ - Outside Webroot)
```

### Detailed Documentation
- [System Architecture & Design (docs/ARCHITECTURE.md)](docs/ARCHITECTURE.md)
- [Database ER Model & Data Dictionary (docs/DATABASE_ER.md)](docs/DATABASE_ER.md)
- [Booking Sequence & State Machine (docs/BOOKING_SEQUENCE.md)](docs/BOOKING_SEQUENCE.md)
- [Requirements Traceability Matrix (docs/TRACEABILITY_MATRIX.md)](docs/TRACEABILITY_MATRIX.md)
- [Production Deployment Guide (docs/DEPLOYMENT_GUIDE.md)](docs/DEPLOYMENT_GUIDE.md)
- [Live Demo Script for Presentation (docs/DEMO_SCRIPT.md)](docs/DEMO_SCRIPT.md)
- [Viva Defense Q&A - 25+ Questions (docs/VIVA_QUESTIONS.md)](docs/VIVA_QUESTIONS.md)
- [Postman API Collection (docs/fixmate_postman_collection.json)](docs/fixmate_postman_collection.json)

---

## 4. Quick Start Guide (Windows / VS Code)

### Prerequisites
- Python 3.12 installed
- MySQL Server installed

### Step 1: Clone and Activate Environment
```powershell
cd "c:\Users\yukta\OneDrive\Documents\Fixmate Final"
.\venv\Scripts\Activate.ps1
```

### Step 2: Start the Dedicated MySQL Server
In a dedicated PowerShell terminal, run:
```powershell
.\scripts\start_mysql.ps1
```
*(Runs MySQL 26.7 isolated on `127.0.0.1:3307` with database `fixmate_db`).*

### Step 3: Run Database Migrations & Seed Data (First Time Only)
```powershell
flask db upgrade
python scripts\seed_data.py
```

### Step 4: Launch the Web Application
In a second PowerShell terminal, run:
```powershell
.\scripts\run_app.ps1
```
Open your browser at **`http://127.0.0.1:5000`**.

---

## 5. Live Demo Credentials

The Sign In page (`/auth/login`) includes **1-Click Quick-Fill buttons** for effortless demonstration:

| Role | Email Address | Password | Account Purpose / Features to Demo |
|---|---|---|---|
| **Customer** | `rahul@fixmate.local` | `Customer@123` | Chembur resident; browse categories, book providers, pay, download PDF invoice |
| **Approved Provider** | `ramesh.electrician@fixmate.local` | `Provider@123` | Verified electrician; 5-min accept window, mark job in-progress & complete |
| **Pending Provider** | `vijay.carpenter@fixmate.local` | `Provider@123` | Unverified carpenter; demonstrate KYC inspection and admin approval |
| **Flagged Provider** | `kunal.painter@fixmate.local` | `Provider@123` | Rating dropped below 3.0; auto-flagged for administrative scrutiny |
| **Super Admin** | `admin@fixmate.local` | `Admin@FixMate2026!` | Full operations: analytics, category price limits, KYC review, dispute refunds |

---

## 6. Automated Testing Suite

All 35 tests run against real MySQL:
```powershell
.\venv\Scripts\pytest.exe -v
```

### Test Coverage Highlights
- **`tests/test_auth.py` (6 tests):** Customer/provider registration, public admin block, 5-strike/15-min lockout, password reset tokens.
- **`tests/test_provider_kyc.py` (6 tests):** MIME whitelist, randomized UUID filenames, unapproved provider search hiding, admin approval & mandatory rejection reason.
- **`tests/test_booking_workflow.py` (6 tests):** 30-day booking bounds, row-locking double-booking prevention, state transitions, same-day 10% cancellation fee, mutual rescheduling.
- **`tests/test_payments_invoices.py` (5 tests):** 18% GST + 10% commission calculations, escrow payouts, ReportLab vector PDF compilation, admin dispute refunds.
- **`tests/test_reviews_complaints.py` (7 tests):** Post-completion review restriction, 1-review limit, 7-day complaint window, admin dispute resolution.
- **`tests/test_admin_and_audit.py` (5 tests):** Role-based access control (403), category CRUD price bounds, account suspension, dynamic settings, MySQL analytics.

**Result: `35 passed, 0 failed, 100% pass rate.`**

---

## 7. Project Directory Structure

```text
FixMate Final/
├── app/
│   ├── blueprints/           # Modular Flask Blueprints
│   │   ├── admin/            # Admin operations & analytics
│   │   ├── api/              # Public REST API v1 endpoints
│   │   ├── auth/             # Login, registration, lockout, reset
│   │   ├── customer/         # Search, booking, invoice, reviews
│   │   ├── errors/           # Custom 400, 403, 404, 429, 500 pages
│   │   ├── main/             # Landing, terms, privacy, FAQ
│   │   ├── payments/         # Simulated payment checkout & escrow
│   │   └── provider/         # KYC upload, services, jobs, earnings
│   ├── forms/                # Flask-WTF validated form classes
│   ├── models/               # 14 SQLAlchemy ORM models (3NF)
│   ├── services/             # Core business logic & state machine
│   ├── static/               # Custom CSS & Vanilla JS
│   ├── templates/            # Jinja2 layouts & role partials
│   └── utils/                # Role decorators (@admin_required, etc.)
├── docs/                     # Full academic documentation suite
├── migrations/               # Alembic version-controlled migrations
├── scripts/                  # Helper scripts (start_mysql, run_app, seed)
├── tests/                    # Comprehensive pytest test suite (35 tests)
├── var/                      # Dedicated MySQL data & secure uploads vault
├── config.py                 # Multi-environment configuration
├── requirements.txt          # Python dependencies
├── run.py                    # Application launcher
└── wsgi.py                   # Production WSGI entry point
```

---

## 8. Academic Scope & Limitations Disclosure

Per project scope requirements, the following architectural choices were made for this academic demonstration:
1. **Responsive Web Application:** Web interface replaces native iOS/Android mobile apps while remaining fully responsive across mobile, tablet, and desktop screens.
2. **Simulated Payment Gateway:** Operates within a transparent Demo Mode calculation layer with real MySQL transaction recording, GST tax calculations, and provider escrow holding without requiring paid external banking credentials.
3. **Simulated ETA Tracking:** Milestone-based tracking with calculated ETAs replaces live turn-by-turn telematics GPS hardware.
4. **In-App Notification Engine:** Real in-app alerts with unread badge counters replace paid third-party SMS/FCM gateways.

---

## 9. Academic Integrity & License
This project was developed by **Yukta Karwa** for academic evaluation at **VESIT**. All rights reserved © 2026.

