# FixMate — Booking Lifecycle & State Transitions

## 1. End-to-End Core Booking Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Customer as Customer (Browser)
    actor Provider as Provider (Browser)
    participant Web as Flask Web App (Customer/Provider Blueprints)
    participant BookingSvc as BookingService
    participant PaymentSvc as PaymentService
    participant InvoiceSvc as InvoiceService
    participant DB as MySQL Database (3NF)
    actor Admin as Administrator (Browser)

    %% Step 1: Booking Creation
    Note over Customer,DB: 1. Booking Creation & Slot Reservation
    Customer->>Web: Select Category, Provider, Date, Time Slot, Address
    Web->>BookingSvc: create_booking(customer, provider, date, slot, address)
    BookingSvc->>DB: Check double-booking (SELECT with row lock)
    alt Slot is already booked
        BookingSvc-->>Web: Raise DoubleBookingError
        Web-->>Customer: Flash "Slot unavailable. Please choose another slot."
    else Slot is free
        BookingSvc->>DB: INSERT INTO bookings (status='PENDING', response_deadline=now+5min)
        BookingSvc->>DB: INSERT INTO notifications (Provider: "New Booking Request")
        BookingSvc-->>Web: Return Booking entity (FIX-YYYYMMDD-XXXX)
        Web-->>Customer: Redirect to Booking Detail (Status: PENDING)
    end

    %% Step 2: Provider Response
    Note over Provider,DB: 2. Provider Acceptance (5-Minute Window)
    Provider->>Web: View incoming booking request
    alt Responded within 5 minutes
        Provider->>Web: Click "Accept Booking"
        Web->>BookingSvc: transition_status(booking, 'ACCEPTED', provider)
        BookingSvc->>DB: UPDATE bookings SET status='ACCEPTED', accepted_at=now()
        BookingSvc->>DB: INSERT INTO notifications (Customer: "Booking Accepted")
        Web-->>Provider: Flash "Booking Accepted. Customer notified."
    else 5 minutes expired without response
        Web->>BookingSvc: check_and_expire_pending_bookings()
        BookingSvc->>DB: Reassign to next best provider or mark UNASSIGNED
    end

    %% Step 3: Service Delivery
    Note over Provider,Customer: 3. Service Execution & Job Completion
    Provider->>Web: Arrive at site & click "Start Job"
    Web->>BookingSvc: transition_status(booking, 'IN_PROGRESS', provider)
    BookingSvc->>DB: UPDATE bookings SET status='IN_PROGRESS', started_at=now()
    
    Provider->>Web: Complete Work & enter Final Amount (e.g. ₹500.00)
    Web->>BookingSvc: transition_status(booking, 'COMPLETED', provider, final_amount=500.00)
    BookingSvc->>DB: UPDATE bookings SET status='COMPLETED', final_amount=500.00, completed_at=now()
    BookingSvc->>DB: INSERT INTO notifications (Customer: "Job Completed. Please proceed to payment.")
    Web-->>Provider: Redirect to Completed Job Summary

    %% Step 4: Payment & Invoice
    Note over Customer,DB: 4. Simulated Payment & Tax Invoicing
    Customer->>Web: View completed booking -> Click "Pay Now (Demo Mode)"
    Customer->>Web: Choose Payment Method (UPI / Card / Net Banking)
    Web->>PaymentSvc: process_simulated_payment(booking, method='UPI')
    PaymentSvc->>PaymentSvc: calculate_breakdown(500.00) -> Base 500 + GST 18% (90) = 590.00
    PaymentSvc->>PaymentSvc: Commission 10% (50.00) -> Provider Escrow Payout (450.00)
    PaymentSvc->>DB: INSERT INTO payments (status='PAID', payout_status='HELD', ref='TXN-...')
    PaymentSvc->>InvoiceSvc: generate_invoice(payment)
    InvoiceSvc->>DB: INSERT INTO invoices (inv_number='INV-...', total=590.00)
    PaymentSvc->>DB: INSERT INTO notifications (Provider: "Payment of ₹450 credited to escrow")
    Web-->>Customer: Redirect to Digital Tax Invoice Page
    Customer->>Web: Click "Download PDF Invoice"
    Web->>InvoiceSvc: generate_pdf_invoice(invoice) -> Stream ReportLab PDF
    Web-->>Customer: Deliver official PDF download

    %% Step 5: Review & Rating
    Note over Customer,DB: 5. Rating & Review Feedback
    Customer->>Web: Submit Review (Rating: 5 Stars + Comment)
    Web->>DB: INSERT INTO reviews (booking_id, rating=5, comment=...)
    Web->>DB: Recalculate provider profile rating_avg and rating_count
    Web-->>Customer: Flash "Thank you for rating your service experience!"

    %% Step 6: Dispute Arbitration
    opt Customer lodges dispute within 7 days
        Note over Customer,Admin: 6. Dispute Complaint & Admin Resolution
        Customer->>Web: Submit Complaint (Subject, Description, Photo)
        Web->>DB: INSERT INTO complaints (status='OPEN', ticket='CMP-...')
        Admin->>Web: Inspect complaint details & booking history
        Admin->>Web: Update status to 'RESOLVED' with notes & issue ₹200 refund
        Web->>PaymentSvc: issue_refund(payment, refund_amount=200.00, reason=..., admin)
        PaymentSvc->>DB: UPDATE payments SET refund_amount=200.00, refunded_at=now()
        PaymentSvc->>DB: UPDATE complaints SET status='RESOLVED', resolution_notes=...
        PaymentSvc->>DB: INSERT INTO notifications (Customer: "Dispute Resolved. Refund of ₹200 issued.")
        Web-->>Admin: Flash "Complaint resolved and refund recorded."
    end
