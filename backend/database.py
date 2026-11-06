import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),        # FIX 1: No default password
    'database': os.environ.get('DB_NAME', 'local_vocal_db'),
    'autocommit': True,
}

# ─── CONNECTION HELPERS ───────────────────────────────────────────────────────

def get_db():
    from flask import g
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(**DB_CONFIG)
        except mysql.connector.Error as e:
            print(f'[ERROR] Could not connect to MySQL: {e}')
            raise
    else:
        # FIX 2: Reconnect if connection dropped (ping to keep alive)
        try:
            g.db.ping(reconnect=True, attempts=3, delay=1)
        except mysql.connector.Error:
            g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db

def close_db(e=None):
    from flask import g
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()

# FIX 3: Removed 'commit' param — autocommit=True handles it automatically
# Use 'one=True' to get a single row, otherwise returns a list
def query(sql, args=(), one=False):
    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)
    cursor.execute(sql, args)
    result = cursor.fetchall()
    cursor.close()                                         # FIX 4: Always close cursor

    # FIX: Cast Decimal values to float and datetime to string for SQLite template compatibility
    import decimal
    import datetime
    for row in result:
        for k, v in row.items():
            if isinstance(v, decimal.Decimal):
                row[k] = float(v)
            elif isinstance(v, (datetime.datetime, datetime.date)):
                row[k] = str(v)

    return (result[0] if result else None) if one else result

# FIX 5: Separate function for INSERT/UPDATE/DELETE — returns lastrowid
def execute(sql, args=()):
    db = get_db()
    cursor = db.cursor(buffered=True)
    cursor.execute(sql, args)
    last_id = cursor.lastrowid
    cursor.close()
    return last_id

# FIX 6: Added init_app so Flask registers close_db on teardown properly
def init_app(app):
    app.teardown_appcontext(close_db)

# ─── INIT DATABASE ─────────────────────────────────────────────────────────────

