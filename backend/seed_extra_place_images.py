"""
seed_extra_place_images.py
Adds inside images for all extra places (added via seed_extra.py) that
don't yet have images in place_images.

Safe to run multiple times — skips any place that already has images.

Usage:
    cd backend
    python seed_extra_place_images.py
"""

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

DB_CONFIG = {
    'host':       os.environ.get('DB_HOST', 'localhost'),
    'user':       os.environ.get('DB_USER', 'root'),
    'password':   os.environ.get('DB_PASSWORD', ''),
    'database':   os.environ.get('DB_NAME', 'local_vocal_db'),
    'autocommit': True,
}

# ── Image data for all extra places ──────────────────────────────────────────
# Format: 'Place Name': [(url, caption, display_order), ...]

PLACE_IMAGES = {

    # ════════════════════════════════════════════════════════════════
    # HOTELS
    # ════════════════════════════════════════════════════════════════

    'Hotel Malvan Darshan': [
        ('https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800',
         'Spacious Deluxe Room', 1),
        ('https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800',
         'Hotel Exterior with Sea View', 2),
        ('https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800',
         'Comfortable King-Size Room', 3),
        ('https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800',
         'Neat & Clean Room Interior', 4),
    ],

    'Tarkarli Beach Resort': [
        ('https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800',
         'Beachside Infinity Pool', 1),
        ('https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800',
         'Resort Spa & Wellness Centre', 2),
        ('https://images.unsplash.com/photo-1506059612708-99d6128a6e72?w=800',
         'Ocean-View Premium Cottage', 3),
        ('https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800',
         'Lush Tropical Resort Grounds', 4),
        ('https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800',
         'Sunset Deck & Bar', 5),
    ],

    'Konkan Nest Homestay': [
        ('https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800',
         'Warm & Homely Guest Room', 1),
        ('https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800',
         'Traditional Konkan Interior', 2),
        ('https://images.unsplash.com/photo-1505693314120-0d443867891c?w=800',
         'Peaceful Garden View', 3),
        ('https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?w=800',
         'Cosy Common Sitting Area', 4),
    ],

    'Green Valley Villa': [
        ('https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800',
         'Private Villa with Valley View', 1),
        ('https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=800',
         'Breezy Terrace & Lounge', 2),
        ('https://images.unsplash.com/photo-1631049552057-403cdb8f0658?w=800',
         'Villa Master Bedroom', 3),
        ('https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800',
         'Modern Private Bathroom', 4),
        ('https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800',
         'Open-Air Dining Pavilion', 5),
    ],

    # ════════════════════════════════════════════════════════════════
    # CAFES
    # ════════════════════════════════════════════════════════════════

    'Chaitanya Chai Corner': [
        ('https://images.unsplash.com/photo-1556742400-b5b7c512e4b8?w=800',
         'Steaming Masala Chai', 1),
        ('https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=800',
         'Cosy Corner Seating', 2),
        ('https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=800',
         'Freshly Brewed Cutting Chai', 3),
        ('https://images.unsplash.com/photo-1567620832903-9fc6debc209f?w=800',
         'Chai with Biscuits & Snacks', 4),
    ],

    'The Konkan Brew Co.': [
        ('https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800',
         'Specialty Coffee Bar', 1),
        ('https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800',
         'Signature Latte Art', 2),
        ('https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800',
         'Rustic Industrial Café Décor', 3),
        ('https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800',
         'House-Baked Pastries', 4),
        ('https://images.unsplash.com/photo-1511920170033-f8396924c348?w=800',
         'Outdoor Terrace Seating', 5),
    ],

    'Seaside Sips Cafe': [
        ('https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800',
         'Breezy Seaside Seating', 1),
        ('https://images.unsplash.com/photo-1561339429-4b8dced7c4c5?w=800',
         'Fresh Fruit Mocktails', 2),
        ('https://images.unsplash.com/photo-1541167760496-1628856ab772?w=800',
         'Cold Brew & Smoothie Bar', 3),
        ('https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=800',
         'Relaxed Indoor Lounge', 4),
    ],

    # ════════════════════════════════════════════════════════════════
    # RESTAURANTS
    # ════════════════════════════════════════════════════════════════

    'Fish Tawa Restaurant': [
        ('https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
         'Fresh Tawa Fish Fry', 1),
        ('https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',
         'Coastal Seafood Platter', 2),
        ('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',
         'Crab & Prawn Specialties', 3),
        ('https://images.unsplash.com/photo-1601050690117-94f5f7a419a8?w=800',
         'Open-Air Waterfront Dining', 4),
        ('https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800',
         'Malvan Fish Thali', 5),
    ],

    'Annapurna Bhojanalay': [
        ('https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',
         'Full Maharashtrian Thali', 1),
        ('https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800',
         'Dal, Bhakri & Usal Spread', 2),
        ('https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800',
         'Simple & Wholesome Meals', 3),
        ('https://images.unsplash.com/photo-1567337710282-00832b415979?w=800',
         'Welcoming Dining Hall', 4),
    ],

    'Sindhudurg Spice Garden': [
        ('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',
         'Spice-Infused Restaurant Ambience', 1),
        ('https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800',
         'Konkan Spice Thali', 2),
        ('https://images.unsplash.com/photo-1601050690117-94f5f7a419a8?w=800',
         'Garden Seating Area', 3),
        ('https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',
         'Aromatic Chef Specials', 4),
        ('https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
         'Fresh Local Ingredients', 5),
    ],

    'Harbour View Seafood': [
        ('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',
         'Grilled Jumbo Prawns', 1),
        ('https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
         'Harbour-Fresh Fish Fry', 2),
        ('https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',
         'Coastal Seafood Curry Bowl', 3),
        ('https://images.unsplash.com/photo-1601050690117-94f5f7a419a8?w=800',
         'Scenic Harbour View Dining', 4),
    ],

    # ════════════════════════════════════════════════════════════════
    # BAKERIES
    # ════════════════════════════════════════════════════════════════

    'Konkan Bake Studio': [
        ('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800',
         'Artisan Bread Selection', 1),
        ('https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800',
         'Fresh-Baked Morning Loaves', 2),
        ('https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=800',
         'Konkan-Inspired Pastries', 3),
        ('https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800',
         'Cake & Dessert Display', 4),
        ('https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800',
         'Modern Bakery Studio Interior', 5),
    ],

    "Grandma's Sweet Shoppe": [
        ('https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=800',
         'Traditional Indian Mithai', 1),
        ('https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800',
         'Laddoo & Barfi Display', 2),
        ('https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800',
         'Homemade Sweets Counter', 3),
        ('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800',
         'Festive Sweet Hampers', 4),
    ],

    'Daily Bread Patisserie': [
        ('https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800',
         'French-Style Croissants', 1),
        ('https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800',
         'Sourdough & Focaccia Loaves', 2),
        ('https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800',
         'Patisserie Cake Counter', 3),
        ('https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=800',
         'Morning Pastry Basket', 4),
        ('https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800',
         'Bright & Airy Bakery Interior', 5),
    ],

    # ════════════════════════════════════════════════════════════════
    # STREET FOOD
    # ════════════════════════════════════════════════════════════════

    'Laxmi Misal Centre': [
        ('https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800',
         'Spicy Kolhapuri Misal Pav', 1),
        ('https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
         'Street-Style Tari Misal', 2),
        ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800',
         'Classic Misal with Farsan Topping', 3),
        ('https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',
         'Busy Morning Street Counter', 4),
    ],

    'Bhuteshwar Bhel Corner': [
        ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800',
         'Crispy Bhel Puri Bowl', 1),
        ('https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
         'Sev Puri & Pani Puri Cart', 2),
        ('https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800',
         'Tangy Tamarind Chutney', 3),
        ('https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',
         'Busy Evening Chaat Stall', 4),
    ],

    'Konkan Corn & Chaat Stall': [
        ('https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
         'Roasted Masala Corn on the Cob', 1),
        ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800',
         'Schezwan Corn Cup', 2),
        ('https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800',
         'Pav Bhaji & Chaat Combo', 3),
        ('https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',
         'Colourful Street Food Spread', 4),
    ],

    'Malvan Pav Bhaji Wala': [
        ('https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800',
         'Sizzling Butter Pav Bhaji', 1),
        ('https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',
         'Coastal-Style Bhaji with Extra Butter', 2),
        ('https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
         'Spiced Vegetable Filling', 3),
        ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800',
         'Evening Street Stall Crowd', 4),
    ],
}


