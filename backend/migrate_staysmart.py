import os
import mysql.connector
import bcrypt
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'local_vocal_db'),
    'autocommit': True,
}

def migrate():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(buffered=True)

    print("[MIGRATION] Extending users table...")
    try:
        cur.execute("ALTER TABLE users MODIFY COLUMN role ENUM('admin', 'receptionist', 'customer', 'user') DEFAULT 'customer'")
    except Exception as e:
        print(f"Role alter warning: {e}")

    try:
        cur.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
    except Exception as e:
        print(f"is_active column: {e}")

    try:
        cur.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
    except Exception as e:
        print(f"phone column: {e}")

    print("[MIGRATION] Creating hotel_services table...")
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

    print("[MIGRATION] Creating activity_logs table...")
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

    # Seed hotel_services if empty
    cur.execute("SELECT COUNT(*) FROM hotel_services")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding hotel_services...")
        services = [
            ('Airport Shuttle & Pickup', 'Direct pickup and drop from Goa Dabolim or MOPA International Airport in private AC luxury sedan.', 1800.00, 'transport', '🚗', 1),
            ('Authentic Malvani Breakfast Buffet', 'Daily lavish morning buffet spread with fresh bakery items, Konkani poha, ghavane, fruits, juices & tea/coffee.', 350.00, 'dining', '🍳', 1),
            ('Ayurvedic Spa & Wellness Massage', '60-minute rejuvenating herbal full body massage by certified Ayurvedic therapists with steam bath.', 2200.00, 'wellness', '🌿', 1),
            ('24/7 In-Room Dining Service', 'Hot meals, local snacks, fresh beverages delivered promptly to your room anytime.', 0.00, 'dining', '🛎️', 1),
            ('Express Laundry & Dry Cleaning', 'Same-day washing, pressing, and delicate dry cleaning service for business & leisure attire.', 450.00, 'housekeeping', '👔', 1),
            ('Guided Sawantwadi Palace & Craft Tour', 'Curated tour of Sawantwadi Royal Palace, Ganjifa card makers, and wooden toy artisans.', 750.00, 'activities', '🏛️', 1)
        ]
        cur.executemany(
            """INSERT INTO hotel_services (name, description, price, category, icon, is_active)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            services
        )

    # Seed Receptionist & Customer demo users
    def hp(p): return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

    # Ensure admin has role 'admin'
    cur.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

    # Ensure receptionist user
    cur.execute("SELECT id FROM users WHERE username = 'receptionist'")
    rec = cur.fetchone()
    if not rec:
        print("[MIGRATION] Creating receptionist user...")
        cur.execute(
            """INSERT INTO users (username, name, email, password_hash, role, is_active, phone)
               VALUES (%s, %s, %s, %s, %s, 1, %s)""",
            ('receptionist', 'Sneha Kulkarni', 'receptionist@staysmart.com', hp('receptionist123'), 'receptionist', '+91 9822334455')
        )
    else:
        cur.execute("UPDATE users SET role = 'receptionist', is_active = 1 WHERE username = 'receptionist'")

    # Ensure demo customer user
    cur.execute("SELECT id FROM users WHERE username = 'customer'")
    cust = cur.fetchone()
    if not cust:
        print("[MIGRATION] Creating customer demo user...")
        cust_id = cur.execute(
            """INSERT INTO users (username, name, email, password_hash, role, is_active, phone)
               VALUES (%s, %s, %s, %s, %s, 1, %s)""",
            ('customer', 'Vikramaditya Rao', 'customer@staysmart.com', hp('customer123'), 'customer', '+91 9811223344')
        )
    else:
        cur.execute("UPDATE users SET role = 'customer', is_active = 1 WHERE username = 'customer'")

    # Map existing regular users to customer role
    cur.execute("UPDATE users SET role = 'customer' WHERE role = 'user' AND username NOT IN ('admin', 'receptionist')")

    # Link demo customer user to guest record
    cur.execute("SELECT id FROM users WHERE username = 'customer'")
    c_uid = cur.fetchone()[0]
    cur.execute("SELECT id FROM guests WHERE user_id = %s", (c_uid,))
    if not cur.fetchone():
        cur.execute("""
            INSERT INTO guests (user_id, full_name, email, phone, address, id_type, id_number, total_stays, notes)
            VALUES (%s, 'Vikramaditya Rao', 'customer@staysmart.com', '+91 9811223344', 'Indiranagar, Bengaluru, Karnataka', 'Passport', 'V9871234', 5, 'Frequent executive guest')
        """, (c_uid,))

    # Update hotel_settings to StaySmart branding if hotel_name exists
    cur.execute("UPDATE hotel_settings SET setting_val = 'StaySmart Hotel & Suites' WHERE setting_key = 'hotel_name'")

    # Seed sample activity logs if empty
    cur.execute("SELECT COUNT(*) FROM activity_logs")
    if cur.fetchone()[0] == 0:
        print("[MIGRATION] Seeding activity_logs...")
        cur.execute("SELECT id FROM users WHERE username = 'receptionist'")
        rec_id = cur.fetchone()[0]
        logs = [
            (rec_id, 'RECEPTIONIST_LOGIN', 'Receptionist Sneha Kulkarni logged into StaySmart PMS.', '127.0.0.1'),
            (rec_id, 'CHECK_IN_PROCESSED', 'Guest Rajesh Sharma checked into Room 102 (Booking BK-2026-001).', '127.0.0.1'),
            (rec_id, 'PAYMENT_RECORDED', 'Payment of ₹8,400.00 recorded for Invoice INV-2026-002 via Card.', '127.0.0.1'),
            (rec_id, 'HOUSEKEEPING_DISPATCHED', 'Urgent checkout clean dispatched for Room 202.', '127.0.0.1'),
            (1, 'ADMIN_SETTINGS_UPDATED', 'Hotel tax policies verified and currency set to INR (₹).', '127.0.0.1')
        ]
        cur.executemany(
            """INSERT INTO activity_logs (user_id, action, details, ip_address)
               VALUES (%s, %s, %s, %s)""",
            logs
        )

    print("[MIGRATION] Migration complete!")
    cur.close()
    conn.close()

if __name__ == '__main__':
    migrate()