def init_db():
    import bcrypt

    conn = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        autocommit=True
    )
    cur = conn.cursor(buffered=True)
    db_name = DB_CONFIG['database']

    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
    cur.execute(f"USE `{db_name}`")

    # ── TABLES ───────────────────────────────────────────────────────────────

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id   INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            icon VARCHAR(20)  NOT NULL DEFAULT '?'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            username      VARCHAR(80)  NOT NULL UNIQUE,
            name          VARCHAR(150) NOT NULL,
            email         VARCHAR(150) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role          ENUM('admin','receptionist','customer','user') DEFAULT 'customer',
            is_active     BOOLEAN DEFAULT 1,
            phone         VARCHAR(20),
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS places (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            description TEXT,
            address     VARCHAR(255),
            phone       VARCHAR(50),
            website     VARCHAR(255),
            price_range VARCHAR(20)  DEFAULT 'Rs',
            category_id INT,
            image_url   VARCHAR(500),
            is_active   BOOLEAN DEFAULT 1,
            is_featured BOOLEAN DEFAULT 0,
            added_by    INT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
            FOREIGN KEY (added_by)    REFERENCES users(id)      ON DELETE SET NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            place_id   INT NOT NULL,
            user_id    INT NOT NULL,
            rating     INT NOT NULL,
            title      VARCHAR(255) NOT NULL,
            body       TEXT         NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY unique_review (place_id, user_id),
            FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id)  REFERENCES users(id)  ON DELETE CASCADE
        )
    """)

    # ── HOTEL MANAGEMENT TABLES ───────────────────────────────────────────────

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
            id          INT AUTO_INCREMENT PRIMARY KEY,
            invoice_id  INT NOT NULL,
            description VARCHAR(255) NOT NULL,
            quantity    DECIMAL(10,2) DEFAULT 1,
            unit_price  DECIMAL(10,2) NOT NULL,
            amount      DECIMAL(10,2) NOT NULL,
            item_type   ENUM('room','service','tax','discount','other') DEFAULT 'room',
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
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
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotel_settings (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            setting_key  VARCHAR(100) NOT NULL UNIQUE,
            setting_val  TEXT,
            updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hotel_services (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(150) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            category VARCHAR(50) DEFAULT 'general',
            icon VARCHAR(50) DEFAULT '🛎️',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            action VARCHAR(100) NOT NULL,
            details TEXT,
            ip_address VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )
    """)

    settings_defaults = [
        ('hotel_name',      'StaySmart Hotel & Suites'),
        ('hotel_address',   'Main Market Road, Sawantwadi 416510'),
        ('hotel_phone',     '+91 2363 272123'),
        ('hotel_email',     'info@staysmart.com'),
        ('check_in_time',   '12:00'),
        ('check_out_time',  '11:00'),
        ('gst_rate',        '12'),
        ('currency',        'INR'),
        ('currency_symbol', '₹')
    ]
    cur.executemany(
        "INSERT IGNORE INTO hotel_settings (setting_key, setting_val) VALUES (%s, %s)",
        settings_defaults
    )

    # ── SEED CATEGORIES ──────────────────────────────────────────────────────

    cats = [('Hotels','🏨'),('Cafes','☕'),('Restaurants','🍽️'),('Bakeries','🥐'),('Street Food','🌮')]
    cur.executemany("INSERT IGNORE INTO categories(name, icon) VALUES(%s, %s)", cats)

    # ── GUARD: skip seeding if data already exists ────────────────────────────
    cur.execute("SELECT COUNT(*) AS c FROM places")
    if cur.fetchone()[0] > 0:
        print('[SKIP] Database already seeded — skipping seed data insertion.')
        cur.close()
        conn.close()
        return

    # ── SEED USERS ───────────────────────────────────────────────────────────

    def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    users = [
        ('admin',        'Admin User',   'admin@localvocal.com', hp('admin123'), 'admin'),
        ('priya_sawant', 'Priya Sawant', 'priya@example.com',    hp('test1234'), 'user'),
        ('rahul_desai',  'Rahul Desai',  'rahul@example.com',    hp('test1234'), 'user'),
        ('sneha_patil',  'Sneha Patil',  'sneha@example.com',    hp('test1234'), 'user'),
        ('arjun_naik',   'Arjun Naik',   'arjun@example.com',    hp('test1234'), 'user'),
    ]
    cur.executemany(
        "INSERT IGNORE INTO users(username, name, email, password_hash, role) VALUES(%s,%s,%s,%s,%s)",
        users
    )

    # ── SEED PLACES ──────────────────────────────────────────────────────────

    cur.execute("SELECT id, name FROM categories")
    cat_map = {name: cid for cid, name in cur.fetchall()}

    places = [
        ('Hotel Sawant Palace',
         'A grand heritage-style hotel in the heart of Sawantwadi with rooftop views of the Western Ghats.',
         'Main Market Road, Sawantwadi 416510', '+91 2363 272123', '', '₹₹₹', cat_map.get('Hotels'),
         'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800', 1, 1),
        ('Konkan Heritage Inn',
         'Boutique property in mango orchards with authentic Malvani architecture and farm-to-table dining.',
         'Near Sawantwadi Lake, Off NH66, Sawantwadi 416510', '+91 9876543210', '', '₹₹₹₹', cat_map.get('Hotels'),
         'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800', 1, 1),
        ('Hotel Shreyas',
         'Budget-friendly stay near the MSRTC bus stand. A reliable choice for solo travellers.',
         'Near Bus Stand, Sawantwadi 416510', '+91 2363 272456', '', '₹', cat_map.get('Hotels'),
         'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800', 1, 0),
        ('Sindhudurg Resorts and Spa',
         'Luxury resort with pool, Ayurvedic spa, infinity deck and gourmet restaurant.',
         'Walaval Road, 4 km from Sawantwadi 416511', '+91 9988776655', '', '₹₹₹₹₹', cat_map.get('Hotels'),
         'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800', 1, 1),
        ('Hotel Pratap',
         'Mid-range hotel near the wooden toy market with local Malvani food.',
         'Palace Road, Sawantwadi 416510', '+91 2363 272789', '', '₹₹', cat_map.get('Hotels'),
         'https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=800', 1, 0),
        ('The Wooden Cup Cafe',
         'Artisanal cafe with specialty pour-over coffees and local lacquerware art.',
         'Near Rajwada Palace, Sawantwadi 416510', '+91 9823456789', '', '₹₹', cat_map.get('Cafes'),
         'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800', 1, 1),
        ('Mango Grove Cafe',
         'Open-air garden cafe under mango trees. Famous for kokum sarbat and Malvani snacks.',
         'Gaondevi Naka, Sawantwadi 416510', '+91 9765432100', '', '₹', cat_map.get('Cafes'),
         'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800', 1, 0),
        ('Malvani Khanaval',
         'Authentic home-style Malvani cooking. Must-try: Sol Kadhi, Kombdi Vade, Bangda Fry.',
         'Near Sawantwadi Lake, Sawantwadi 416510', '+91 9834567890', '', '₹₹', cat_map.get('Restaurants'),
         'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800', 1, 0),
        ('Ratnadeep Pure Veg',
         'Pure vegetarian restaurant with famous Maharashtrian thali with 12+ items.',
         'Main Road, Sawantwadi 416510', '+91 2363 273456', '', '₹', cat_map.get('Restaurants'),
         'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800', 1, 0),
        ('Goan Bake House',
         'Fresh Goan poi, bebinca, dodol every morning. Family-run for 35+ years.',
         'Near MSRTC Bus Stand, Sawantwadi 416510', '+91 9823001122', '', '₹', cat_map.get('Bakeries'),
         'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800', 1, 0),
        ('Sawantwadi Vada Pav Corner',
         'Legendary vada pav with a secret chutney recipe for 20 years. Open 7AM to 2PM only.',
         'Palace Chowk, Main Market, Sawantwadi 416510', '', '', '₹', cat_map.get('Street Food'),
         'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800', 1, 0),
    ]
    cur.executemany(
        """INSERT IGNORE INTO places
           (name, description, address, phone, website, price_range,
            category_id, image_url, is_active, is_featured)
           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        places
    )

    # ── SEED REVIEWS ─────────────────────────────────────────────────────────

    cur.execute("SELECT id, name     FROM places")
    place_map = {name: pid for pid, name in cur.fetchall()}

    cur.execute("SELECT id, username FROM users")
    user_map  = {uname: uid for uid, uname in cur.fetchall()}

    def pid(n): return place_map.get(n)
    def uid(u): return user_map.get(u)

    reviews = [
        (pid('Hotel Sawant Palace'),        uid('priya_sawant'), 5, 'Best hotel in Konkan!',       'Rooftop view of the Ghats at sunrise is unforgettable. Highly recommend!'),
        (pid('Hotel Sawant Palace'),        uid('rahul_desai'),  4, 'Great location',               'Centrally located. Rooms spacious and beds comfortable.'),
        (pid('Hotel Sawant Palace'),        uid('sneha_patil'),  5, 'Perfect for family vacation',  'Brought my parents here. Staff arranged a lovely surprise. Will return!'),
        (pid('Konkan Heritage Inn'),        uid('priya_sawant'), 5, 'Hidden paradise',              'Mango orchard setting is stunning. Best hosts I have met in Maharashtra.'),
        (pid('Konkan Heritage Inn'),        uid('arjun_naik'),   4, 'Beautiful but pricey',         'Ambience is unmatched. Slightly high price for room size.'),
        (pid('The Wooden Cup Cafe'),        uid('rahul_desai'),  5, 'Coffee changed my life',       'Ethiopian pour-over here is the best outside Mumbai. Love it!'),
        (pid('The Wooden Cup Cafe'),        uid('sneha_patil'),  4, 'Charming spot',                'Banana bread and kokum cheesecake were surprisingly great.'),
        (pid('Mango Grove Cafe'),           uid('priya_sawant'), 4, 'What a vibe!',                 'Spent 2 hours reading and sipping kokum sarbat. So relaxing.'),
        (pid('Malvani Khanaval'),           uid('rahul_desai'),  5, 'Best Malvani food, period.',   'Kombdi vade is crispy and perfectly spiced. Grandma-level cooking.'),
        (pid('Malvani Khanaval'),           uid('arjun_naik'),   5, 'A true Konkan gem',            'Sol kadhi alone was worth the trip. Go early!'),
        (pid('Ratnadeep Pure Veg'),         uid('sneha_patil'),  5, 'Unbeatable thali value',       '12 items all freshly made. Puranpoli and amti combo is divine.'),
        (pid('Goan Bake House'),            uid('priya_sawant'), 5, 'Best Goan bread outside Goa',  'Poi is fresh, soft and authentic. Bebinca is rich and perfect.'),
        (pid('Sawantwadi Vada Pav Corner'), uid('rahul_desai'),  5, 'The chutney is everything',    'Secret chutney in a league of its own. Come early, sells out by noon!'),
    ]
    valid = [(p, u, r, t, b) for p, u, r, t, b in reviews if p and u]
    cur.executemany(
        "INSERT IGNORE INTO reviews(place_id, user_id, rating, title, body) VALUES(%s,%s,%s,%s,%s)",
        valid
    )

    print(f'[OK] MySQL database `{db_name}` initialized with sample Sawantwadi data.')
    cur.close()
    conn.close()

if __name__ == '__main__':
    init_db()