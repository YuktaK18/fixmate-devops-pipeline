# FixMate — Live Professor Demonstration Script

> **Student Note (Yukta Karwa, VESIT):** Keep this document open during your project presentation. Follow this sequence step-by-step to demonstrate every technical requirement smoothly.

---

## Pre-Demo Checklist (Do this 2 minutes before the presentation)
1. **Start MySQL Server:**
   - Open PowerShell in VS Code and run:
     ```powershell
     .\scripts\start_mysql.ps1
     ```
   - Verify it outputs: `[FixMate] Dedicated MySQL Server is ACTIVE on port 3307.`
2. **Start Flask Web App:**
   - Open a second PowerShell terminal in VS Code and run:
     ```powershell
     .\scripts\run_app.ps1
     ```
   - Open your browser at: `http://127.0.0.1:5000`
3. **Verify Demo Accounts:**
   - **Customer:** `rahul@fixmate.local` / `Customer@123`
   - **Approved Provider:** `ramesh.electrician@fixmate.local` / `Provider@123`
   - **Pending Provider:** `vijay.carpenter@fixmate.local` / `Provider@123`
   - **Administrator:** `admin@fixmate.local` / `Admin@FixMate2026!`
   *(Note: The Sign In page has 1-click "Quick-Fill Demo Credentials" buttons for instant login).*

---

## Act 1: The Landing Page & Architecture (1 minute)
- **Action:** Open `http://127.0.0.1:5000/`.
- **What to Say to Professor:**
  > *"Good morning Professor. FixMate is a Home Service Management System designed to connect verified local service professionals with residential customers, governed by an administrative back-office.
  > The system is built with a real Python Flask + MySQL backend adhering to a 3-tier architecture with modular blueprints, an encapsulated service layer, and database constraints. There are zero mock JSONs or dead buttons."*
- **Action:** Point out the top demo banner and the catalog cards (Plumbing, Electrical, Carpentry, Painting, etc.).

---

## Act 2: Customer Discovery & Booking Creation (2 minutes)
- **Action:** Click **Sign In** -> Click **"Quick-Fill: Customer"** button -> Click **Sign In**.
- **What to Say to Professor:**
  > *"I am now logged in as Rahul Verma, a resident in Chembur. The customer dashboard shows upcoming bookings, active jobs, and quick category shortcuts.
  > Let's browse the Electrical Repairs category."*
- **Action:** Click on **Electrical Repairs** category.
  - Show that **Ramesh Kumar** appears as an Approved Provider with verified badge, 4.9-star rating, and ₹300 starting price.
  - Point out that unapproved providers are strictly hidden at the MySQL query level (`verification_status = 'APPROVED'`).
- **Action:** Click **"Book Appointment"** on Ramesh Kumar.
  - Select a future date (e.g., tomorrow).
  - Select time slot: `11:00 - 01:00 PM`.
  - Enter address: `Flat 402, Sindhi Society, Chembur, Mumbai - 400071`.
  - Notes: `Master switchboard tripping under load`.
  - Click **Confirm and Book Service**.
- **What to Say to Professor:**
  > *"The booking is created in the PENDING state with an automatic 5-minute response deadline. Our backend uses database row locking and composite index checks to guarantee that no two customers can double-book Ramesh for the same date and slot."*

---

## Act 3: Provider Job Acceptance & Completion (2 minutes)
- **Action:** Click Logout -> Click **Sign In** -> Click **"Quick-Fill: Provider"** -> Click **Sign In**.
- **What to Say to Professor:**
  > *"Now I am logged in as Ramesh Kumar, the service provider. In Ramesh's dashboard, we immediately see the incoming booking request from Rahul Verma with a live 5-minute countdown."*
- **Action:** Click **"Accept Job"**.
  - Show the booking status moves to **ACCEPTED**.
- **Action:** Click **"Start Job (On-Site)"**.
  - Show the status moves to **IN_PROGRESS**.
