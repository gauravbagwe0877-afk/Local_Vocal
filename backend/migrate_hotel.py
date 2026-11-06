import os
import json
import datetime
import mysql.connector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'local_vocal_db'),
    'autocommit': True,
}

TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS room_types (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        name         VARCHAR(100) NOT NULL,
        description  TEXT,
        max_adults   INT DEFAULT 2,
        max_children INT DEFAULT 1,
        base_rate    DECIMAL(10,2) NOT NULL,
        amenities    JSON,
        image_url    VARCHAR(500),
        is_active    BOOLEAN DEFAULT 1,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS rooms (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        room_number      VARCHAR(20) NOT NULL UNIQUE,
        floor            VARCHAR(10),
        room_type_id     INT,
        status           ENUM('available','reserved','occupied',
                             'cleaning','inspected','maintenance') DEFAULT 'available',
        housekeeping_status ENUM('clean','dirty','inspecting') DEFAULT 'clean',
        notes            TEXT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (room_type_id) REFERENCES room_types(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS guests (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        user_id      INT,
        full_name    VARCHAR(200) NOT NULL,
        email        VARCHAR(150) NOT NULL,
        phone        VARCHAR(20),
        address      TEXT,
        id_type      VARCHAR(50),
        id_number    VARCHAR(100),
        total_stays  INT DEFAULT 0,
        notes        TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS bookings (
        id               INT AUTO_INCREMENT PRIMARY KEY,
        booking_ref      VARCHAR(20) NOT NULL UNIQUE,
        guest_id         INT NOT NULL,
        room_id          INT,
        room_type_id     INT,
        check_in_date    DATE NOT NULL,
        check_out_date   DATE NOT NULL,
        nights           INT NOT NULL,
        adults           INT DEFAULT 1,
        children         INT DEFAULT 0,
        status           ENUM('pending','confirmed','checked_in',
                             'checked_out','cancelled','no_show') DEFAULT 'pending',
        room_rate        DECIMAL(10,2),
        total_amount     DECIMAL(10,2),
        paid_amount      DECIMAL(10,2) DEFAULT 0,
        special_requests TEXT,
        source           VARCHAR(50) DEFAULT 'walk_in',
        created_by       INT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (guest_id)     REFERENCES guests(id),
        FOREIGN KEY (room_id)      REFERENCES rooms(id) ON DELETE SET NULL,
        FOREIGN KEY (room_type_id) REFERENCES room_types(id) ON DELETE SET NULL,
        FOREIGN KEY (created_by)   REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoices (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        invoice_number VARCHAR(30) NOT NULL UNIQUE,
        booking_id     INT NOT NULL,
        subtotal       DECIMAL(10,2) DEFAULT 0,
        tax_amount     DECIMAL(10,2) DEFAULT 0,
        discount       DECIMAL(10,2) DEFAULT 0,
        total          DECIMAL(10,2) DEFAULT 0,
        paid_amount    DECIMAL(10,2) DEFAULT 0,
        status         ENUM('draft','issued','paid','partial','refunded') DEFAULT 'draft',
        notes          TEXT,
        issued_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (booking_id) REFERENCES bookings(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS invoice_items (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        invoice_id  INT NOT NULL,
        description VARCHAR(255) NOT NULL,
        quantity    DECIMAL(10,2) DEFAULT 1,
        unit_price  DECIMAL(10,2) NOT NULL,
        amount      DECIMAL(10,2) NOT NULL,
        item_type   ENUM('room','service','tax','discount','other') DEFAULT 'room',
        FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id             INT AUTO_INCREMENT PRIMARY KEY,
        invoice_id     INT NOT NULL,
        booking_id     INT,
        amount         DECIMAL(10,2) NOT NULL,
        method         ENUM('cash','card','upi','bank_transfer','other') DEFAULT 'cash',
        reference      VARCHAR(100),
        recorded_by    INT,
        payment_date   DATE NOT NULL,
        notes          TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (invoice_id)  REFERENCES invoices(id),
        FOREIGN KEY (booking_id)  REFERENCES bookings(id),
        FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS housekeeping_tasks (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        room_id      INT NOT NULL,
        assigned_to  INT,
        status       ENUM('pending','in_progress','completed','inspected') DEFAULT 'pending',
        priority     ENUM('low','normal','high','urgent') DEFAULT 'normal',
        task_type    ENUM('checkout_clean','daily_clean','deep_clean','inspection') DEFAULT 'daily_clean',
        notes        TEXT,
        started_at   TIMESTAMP NULL,
        completed_at TIMESTAMP NULL,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (room_id)     REFERENCES rooms(id),
        FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS expenses (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        category    VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        amount      DECIMAL(10,2) NOT NULL,
        method      ENUM('cash','card','upi','bank_transfer','other') DEFAULT 'cash',
        expense_date DATE NOT NULL,
        recorded_by INT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recorded_by) REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS maintenance_requests (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        room_id      INT,
        reported_by  INT,
        assigned_to  INT,
        issue        TEXT NOT NULL,
        priority     ENUM('low','normal','high','urgent') DEFAULT 'normal',
        status       ENUM('open','in_progress','resolved','closed') DEFAULT 'open',
        resolved_at  TIMESTAMP NULL,
        notes        TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (room_id)      REFERENCES rooms(id) ON DELETE SET NULL,
        FOREIGN KEY (reported_by)  REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY (assigned_to)  REFERENCES users(id) ON DELETE SET NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS hotel_settings (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        setting_key  VARCHAR(100) NOT NULL UNIQUE,
        setting_val  TEXT,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """
]

SETTINGS_DATA = [
    ('hotel_name',      'Hotel Sawant Palace'),
    ('hotel_address',   'Main Market Road, Sawantwadi 416510'),
    ('hotel_phone',     '+91 2363 272123'),
    ('hotel_email',     'info@sawantpalace.com'),
    ('check_in_time',   '12:00'),
    ('check_out_time',  '11:00'),
    ('gst_rate',        '12'),
    ('currency',        'INR'),
    ('currency_symbol', '₹')
]

def run_migration():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(buffered=True)

    print("[MIGRATION] Creating tables if not exist...")
    for sql in TABLES_SQL:
        cur.execute(sql)

    print("[MIGRATION] Seeding hotel_settings...")
    for k, v in SETTINGS_DATA:
        cur.execute(
            "INSERT IGNORE INTO hotel_settings (setting_key, setting_val) VALUES (%s, %s)",
            (k, v)
        )

    # 1. Room Types (5)
    cur.execute("SELECT COUNT(*) FROM room_types")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 5 room types...")
        room_types = [
            (
                'Single',
                'Cozy individual room suited for solo business travellers and explorers.',
                1, 0, 1500.00,
                json.dumps(["Single Bed", "Free Wi-Fi", "AC", "Work Desk", "Attached Bathroom"]),
                'https://images.unsplash.com/photo-1505693416388-ac5ce068fe85?w=800',
                1
            ),
            (
                'Double',
                'Comfortable room with a queen bed, ambient lighting, and work space.',
                2, 1, 2500.00,
                json.dumps(["Queen Bed", "Free Wi-Fi", "AC", "Smart TV", "Hot Shower", "Tea Maker"]),
                'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800',
                1
            ),
            (
                'Deluxe',
                'Spacious room featuring private balcony with scenic Western Ghats views.',
                2, 2, 4000.00,
                json.dumps(["King Bed", "Balcony with Ghats View", "High-Speed Wi-Fi", "Mini Fridge", "Bathtub", "Complimentary Breakfast"]),
                'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800',
                1
            ),
            (
                'Suite',
                'Grand presidential suite with separate living area, jacuzzi, and personalized concierge.',
                3, 2, 7500.00,
                json.dumps(["King Bed + Living Lounge", "Panoramic View", "Jacuzzi", "Mini Bar", "Butler Service", "Complimentary High Tea"]),
                'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800',
                1
            ),
            (
                'Family',
                'Generous family suite with dual queen beds and dedicated lounge for family stays.',
                4, 2, 5000.00,
                json.dumps(["2 Queen Beds", "Spacious Family Lounge", "AC", "Dining Table", "2 Bathrooms", "Kids Play Corner"]),
                'https://images.unsplash.com/photo-1566665797739-1674de7a421a?w=800',
                1
            )
        ]
        cur.executemany(
            """INSERT INTO room_types
               (name, description, max_adults, max_children, base_rate, amenities, image_url, is_active)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            room_types
        )

    # Fetch room type IDs
    cur.execute("SELECT id, name FROM room_types")
    rt_map = {name: rt_id for rt_id, name in cur.fetchall()}

    # 2. Rooms (15 across 3 floors)
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 15 rooms...")
        rooms_data = [
            # Floor 1
            ('101', 'Floor 1', rt_map['Single'], 'available', 'clean', 'Quiet corner room near garden entrance'),
            ('102', 'Floor 1', rt_map['Single'], 'occupied',  'dirty', 'Guest requested extra pillows and quiet cleaning'),
            ('103', 'Floor 1', rt_map['Double'], 'occupied',  'clean', 'Corporate guest checked in'),
            ('104', 'Floor 1', rt_map['Double'], 'available', 'clean', 'Freshly sanitized linen'),
            ('105', 'Floor 1', rt_map['Deluxe'], 'maintenance', 'clean', 'Plumbing repair on washroom tap'),
            # Floor 2
            ('201', 'Floor 2', rt_map['Double'], 'reserved',  'clean', 'Arrival scheduled for 3 PM'),
            ('202', 'Floor 2', rt_map['Double'], 'cleaning',  'dirty', 'Checkout clean underway'),
            ('203', 'Floor 2', rt_map['Deluxe'], 'occupied',  'clean', 'Balcony facing hills'),
            ('204', 'Floor 2', rt_map['Deluxe'], 'available', 'clean', 'Inspected and certified ready'),
            ('205', 'Floor 2', rt_map['Family'], 'occupied',  'clean', 'Family with 2 children'),
            # Floor 3
            ('301', 'Floor 3', rt_map['Deluxe'], 'available', 'clean', 'Rooftop floor deluxe suite'),
            ('302', 'Floor 3', rt_map['Suite'],  'occupied',  'clean', 'VIP honeymoon suite booking'),
            ('303', 'Floor 3', rt_map['Suite'],  'reserved',  'clean', 'VIP reservation confirmed'),
            ('304', 'Floor 3', rt_map['Family'], 'inspected', 'clean', 'Cleaned and ready for large group'),
            ('305', 'Floor 3', rt_map['Family'], 'available', 'clean', 'Mountain view corner room')
        ]
        cur.executemany(
            """INSERT INTO rooms
               (room_number, floor, room_type_id, status, housekeeping_status, notes)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            rooms_data
        )

    # Fetch users map for foreign keys
    cur.execute("SELECT id, username FROM users")
    user_map = {u: uid for uid, u in cur.fetchall()}
    admin_id = user_map.get('admin', 1)

    # 3. Guests (8)
    cur.execute("SELECT COUNT(*) FROM guests")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 8 guests...")
        guests_data = [
            (user_map.get('priya_sawant'), 'Priya Sawant', 'priya@example.com', '+91 9823112233', 'Bandra West, Mumbai, Maharashtra', 'Passport', 'Z6543219', 4, 'Frequent corporate traveler, prefers upper floor'),
            (user_map.get('rahul_desai'), 'Rahul Desai', 'rahul@example.com', '+91 9876501234', 'Panaji, Goa', 'Driving License', 'GA03 2019001234', 2, 'Likes late check-out when available'),
            (user_map.get('sneha_patil'), 'Sneha Patil', 'sneha@example.com', '+91 9820098765', 'Kothrud, Pune, Maharashtra', 'Aadhaar', '7892 3412 9012', 2, 'Family vacations, requests child cot'),
            (user_map.get('arjun_naik'), 'Arjun Naik', 'arjun@example.com', '+91 9765432190', 'Margao, Goa', 'Aadhaar', '3321 9081 5543', 1, 'Vegetarian meals preferred'),
            (None, 'Rajesh Sharma', 'rajesh.sharma@gmail.com', '+91 9822012345', 'Shivaji Nagar, Pune, Maharashtra', 'Aadhaar', '4521 8892 1204', 3, 'Regular business guest'),
            (None, 'Vikramaditya Rao', 'v.rao@techventures.in', '+91 9811223344', 'Indiranagar, Bengaluru, Karnataka', 'Passport', 'V9871234', 5, 'Executive guest, airport cab needed'),
            (None, 'Ananya Kulkarni', 'ananya.k@outlook.com', '+91 9922334455', 'Thane West, Mumbai, Maharashtra', 'Aadhaar', '5412 8763 2190', 1, 'Anniversary holiday celebration'),
            (None, 'Dr. Mahesh Hegde', 'mhegde@mangaloreclinic.org', '+91 9448123456', 'Kadri, Mangalore, Karnataka', 'Aadhaar', '9812 4532 6781', 2, 'Medical conference attendee')
        ]
        cur.executemany(
            """INSERT INTO guests
               (user_id, full_name, email, phone, address, id_type, id_number, total_stays, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            guests_data
        )

    # Fetch room IDs & guest IDs
    cur.execute("SELECT id, room_number, room_type_id FROM rooms")
    room_map = {rnum: (rid, rtid) for rid, rnum, rtid in cur.fetchall()}

    cur.execute("SELECT id, full_name FROM guests")
    guest_map = {name: gid for gid, name in cur.fetchall()}

    # 4. Bookings (12)
    cur.execute("SELECT COUNT(*) FROM bookings")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 12 bookings...")
        today = datetime.date.today()

        bookings_data = [
            # 1. Checked in (guest: Rajesh Sharma, room 102 Single)
            ('BK-2026-001', guest_map['Rajesh Sharma'], room_map['102'][0], room_map['102'][1],
             today - datetime.timedelta(days=1), today + datetime.timedelta(days=2), 3, 1, 0,
             'checked_in', 1500.00, 4500.00, 4500.00, 'Extra pillows requested', 'website', admin_id),
            # 2. Checked in (guest: Priya Sawant, room 103 Double)
            ('BK-2026-002', guest_map['Priya Sawant'], room_map['103'][0], room_map['103'][1],
             today, today + datetime.timedelta(days=3), 3, 2, 0,
             'checked_in', 2500.00, 7500.00, 7500.00, 'Non-smoking floor', 'direct', admin_id),
            # 3. Checked in (guest: Vikramaditya Rao, room 302 Suite)
            ('BK-2026-003', guest_map['Vikramaditya Rao'], room_map['302'][0], room_map['302'][1],
             today - datetime.timedelta(days=2), today + datetime.timedelta(days=1), 3, 2, 1,
             'checked_in', 7500.00, 22500.00, 22500.00, 'Late check-out pre-approved at 2 PM', 'phone', admin_id),
            # 4. Checked in (guest: Sneha Patil, room 205 Family)
            ('BK-2026-004', guest_map['Sneha Patil'], room_map['205'][0], room_map['205'][1],
             today, today + datetime.timedelta(days=2), 2, 4, 1,
             'checked_in', 5000.00, 10000.00, 5000.00, 'Child extra mattress provided', 'walk_in', admin_id),
            # 5. Checked in (guest: Arjun Naik, room 203 Deluxe)
            ('BK-2026-005', guest_map['Arjun Naik'], room_map['203'][0], room_map['203'][1],
             today - datetime.timedelta(days=1), today + datetime.timedelta(days=1), 2, 2, 0,
             'checked_in', 4000.00, 8000.00, 8000.00, 'Strictly vegetarian breakfast', 'website', admin_id),
            # 6. Confirmed (guest: Rahul Desai, room 201 Double)
            ('BK-2026-006', guest_map['Rahul Desai'], room_map['201'][0], room_map['201'][1],
             today + datetime.timedelta(days=1), today + datetime.timedelta(days=4), 3, 2, 0,
             'confirmed', 2500.00, 7500.00, 2500.00, 'Arrival after 6 PM', 'ota', admin_id),
            # 7. Confirmed (guest: Ananya Kulkarni, room 303 Suite)
            ('BK-2026-007', guest_map['Ananya Kulkarni'], room_map['303'][0], room_map['303'][1],
             today + datetime.timedelta(days=2), today + datetime.timedelta(days=5), 3, 2, 0,
             'confirmed', 7500.00, 22500.00, 10000.00, 'Anniversary cake and floral arrangement', 'website', admin_id),
            # 8. Pending (guest: Dr. Mahesh Hegde, room 104 Double)
            ('BK-2026-008', guest_map['Dr. Mahesh Hegde'], room_map['104'][0], room_map['104'][1],
             today + datetime.timedelta(days=3), today + datetime.timedelta(days=5), 2, 1, 0,
             'pending', 2500.00, 5000.00, 0.00, 'Awaiting confirmation call', 'phone', admin_id),
            # 9. Checked out (guest: Rajesh Sharma, room 101 Single)
            ('BK-2026-009', guest_map['Rajesh Sharma'], room_map['101'][0], room_map['101'][1],
             today - datetime.timedelta(days=7), today - datetime.timedelta(days=4), 3, 1, 0,
             'checked_out', 1500.00, 4500.00, 4500.00, 'Business trip completed', 'walk_in', admin_id),
            # 10. Checked out (guest: Priya Sawant, room 301 Deluxe)
            ('BK-2026-010', guest_map['Priya Sawant'], room_map['301'][0], room_map['301'][1],
             today - datetime.timedelta(days=10), today - datetime.timedelta(days=7), 3, 2, 0,
             'checked_out', 4000.00, 12000.00, 12000.00, 'Smooth stay and full payment', 'website', admin_id),
            # 11. Cancelled (guest: Rahul Desai, room 104 Double)
            ('BK-2026-011', guest_map['Rahul Desai'], room_map['104'][0], room_map['104'][1],
             today - datetime.timedelta(days=5), today - datetime.timedelta(days=3), 2, 1, 0,
             'cancelled', 2500.00, 5000.00, 0.00, 'Cancelled due to travel plan change', 'ota', admin_id),
            # 12. No Show (guest: Arjun Naik, room 204 Deluxe)
            ('BK-2026-012', guest_map['Arjun Naik'], room_map['204'][0], room_map['204'][1],
             today - datetime.timedelta(days=3), today - datetime.timedelta(days=1), 2, 2, 0,
             'no_show', 4000.00, 8000.00, 2000.00, 'Guest did not arrive, deposit retained', 'phone', admin_id)
        ]

        cur.executemany(
            """INSERT INTO bookings
               (booking_ref, guest_id, room_id, room_type_id, check_in_date, check_out_date,
                nights, adults, children, status, room_rate, total_amount, paid_amount,
                special_requests, source, created_by)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            bookings_data
        )

    # Fetch booking IDs
    cur.execute("SELECT id, booking_ref FROM bookings")
    b_map = {ref: bid for bid, ref in cur.fetchall()}

    # 5. Invoices & Payments (5)
    cur.execute("SELECT COUNT(*) FROM invoices")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 5 invoices and payments...")
        today = datetime.date.today()

        # Invoices:
        # INV-2026-001 for BK-2026-001 (Single, 3 nights: 4500 + 540 GST = 5040)
        # INV-2026-002 for BK-2026-002 (Double, 3 nights: 7500 + 900 GST = 8400)
        # INV-2026-003 for BK-2026-003 (Suite, 3 nights: 22500 + 2700 GST = 25200)
        # INV-2026-004 for BK-2026-004 (Family, 2 nights: 10000 + 1200 GST = 11200, paid 5600 partial)
        # INV-2026-005 for BK-2026-007 (Suite, 3 nights: 22500 + 2700 GST = 25200, advance paid 10000)

        invoices_data = [
            ('INV-2026-001', b_map['BK-2026-001'], 4500.00, 540.00, 0.00, 5040.00, 5040.00, 'paid', 'Standard stay bill'),
            ('INV-2026-002', b_map['BK-2026-002'], 7500.00, 900.00, 0.00, 8400.00, 8400.00, 'paid', 'Full payment received at check-in'),
            ('INV-2026-003', b_map['BK-2026-003'], 22500.00, 2700.00, 0.00, 25200.00, 25200.00, 'paid', 'Suite VIP package with airport transit'),
            ('INV-2026-004', b_map['BK-2026-004'], 10000.00, 1200.00, 0.00, 11200.00, 5600.00, 'partial', '50% advance deposit paid'),
            ('INV-2026-005', b_map['BK-2026-007'], 22500.00, 2700.00, 0.00, 25200.00, 10000.00, 'partial', 'Advance booking deposit received')
        ]
        cur.executemany(
            """INSERT INTO invoices
               (invoice_number, booking_id, subtotal, tax_amount, discount, total, paid_amount, status, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            invoices_data
        )

        cur.execute("SELECT id, invoice_number, booking_id FROM invoices")
        inv_map = {inv_num: (iid, bid) for iid, inv_num, bid in cur.fetchall()}

        # Invoice items
        items_data = [
            # INV-2026-001
            (inv_map['INV-2026-001'][0], 'Single Room Stay (3 Nights @ ₹1,500)', 3, 1500.00, 4500.00, 'room'),
            (inv_map['INV-2026-001'][0], 'GST Tax (12%)', 1, 540.00, 540.00, 'tax'),
            # INV-2026-002
            (inv_map['INV-2026-002'][0], 'Double Room Stay (3 Nights @ ₹2,500)', 3, 2500.00, 7500.00, 'room'),
            (inv_map['INV-2026-002'][0], 'GST Tax (12%)', 1, 900.00, 900.00, 'tax'),
            # INV-2026-003
            (inv_map['INV-2026-003'][0], 'Presidential Suite Stay (3 Nights @ ₹7,500)', 3, 7500.00, 22500.00, 'room'),
            (inv_map['INV-2026-003'][0], 'GST Tax (12%)', 1, 2700.00, 2700.00, 'tax'),
            # INV-2026-004
            (inv_map['INV-2026-004'][0], 'Family Suite Stay (2 Nights @ ₹5,000)', 2, 5000.00, 10000.00, 'room'),
            (inv_map['INV-2026-004'][0], 'GST Tax (12%)', 1, 1200.00, 1200.00, 'tax'),
            # INV-2026-005
            (inv_map['INV-2026-005'][0], 'Presidential Suite Stay (3 Nights @ ₹7,500)', 3, 7500.00, 22500.00, 'room'),
            (inv_map['INV-2026-005'][0], 'GST Tax (12%)', 1, 2700.00, 2700.00, 'tax')
        ]
        cur.executemany(
            """INSERT INTO invoice_items
               (invoice_id, description, quantity, unit_price, amount, item_type)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            items_data
        )

        # Payments
        payments_data = [
            (inv_map['INV-2026-001'][0], inv_map['INV-2026-001'][1], 5040.00, 'upi', 'UPI-TXN-9021841', admin_id, today - datetime.timedelta(days=1), 'Full payment via GPay'),
            (inv_map['INV-2026-002'][0], inv_map['INV-2026-002'][1], 8400.00, 'card', 'POS-HDFC-5821', admin_id, today, 'Debit card swipe at front desk'),
            (inv_map['INV-2026-003'][0], inv_map['INV-2026-003'][1], 25200.00, 'bank_transfer', 'NEFT-ICICI-00918', admin_id, today - datetime.timedelta(days=2), 'Corporate direct transfer'),
            (inv_map['INV-2026-004'][0], inv_map['INV-2026-004'][1], 5600.00, 'cash', 'RCPT-CSH-104', admin_id, today, '50% cash advance paid'),
            (inv_map['INV-2026-005'][0], inv_map['INV-2026-005'][1], 10000.00, 'upi', 'UPI-TXN-8821943', admin_id, today - datetime.timedelta(days=1), 'Advance booking token')
        ]
        cur.executemany(
            """INSERT INTO payments
               (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            payments_data
        )

    # 6. Housekeeping Tasks (6)
    cur.execute("SELECT COUNT(*) FROM housekeeping_tasks")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 6 housekeeping tasks...")
        now = datetime.datetime.now()
        hk_data = [
            (room_map['202'][0], admin_id, 'in_progress', 'urgent', 'checkout_clean', 'Checkout clean needed before 2 PM arrival', now - datetime.timedelta(hours=1), None),
            (room_map['102'][0], admin_id, 'pending', 'normal', 'daily_clean', 'Daily linen refresh and refill tea bar', None, None),
            (room_map['105'][0], admin_id, 'pending', 'high', 'deep_clean', 'Post-maintenance washroom sanitization', None, None),
            (room_map['204'][0], admin_id, 'completed', 'normal', 'inspection', 'Turn-down service and inspection done', now - datetime.timedelta(hours=3), now - datetime.timedelta(hours=2)),
            (room_map['304'][0], admin_id, 'inspected', 'normal', 'inspection', 'Floor supervisor quality check passed', now - datetime.timedelta(hours=4), now - datetime.timedelta(hours=3)),
            (room_map['302'][0], admin_id, 'completed', 'high', 'daily_clean', 'Suite luxury refresh with fresh towels and fruits', now - datetime.timedelta(hours=5), now - datetime.timedelta(hours=4))
        ]
        cur.executemany(
            """INSERT INTO housekeeping_tasks
               (room_id, assigned_to, status, priority, task_type, notes, started_at, completed_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            hk_data
        )

    # 7. Maintenance Requests (4)
    cur.execute("SELECT COUNT(*) FROM maintenance_requests")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 4 maintenance requests...")
        now = datetime.datetime.now()
        mr_data = [
            (room_map['105'][0], admin_id, admin_id, 'Bathroom sink drain slow and tap dripping', 'urgent', 'in_progress', None, 'Plumber currently replacing drain valve'),
            (room_map['204'][0], admin_id, admin_id, 'AC cooling weak, coil cleaning required', 'normal', 'resolved', now - datetime.timedelta(days=1), 'Coil cleaned and refrigerant refilled'),
            (room_map['302'][0], admin_id, admin_id, 'Master balcony door lock latch loose', 'low', 'open', None, 'Carpenter notified, replacement latch ordered'),
            (room_map['102'][0], admin_id, admin_id, 'Bedside reading spotlight flickering', 'normal', 'open', None, 'Electrician to replace warm LED driver')
        ]
        cur.executemany(
            """INSERT INTO maintenance_requests
               (room_id, reported_by, assigned_to, issue, priority, status, resolved_at, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            mr_data
        )

    # 8. Expenses (10)
    cur.execute("SELECT COUNT(*) FROM expenses")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding 10 expenses...")
        today = datetime.date.today()
        expenses_data = [
            ('Linen & Laundry', 'Commercial washing for bedsheets, duvet covers & bath towels', 3450.00, 'cash', today - datetime.timedelta(days=2), admin_id),
            ('Kitchen Supplies', 'Morning breakfast buffet groceries, dairy & fresh bread', 6800.00, 'upi', today - datetime.timedelta(days=1), admin_id),
            ('Utilities', 'Monthly electricity bill for central AC and hotel water pumps', 18400.00, 'bank_transfer', today - datetime.timedelta(days=5), admin_id),
            ('Maintenance & Repairs', 'Plumbing fittings, replacement washers, and silicone sealant', 1250.00, 'cash', today - datetime.timedelta(days=3), admin_id),
            ('Housekeeping Supplies', 'Floor cleaner, surface disinfectant & room freshener refills', 2900.00, 'card', today - datetime.timedelta(days=4), admin_id),
            ('Toiletries & Amenities', 'Luxury herbal shampoo, ayurvedic soap & dental kits bulk supply', 4200.00, 'upi', today - datetime.timedelta(days=6), admin_id),
            ('Internet & Telecom', 'High-speed business fiber internet broadband renewal', 2499.00, 'card', today - datetime.timedelta(days=8), admin_id),
            ('Garden & Landscaping', 'Courtyard potted plants upkeep and lawn trimming service', 1800.00, 'cash', today - datetime.timedelta(days=7), admin_id),
            ('Stationery & Office', 'Guest registration forms, keycard envelopes, invoice paper rolls', 950.00, 'cash', today - datetime.timedelta(days=10), admin_id),
            ('Beverages & Minibar', 'Artisanal roasted coffee beans, premium tea & sugar sachets', 1650.00, 'upi', today - datetime.timedelta(days=9), admin_id)
        ]
        cur.executemany(
            """INSERT INTO expenses
               (category, description, amount, method, expense_date, recorded_by)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            expenses_data
        )

    print("[SUCCESS] Phase 1 Database Migration & Seeding completed successfully!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    run_migration()