```

---

## 2. Booking State Transition Diagram

```mermaid
stateDiagram-v2
    [*] --> PENDING: Customer submits booking
    
    PENDING --> ACCEPTED: Provider accepts within 5 minutes
    PENDING --> REJECTED: Provider explicitly rejects
    PENDING --> CANCELLED: Customer cancels before acceptance (Fee: ₹0)

    ACCEPTED --> IN_PROGRESS: Provider starts job on scheduled date
    ACCEPTED --> RESCHEDULED: Customer/Provider requests new date/slot
    ACCEPTED --> CANCELLED: Cancelled after acceptance (10% fee if same day)

    RESCHEDULED --> ACCEPTED: Other party accepts proposed time slot
    RESCHEDULED --> CANCELLED: Mutually aborted

    IN_PROGRESS --> COMPLETED: Provider finishes job and submits final amount

    COMPLETED --> [*]: Payment settled, review submitted, invoice archived
    REJECTED --> [*]: Closed
    CANCELLED --> [*]: Closed
```

### Transition Validation Matrix

| Current State | Target State | Permitted Actor | Validation Rules |
|---|---|---|---|
| `PENDING` | `ACCEPTED` | Provider | Response deadline must not have expired (< 5 mins). |
| `PENDING` | `REJECTED` | Provider | Provider declines job; customer notified immediately. |
| `PENDING` | `CANCELLED` | Customer | No penalty fee applied (`cancellation_fee = 0.00`). |
| `ACCEPTED` | `IN_PROGRESS` | Provider | Provider on-site; timer starts. |
| `ACCEPTED` | `RESCHEDULED` | Customer / Provider | Requires mutual agreement on new proposed slot. |
| `ACCEPTED` | `CANCELLED` | Customer | If cancelled on the same scheduled date, 10% penalty fee applied. |
| `RESCHEDULED` | `ACCEPTED` | Counterparty | Confirms rescheduled date/slot in provider calendar. |
| `IN_PROGRESS` | `COMPLETED` | Provider | Provider inputs final confirmed bill amount. |
| `COMPLETED` | *Any* | *None* | Terminal state. Review allowed; complaint allowed within 7 days. |

