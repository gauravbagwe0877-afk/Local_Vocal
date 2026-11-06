# 🏨 StaySmart – Hotel Management System & Local Vocal Platform

A comprehensive, full-stack, enterprise-grade Hotel Management System (HMS / PMS) integrated with the Sawantwadi discovery portal. Built using **Python (Flask)**, **MySQL**, and a tailored modern **UI/UX Design System** (Warm terracotta `#B5451B`, forest green `#2D6A4F`, warm cream `#FDF6EC`, Playfair Display & Inter typography).

---

## 🌟 Key Upgraded Highlights

### 1. 🛡️ Three-Tier Role-Based Authentication
- **Administrator Panel (`/admin/dashboard`)**:
  - Executive KPI dashboard (real-time dynamic occupancy, collections, ADR, RevPAR).
  - Full Room Inventory & Room Types / Tariffs CRUD.
  - Customer directory & Receptionist staff management (creation, editing, instant deactivation).
  - System-wide booking management, status overrides, and cancellation audits.
  - Financial ledger, collections by payment method, daily/weekly/monthly revenue reports with net profit calculations.
  - Hotel amenities & services configuration.
  - Comprehensive immutable activity logs (`activity_logs`) recording logins, actions, and IP addresses.
- **Receptionist Front Desk Console (`/receptionist/dashboard`)**:
  - Live front desk operations: Today's expected arrivals, departures, in-house guests.
  - Customer registration & instant search (by Name, Phone, or Booking ID).
  - New walk-in reservation wizard with **real-time double-booking prevention**.
  - One-click Check-in and Check-out console.
  - Cashiering & payment recording (Cash, Card, UPI, Bank Transfer).
  - Print-ready GST booking confirmation receipts.
  - Archived booking history and daily shift reports.
  - *Strict security*: Receptionists are completely blocked from admin tools, configuration, and user deactivation.
- **Customer Guest Portal (`/customer/dashboard`)**:
  - Dedicated self-service guest portal with real-time room availability search.
  - Room filtering by check-in/out dates, guest capacity, and room category.
  - Transparent itemized cost breakdown (Nights &times; Base Tariff + 12% GST).
  - Online booking workflow with instant unique Booking ID (`BK-YYYY-XXXX`).
  - Active/upcoming bookings management and cancellation per hotel policies.
  - Print-ready itemized tax receipts and payment ledger.
  - Profile update and full guest privacy (Customer A cannot access Customer B's records).

### 2. ⚡ Real-Time Double-Booking Prevention
The system enforces strict overlapping date checks at the database query level:
```sql
SELECT r.id FROM rooms r
WHERE r.id = :room_id AND r.status IN ('available', 'clean')
  AND r.id NOT IN (
      SELECT room_id FROM bookings
      WHERE status IN ('confirmed', 'checked_in')
        AND NOT (check_out_date <= :check_in OR check_in_date >= :check_out)
  )
```

### 3. 🎨 Standardized Modern Design System
- **Colors**: Terracotta `#B5451B`, Forest Green `#2D6A4F`, Amber `#F4A261`, Warm Cream `#FDF6EC`, Surface `#FFFFFF`.
- **Typography**: Playfair Display (Headings), Inter (Body UI), JetBrains Mono (IDs & Financials).
- **Components**: 260px fixed sidebar, stat cards with hover lift, floating-label forms with validation, responsive data tables with status badges, and print-ready tax receipts.

---

## 🔑 Demo & Test Credentials

| Role | Username | Password | Dedicated Portal |
| :--- | :--- | :--- | :--- |
| **Administrator** | `admin` | `admin123` | [http://127.0.0.1:5000/admin/login](http://127.0.0.1:5000/admin/login) |
| **Receptionist** | `receptionist` | `receptionist123` | [http://127.0.0.1:5000/receptionist/login](http://127.0.0.1:5000/receptionist/login) |
| **Customer** | `customer` | `customer123` | [http://127.0.0.1:5000/customer/login](http://127.0.0.1:5000/customer/login) |

*New customers can also self-register at [http://127.0.0.1:5000/customer/register](http://127.0.0.1:5000/customer/register).*

---

## 🚀 How to Run the Application

### 1. Requirements
- Python 3.10+
- MySQL Server (running on `localhost:3306`, user: `root`, password: `root`, database: `local_vocal_db`)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Server
From the root directory:
```bash
python run.py
```
Or from the `backend/` directory:
```bash
cd backend
python run.py
```
Access the application at: **`http://127.0.0.1:5000`**

### 4. Run Automated Test Suites
Run the comprehensive role-based security & integration suite:
```bash
python backend/test_staysmart_roles.py
```
Run the PMS unit suite:
```bash
python backend/test_hotel_pms.py
```

---

## 🗂️ Project Architecture

```
local_vocal/
├── run.py                          # Root launcher
├── requirements.txt                # Python dependencies
├── README.md                       # Documentation
│
├── backend/
│   ├── app.py                      # Flask factory & blueprint registration
│   ├── run.py                      # Backend launcher with gallery assets
│   ├── database.py                 # MySQL pooled connection helper
│   ├── auth_decorators.py          # Role guards (@admin_required, @receptionist_required, @customer_required)
│   ├── migrate_staysmart.py        # StaySmart DB migration & seeding
│   ├── test_staysmart_roles.py     # 7 comprehensive security & integration tests
│   ├── test_hotel_pms.py           # PMS unit tests
│   └── blueprints/
│       ├── auth.py                 # Dedicated & unified authentication routes
│       ├── admin.py                # Admin console (Rooms, Staff, Reports, Logs)
│       ├── receptionist.py         # Front desk (Check-in/out, Cashiering, Search)
│       ├── customer.py             # Guest portal (Availability search, Booking, Receipts)
│       ├── hotel.py                # Legacy PMS routes (backward compatible)
│       └── main.py                 # Explore Sawantwadi places & reviews
│
└── frontend/
    ├── static/
    │   ├── css/
    │   │   ├── style.css           # Public styles
    │   │   └── hotel_pms.css       # StaySmart Design System styles
    │   └── js/
    │       ├── main.js             # Public scripts
    │       └── hotel_pms.js        # PMS modals, tabs, and print helpers
    │
    └── templates/
        ├── base.html               # Public base template with StaySmart branding
        ├── index.html              # Home with quick room availability search
        ├── auth/                   # Role login portals & registration
        ├── admin/                  # Admin console screens
        ├── receptionist/           # Front desk operations screens
        └── customer/               # Guest booking portal screens
```
