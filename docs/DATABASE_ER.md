# FixMate — Database Design & Entity Relationship (ER) Model

## 1. Relational Database Overview
The FixMate database runs on a dedicated **MySQL Server 26.7** instance on port **3307** (`fixmate_db`). It implements **Third Normal Form (3NF)** with strict referential integrity, primary keys, indexed foreign keys, enum constraints, and audit timestamps (`created_at`, `updated_at`).

---

## 2. Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    USERS ||--o| PROVIDER_PROFILES : "has profile (1:1)"
    USERS ||--o{ BOOKINGS : "books as customer (1:N)"
    USERS ||--o{ BOOKINGS : "executes as provider (1:N)"
    USERS ||--o{ REVIEWS : "writes review (1:N)"
    USERS ||--o{ COMPLAINTS : "files complaint (1:N)"
    USERS ||--o{ NOTIFICATIONS : "receives (1:N)"
    USERS ||--o{ ADMIN_AUDIT_LOGS : "performed by admin (1:N)"

    PROVIDER_PROFILES ||--o{ PROVIDER_DOCUMENTS : "uploads KYC (1:N)"
    PROVIDER_PROFILES ||--o{ PROVIDER_SERVICES : "offers (1:N)"
    PROVIDER_PROFILES ||--o{ REVIEWS : "receives (1:N)"

    SERVICE_CATEGORIES ||--o{ PROVIDER_SERVICES : "categorizes (1:N)"
    SERVICE_CATEGORIES ||--o{ BOOKINGS : "service type (1:N)"

    BOOKINGS ||--o{ BOOKING_STATUS_HISTORY : "tracks transitions (1:N)"
    BOOKINGS ||--o| PAYMENTS : "billed via (1:1)"
    BOOKINGS ||--o| INVOICES : "documented by (1:1)"
    BOOKINGS ||--o| REVIEWS : "reviewed via (1:1)"
    BOOKINGS ||--o{ COMPLAINTS : "disputed under (1:N)"

    PAYMENTS ||--o| INVOICES : "settles (1:1)"

    USERS {
        int id PK
        string name
        string email UK "Indexed"
        string phone UK
        string password_hash
        enum role "customer | provider | admin"
        boolean is_active
        boolean is_suspended
        int failed_login_attempts
        datetime locked_until
        boolean terms_accepted
        datetime terms_accepted_at
        datetime created_at
    }

    PROVIDER_PROFILES {
        int id PK
        int user_id FK, UK
        text bio
        int experience_years
        string service_pincode "Indexed"
        string service_area_name
        int service_radius_km
        enum verification_status "PENDING | APPROVED | REJECTED"
        text rejection_reason
        enum availability_status "AVAILABLE | BUSY | OFFLINE"
        decimal rating_avg
        int rating_count
        int completed_jobs_count
        boolean is_flagged_for_review
        string flagged_reason
        datetime verified_at
    }

    PROVIDER_DOCUMENTS {
        int id PK
        int provider_profile_id FK
        enum document_type "ID_PROOF | ADDRESS_PROOF"
        string original_filename
        string stored_filename UK
        string mime_type
        int file_size_bytes
        enum verification_status "PENDING | APPROVED | REJECTED"
        datetime uploaded_at
    }

    SERVICE_CATEGORIES {
        int id PK
        string name UK
        string slug UK, "Indexed"
        text description
        string icon
        decimal min_base_price
        decimal max_base_price
        boolean is_active
    }

    PROVIDER_SERVICES {
        int id PK
        int provider_profile_id FK
        int category_id FK
        decimal custom_price
        text description
    }

    BOOKINGS {
        int id PK
        string booking_code UK, "Indexed"
        int customer_id FK
        int provider_id FK
        int category_id FK
        date scheduled_date "Indexed"
        string scheduled_time_slot
        text service_address
        string pincode
        text special_instructions
        enum status "PENDING | ACCEPTED | REJECTED | IN_PROGRESS | COMPLETED | CANCELLED | RESCHEDULED"
        decimal quoted_amount
        decimal final_amount
        decimal cancellation_fee
        text cancellation_reason
        date reschedule_proposed_date
        string reschedule_proposed_time_slot
        datetime response_deadline
        datetime accepted_at
        datetime started_at
        datetime completed_at
    }

    BOOKING_STATUS_HISTORY {
        int id PK
        int booking_id FK
        string old_status
        string new_status
        int changed_by_user_id FK
        text reason
        datetime created_at
    }

    PAYMENTS {
        int id PK
        string transaction_reference UK, "Indexed"
        int booking_id FK, UK
        decimal subtotal
        decimal gst_rate
        decimal gst_amount
        decimal amount
        decimal commission_rate
        decimal commission_amount
        decimal provider_payout_amount
        enum payout_status "HELD | RELEASED"
        enum payment_method "UPI | CARD | NET_BANKING | WALLET"
        enum status "PENDING | PAID | FAILED | REFUNDED"
        decimal refund_amount
        text refund_reason
        datetime refunded_at
        datetime paid_at
    }

    INVOICES {
        int id PK
        string invoice_number UK, "Indexed"
        int booking_id FK, UK
        int payment_id FK, UK
        string customer_name
        string provider_name
        string service_title
        decimal subtotal
        decimal gst_rate
        decimal gst_amount
        decimal total_amount
        string pdf_filename
        datetime generated_at
    }

    REVIEWS {
        int id PK
        int booking_id FK, UK
        int customer_id FK
        int provider_id FK
        int provider_profile_id FK
        int rating "1 to 5"
        text comment
        datetime created_at
    }

    COMPLAINTS {
        int id PK
        string ticket_number UK, "Indexed"
        int booking_id FK
        int customer_id FK
        string subject
        text description
        string photo_filename
        enum status "OPEN | IN_REVIEW | RESOLVED | REJECTED"
        text resolution_notes
        int resolved_by_admin_id FK
        datetime resolved_at
        datetime created_at
    }

    NOTIFICATIONS {
        int id PK
        int user_id FK
        string title
        text message
        enum notification_type "BOOKING | KYC | PAYMENT | DISPUTE | ACCOUNT"
        string link_url
        boolean is_read
        datetime created_at
    }

    ADMIN_AUDIT_LOGS {
        int id PK
        int admin_id FK
        string action "Indexed"
        string target_entity
        string target_id
        text details
        string ip_address
        datetime created_at
    }

    SYSTEM_SETTINGS {
        int id PK
        string key_name UK, "Indexed"
        string key_value
        string description
        datetime updated_at
    }
```

---

## 3. Data Dictionary Summary

| Table Name | Entity Purpose | Primary Constraints & Indexes |
|---|---|---|
| `users` | Accounts for Customers, Providers, and Admins | PK (`id`), Unique (`email`), Unique (`phone`), Index on `email` |
| `provider_profiles` | KYC status, area, rating stats, flag alerts | PK (`id`), 1:1 FK (`user_id`), Index on `service_pincode` |
| `provider_documents` | File metadata for ID and Address Proofs | PK (`id`), FK (`provider_profile_id`), Unique (`stored_filename`) |
| `service_categories` | Service catalog with admin price boundaries | PK (`id`), Unique (`name`), Unique (`slug`) |
| `provider_services` | Association of provider with catalog + custom price | PK (`id`), Composite FK (`provider_profile_id`, `category_id`) |
| `bookings` | Core service reservations and slot locking | PK (`id`), Unique (`booking_code`), Composite Index on (`provider_id`, `scheduled_date`, `scheduled_time_slot`) |
| `booking_status_history` | Audit trail of every lifecycle status transition | PK (`id`), FK (`booking_id`), FK (`changed_by_user_id`) |
| `payments` | Financial records (GST 18%, Commission 10%, Escrow) | PK (`id`), Unique (`transaction_reference`), 1:1 FK (`booking_id`) |
| `invoices` | Official tax invoices with ReportLab PDF export | PK (`id`), Unique (`invoice_number`), 1:1 FK (`booking_id`, `payment_id`) |
| `reviews` | Customer 1–5 star ratings and feedback | PK (`id`), Unique 1:1 FK (`booking_id`), FK (`customer_id`, `provider_id`) |
| `complaints` | Customer disputes within 7 days of completion | PK (`id`), Unique (`ticket_number`), FK (`booking_id`, `customer_id`) |
| `notifications` | In-app alerts for bookings, payments, and account actions | PK (`id`), FK (`user_id`), Index on (`user_id`, `is_read`) |
| `admin_audit_logs` | Immutable audit trail of critical administrative actions | PK (`id`), FK (`admin_id`), Index on `action` |
| `system_settings` | Dynamic platform parameters (fees, GST, commission) | PK (`id`), Unique (`key_name`) |

---

## 4. Database Setup & Migration Instructions

1. **Start the Dedicated MySQL Server:**
   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 26.7\bin\mysqld.exe" --defaults-file="c:\Users\yukta\OneDrive\Documents\Fixmate Final\var\my_fixmate.ini" --console
   ```

2. **Initialize Schema & Seed Test Data:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   flask db upgrade
   python scripts\seed_data.py
   ```