- **Action:** Click **"Complete Job"**.
  - In the modal, confirm final bill amount: `₹450.00`.
  - Click **"Confirm Completion"**.
- **What to Say to Professor:**
  > *"The job is now marked COMPLETED. Ramesh's job is done, and the booking transitions into the payment settlement phase. Notice how our state machine rejects any illegal transitions."*

---

## Act 4: Customer Payment & PDF Tax Invoice (2 minutes)
- **Action:** Switch back to Customer (click **"Quick-Fill: Customer"**).
- **Action:** Navigate to **Bookings** -> Click **"View & Pay"** on the completed job.
- **What to Say to Professor:**
  > *"Rahul sees that the job has been completed by Ramesh for ₹450.00. Clicking 'Proceed to Payment' opens our simulated financial settlement engine."*
- **Action:** Click **"Proceed to Payment (Demo Mode)"**.
  - Show the financial breakdown:
    - Base Service Charge: ₹450.00
    - GST @ 18%: ₹81.00
    - Total Amount Payable: ₹531.00
    - Platform Commission (10%): ₹45.00
    - Provider Escrow Payout: ₹405.00 (Held in escrow per SRS 4.6.3)
  - Choose **UPI (Google Pay / PhonePe)** -> Click **"Complete Payment & Generate Invoice"**.
- **Action:** Show the digital invoice page.
- **Action:** Click **"Download PDF Invoice"**.
  - Open the downloaded PDF in Chrome to show the official ReportLab generated invoice with GSTIN, booking reference, and tax breakdown.

---

## Act 5: Feedback & Dispute Handling (1.5 minutes)
- **Action:** Back on the booking detail page, scroll to **"Rate & Review Service"**.
  - Select **5 Stars** and type: `Excellent electrician, resolved switchboard tripping within 30 minutes!`
  - Click **"Submit Review"**.
  - Point out that reviews are restricted to completed jobs, exactly one per booking.
- **Action:** Point out the **"Lodge Dispute Complaint"** button.
  - Explain that complaints are permitted within 7 days of completion with optional photo upload.

---

## Act 6: Administrator Operations & Governance (2.5 minutes)
- **Action:** Logout -> Click **Sign In** -> Click **"Quick-Fill: Admin"** -> Click **Sign In**.
- **What to Say to Professor:**
  > *"Finally, let's inspect the Administrator Control Center. The admin dashboard computes real statistics directly from MySQL: total revenue, daily and weekly bookings, open disputes, and active accounts."*
- **Action:** Navigate to **Providers** -> Click **Pending Applications**.
  - Click on **Vijay Carpenter** (`PENDING` application).
  - Show Vijay's uploaded Aadhaar card and Address proof streaming securely through our authorized route (`/admin/documents/<id>`).
  - Demonstrate clicking **"Approve Application"**.
  - Show Vijay's status immediately updates to `APPROVED` and an in-app notification is dispatched.
- **Action:** Navigate to **Categories**:
  - Show min and max base price boundaries (e.g. Plumbing: ₹200 to ₹2500). Explain that providers cannot undercharge or overcharge beyond these limits.
- **Action:** Navigate to **Audit Logs**:
  - Show the real MySQL immutable audit trail logging the approval action, timestamp, and administrator ID.
- **Action:** Navigate to `/api/v1/health` in a new tab:
  - Show JSON: `{"status": "healthy", "database": "connected", "database_engine": "MySQL 26.7"}`.

---

## Act 7: Automated Test Verification (1 minute)
- **Action:** Switch to terminal in VS Code.
- **Action:** Run:
  ```powershell
  .\venv\Scripts\pytest.exe -v
  ```
- **What to Say to Professor:**
  > *"To ensure enterprise quality and strict adherence to the SRS, our test suite contains 35 comprehensive automated tests covering security lockout, KYC validation, state machine integrity, double-booking prevention, 18% GST splits, ReportLab PDF generation, and dispute windows. All 35 tests execute live against our MySQL database."*
- **Show Result:** `35 passed in XX seconds`.