def run():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor(buffered=True)

    # Ensure table exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS place_images (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            place_id      INT          NOT NULL,
            image_url     VARCHAR(500) NOT NULL,
            caption       VARCHAR(255) DEFAULT '',
            display_order INT          DEFAULT 0,
            FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
        )
    """)

    cur.execute('SELECT id, name FROM places')
    place_map = {name: pid for pid, name in cur.fetchall()}

    total_inserted = 0
    skipped        = 0
    not_found      = 0

    for place_name, images in PLACE_IMAGES.items():
        place_id = place_map.get(place_name)
        if not place_id:
            print(f'[SKIP] Not in DB: {place_name!r}')
            not_found += 1
            continue

        cur.execute('SELECT COUNT(*) FROM place_images WHERE place_id = %s', (place_id,))
        if cur.fetchone()[0] > 0:
            print(f'[SKIP] Already has images: {place_name!r}')
            skipped += 1
            continue

        rows = [(place_id, url, caption, order) for url, caption, order in images]
        cur.executemany(
            'INSERT INTO place_images (place_id, image_url, caption, display_order) '
            'VALUES (%s,%s,%s,%s)',
            rows
        )
        total_inserted += len(rows)
        print(f'[OK]   {place_name!r} — {len(rows)} images seeded.')

    cur.close()
    conn.close()

    print(f'\n[DONE] {total_inserted} images inserted | '
          f'{skipped} already seeded | {not_found} places not found in DB.')


if __name__ == '__main__':
    run()
