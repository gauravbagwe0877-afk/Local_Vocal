"""
seed_category_images.py
Adds inside images for ALL non-hotel categories (Cafes, Restaurants,
Bakeries, Street Food) into the place_images table.

Safe to run multiple times — skips any place that already has images.

Usage:
    cd backend
    python seed_category_images.py
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

# ── Image data keyed by place name ───────────────────────────────────────────
# Each entry: (image_url, caption, display_order)

PLACE_IMAGES = {

    # ── CAFES ────────────────────────────────────────────────────────────────

    'The Wooden Cup Cafe': [
        ('https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=800',
         'Cosy Indoor Seating Area', 1),
        ('https://images.unsplash.com/photo-1509042239860-f550ce710b93?w=800',
         'Signature Pour-Over Coffee', 2),
        ('https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800',
         'Artisan Espresso Bar', 3),
        ('https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=800',
         'Handcrafted Latte Art', 4),
        ('https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800',
         'Lacquerware Décor & Cafe Vibes', 5),
    ],

    'Mango Grove Cafe': [
        ('https://images.unsplash.com/photo-1511920170033-f8396924c348?w=800',
         'Open-Air Garden Seating', 1),
        ('https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=800',
         'Under the Mango Trees', 2),
        ('https://images.unsplash.com/photo-1561339429-4b8dced7c4c5?w=800',
         'Chilled Kokum Sarbat', 3),
        ('https://images.unsplash.com/photo-1541167760496-1628856ab772?w=800',
         'Refreshing Cold Beverage Menu', 4),
    ],

    # ── RESTAURANTS ──────────────────────────────────────────────────────────

    'Malvani Khanaval': [
        ('https://images.unsplash.com/photo-1585937421612-70a008356fbe?w=800',
         'Traditional Malvani Thali', 1),
        ('https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=800',
         'Kombdi Vade & Sol Kadhi', 2),
        ('https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?w=800',
         'Authentic Bangda Fish Fry', 3),
        ('https://images.unsplash.com/photo-1601050690117-94f5f7a419a8?w=800',
         'Home-Style Dining Setting', 4),
        ('https://images.unsplash.com/photo-1504674900247-0877df9cc836?w=800',
         "Chef's Special Coconut Curry", 5),
    ],

    'Ratnadeep Pure Veg': [
        ('https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=800',
         'Maharashtrian Thali — 12 Items', 1),
        ('https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=800',
         'Fresh Puranpoli & Amti', 2),
        ('https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800',
         'Pure Veg Spread', 3),
        ('https://images.unsplash.com/photo-1567337710282-00832b415979?w=800',
         'Clean & Welcoming Dining Hall', 4),
    ],

    # ── BAKERIES ─────────────────────────────────────────────────────────────

    'Goan Bake House': [
        ('https://images.unsplash.com/photo-1517433670267-08bbd4be890f?w=800',
         'Fresh Goan Poi Straight from the Oven', 1),
        ('https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=800',
         'Bebinca & Traditional Goan Sweets', 2),
        ('https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=800',
         'Artisanal Bread Loaves', 3),
        ('https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=800',
         'Morning Pastry Selection', 4),
        ('https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=800',
         '35-Year Family Bakery Counter', 5),
    ],

    # ── STREET FOOD ──────────────────────────────────────────────────────────

    'Sawantwadi Vada Pav Corner': [
        ('https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=800',
         'Legendary Secret-Chutney Vada Pav', 1),
        ('https://images.unsplash.com/photo-1565299507177-b0ac66763828?w=800',
         'Fresh Batata Vada Filling', 2),
        ('https://images.unsplash.com/photo-1565958011703-44f9829ba187?w=800',
         'Crispy Golden Vadas', 3),
        ('https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',
         'Palace Chowk Morning Rush', 4),
    ],
}


def run():
    conn = conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor(buffered=True)

    # Ensure table exists (idempotent)
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

    # Fetch place name → id map
    cur.execute('SELECT id, name FROM places')
    place_map = {name: pid for pid, name in cur.fetchall()}

    total_inserted = 0

    for place_name, images in PLACE_IMAGES.items():
        place_id = place_map.get(place_name)
        if not place_id:
            print(f'[SKIP] Place not found in DB: {place_name!r}')
            continue

        # Check if images already seeded for this place
        cur.execute('SELECT COUNT(*) FROM place_images WHERE place_id = %s', (place_id,))
        if cur.fetchone()[0] > 0:
            print(f'[SKIP] {place_name!r} already has images — skipping.')
            continue

        rows = [(place_id, url, caption, order) for url, caption, order in images]
        cur.executemany(
            'INSERT INTO place_images (place_id, image_url, caption, display_order) VALUES (%s,%s,%s,%s)',
            rows
        )
        total_inserted += len(rows)
        print(f'[OK]   {place_name!r} — {len(rows)} images seeded.')

    cur.close()
    conn.close()

    if total_inserted:
        print(f'\n[DONE] {total_inserted} new images added across all categories.')
    else:
        print('\n[DONE] All places already had images — nothing new to seed.')


if __name__ == '__main__':
    run()
