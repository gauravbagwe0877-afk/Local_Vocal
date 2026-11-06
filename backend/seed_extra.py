"""
seed_extra.py — Add more places per category to Local Vocal DB.
Run with:  python seed_extra.py

• Does NOT touch database.py at all.
• Uses INSERT IGNORE — completely safe to re-run multiple times.
• Adds 3–4 new places for each of the 5 categories:
    Hotels | Cafes | Restaurants | Bakeries | Street Food
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST', 'localhost'),
    'user':     os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'local_vocal_db'),
    'autocommit': True,
}

conn = mysql.connector.connect(**DB_CONFIG)
cur  = conn.cursor(buffered=True, dictionary=True)

# ── Fetch category IDs ─────────────────────────────────────────────────────────
cur.execute("SELECT id, name FROM categories")
cat_map = {row['name']: row['id'] for row in cur.fetchall()}

print("[INFO] Found categories:", list(cat_map.keys()))

# ── New places ────────────────────────────────────────────────────────────────
#  Each tuple:
#  (name, description, address, phone, website, price_range,
#   category_id, image_url, is_active, is_featured)

new_places = [

    # ── HOTELS ────────────────────────────────────────────────────────────────
    (
        'Hotel Malvan Darshan',
        'Comfortable mid-range hotel just 2 km from Sindhudurg Fort. Perfect base for beach and fort trips.',
        'Malvan Main Road, Malvan 416606', '+91 2365 252001', '', '₹₹',
        cat_map.get('Hotels'),
        'https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800',
        1, 0
    ),
    (
        'Tarkarli Beach Resort',
        'Eco-resort on the banks of Karli River with water sports, dolphin safaris and snorkelling packages.',
        'Tarkarli Beach Road, Malvan 416606', '+91 9823456700', 'https://tarkarliresort.in', '₹₹₹',
        cat_map.get('Hotels'),
        'https://images.unsplash.com/photo-1499793983690-e29da59ef1c2?w=800',
        1, 1
    ),
    (
        'Konkan Nest Homestay',
        'Traditional Konkan home immersed in cashew and coconut plantation. Home-cooked Malvani meals included.',
        'Vengurla Road, Near Shiroda, Sawantwadi 416512', '+91 9765001122', '', '₹₹',
        cat_map.get('Hotels'),
        'https://images.unsplash.com/photo-1510798831971-661eb04b3739?w=800',
        1, 0
    ),
    (
        'Green Valley Villa',
        'Hillside villa with panoramic Sahyadri views, private sit-out and bonfire facility on request.',
        'Amboli Ghat Road, 12 km from Sawantwadi 416505', '+91 9876001234', '', '₹₹₹',
        cat_map.get('Hotels'),
        'https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800',
        1, 0
    ),

    # ── CAFES ─────────────────────────────────────────────────────────────────
    (
        'Chaitanya Chai Corner',
        'Beloved local chai stall turned mini-cafe. Famous for masala cutting chai and khari biscuits.',
        'Near Palace Gate, Sawantwadi 416510', '', '', '₹',
        cat_map.get('Cafes'),
        'https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=800',
        1, 0
    ),
    (
        'The Konkan Brew Co.',
        'Specialty coffee roastery sourcing single-estate beans from Coorg. Cold brews and nitro coffee on tap.',
        'Station Road, Sawantwadi 416510', '+91 9823100200', '', '₹₹',
        cat_map.get('Cafes'),
        'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800',
        1, 1
    ),
    (
        'Seaside Sips Cafe',
        'Beachside cafe at Tarkarli serving smoothies, juices and Goan-style toasts with sea-view seating.',
        'Tarkarli Beach Promenade, Malvan 416606', '+91 9988001100', '', '₹₹',
        cat_map.get('Cafes'),
        'https://images.unsplash.com/photo-1442512595331-e89e73853f31?w=800',
        1, 0
    ),

    # ── RESTAURANTS ────────────────────────────────────────────────────────────
    (
        'Fish Tawa Restaurant',
        'Celebrated for its platters of Tawa-fried Surmai, Bangda and Pomfret. Eat at communal tables.',
        'Fish Market Lane, Malvan 416606', '+91 2365 252345', '', '₹₹',
        cat_map.get('Restaurants'),
        'https://images.unsplash.com/photo-1559339352-11d035aa65de?w=800',
        1, 1
    ),
    (
        'Annapurna Bhojanalay',
        'Classic Maharashtrian lunch-only thali with unlimited refills. Operated by a local self-help group.',
        'Near ST Stand, Sawantwadi 416510', '+91 2363 274100', '', '₹',
        cat_map.get('Restaurants'),
        'https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=800',
        1, 0
    ),
    (
        'Sindhudurg Spice Garden',
        'Open-air dining in a spice plantation setting. Speciality: whole-spice Malvani mutton curry.',
        'Spice Garden Road, Kudal 416520', '+91 9765432199', '', '₹₹₹',
        cat_map.get('Restaurants'),
        'https://images.unsplash.com/photo-1466978913421-dad2ebd01d17?w=800',
        1, 0
    ),
    (
        'Harbour View Seafood',
        'Open-deck restaurant overlooking Malvan Harbour. Grilled lobster and crab masala are house specials.',
        'Harbour Point, Malvan 416606', '+91 9823001999', '', '₹₹₹',
        cat_map.get('Restaurants'),
        'https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
        1, 1
    ),

    # ── BAKERIES ──────────────────────────────────────────────────────────────
    (
        'Konkan Bake Studio',
        'Modern artisan bakery with sourdough, focaccia and fusion mango-coconut tarts.',
        'New Market Complex, Sawantwadi 416510', '+91 9823400100', '', '₹₹',
        cat_map.get('Bakeries'),
        'https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800',
        1, 0
    ),
    (
        "Grandma's Sweet Shoppe",
        'Three-generation family shop making traditional Malvani chakli, chirote and modak every morning.',
        'Temple Street, Sawantwadi 416510', '+91 2363 272999', '', '₹',
        cat_map.get('Bakeries'),
        'https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800',
        1, 0
    ),
    (
        'Daily Bread Patisserie',
        'French-trained pastry chef runs this tiny gem. Croissants, macarons and Goan bebinca cheesecake.',
        'Civil Lines, Near Collectorate, Sawantwadi 416510', '+91 9988123456', '', '₹₹₹',
        cat_map.get('Bakeries'),
        'https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=800',
        1, 1
    ),

    # ── STREET FOOD ────────────────────────────────────────────────────────────
    (
        'Laxmi Misal Centre',
        'Legendary misal pav with dry and wet kolhapuri-style options. Queue expected from 8 AM.',
        'Main Bazar, Sawantwadi 416510', '', '', '₹',
        cat_map.get('Street Food'),
        'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=800',
        1, 1
    ),
    (
        'Bhuteshwar Bhel Corner',
        'Classic Mumbai-style bhel puri, sev puri and ragda pattice served from a colourful cart.',
        'Railway Station Road, Sawantwadi 416510', '', '', '₹',
        cat_map.get('Street Food'),
        'https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',
        1, 0
    ),
    (
        'Konkan Corn & Chaat Stall',
        'Roasted corn, masala peanuts and authentic Pune-style chaat. Evening-only, near the lake front.',
        'Lake Front, Sawantwadi 416510', '', '', '₹',
        cat_map.get('Street Food'),
        'https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=800',
        1, 0
    ),
    (
        'Malvan Pav Bhaji Wala',
        'Signature butter-loaded pav bhaji cooked on a giant iron tawa. Open evenings 5 PM – 11 PM.',
        'Near Bus Stand, Malvan 416606', '', '', '₹',
        cat_map.get('Street Food'),
        'https://images.unsplash.com/photo-1606755962773-d324e0a13086?w=800',
        1, 0
    ),
]

# ── Filter out any place where category wasn't found (safety check) ────────────
valid_places = [p for p in new_places if p[6] is not None]
skipped      = len(new_places) - len(valid_places)
if skipped:
    print(f"[WARN] {skipped} place(s) skipped — category ID not found.")

# ── Insert ─────────────────────────────────────────────────────────────────────
insert_sql = """
    INSERT IGNORE INTO places
        (name, description, address, phone, website, price_range,
         category_id, image_url, is_active, is_featured)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""
cur.executemany(insert_sql, valid_places)

print(f"[OK] Attempted to insert {len(valid_places)} new places.")
print("     (Duplicates are silently skipped thanks to INSERT IGNORE.)")

cur.close()
conn.close()
