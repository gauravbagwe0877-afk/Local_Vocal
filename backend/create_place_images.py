"""
Migration: Create place_images table and seed hotel inside images.
Run once: python create_place_images.py
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


def run():
    conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor(buffered=True)

    # ── Create table ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS place_images (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            place_id      INT         NOT NULL,
            image_url     VARCHAR(500) NOT NULL,
            caption       VARCHAR(255) DEFAULT '',
            display_order INT          DEFAULT 0,
            FOREIGN KEY (place_id) REFERENCES places(id) ON DELETE CASCADE
        )
    """)
    print('[OK] place_images table ready.')

    # ── Guard ─────────────────────────────────────────────────────────────────
    cur.execute('SELECT COUNT(*) FROM place_images')
    if cur.fetchone()[0] > 0:
        print('[SKIP] place_images already seeded — nothing to do.')
        cur.close()
        conn.close()
        return

    # ── Fetch existing place IDs ───────────────────────────────────────────────
    cur.execute('SELECT id, name FROM places')
    place_map = {name: pid for pid, name in cur.fetchall()}

    images = []

    # ── Hotel Sawant Palace — Heritage rooftop property ───────────────────────
    if p := place_map.get('Hotel Sawant Palace'):
        images += [
            (p, 'https://images.unsplash.com/photo-1631049307264-da0ec9d70304?w=800',
             'Deluxe Room with Ghat View', 1),
            (p, 'https://images.unsplash.com/photo-1611892440504-42a792e24d32?w=800',
             'Elegantly Furnished Bedroom', 2),
            (p, 'https://images.unsplash.com/photo-1584132967334-10e028bd69f7?w=800',
             'Premium En-Suite Bathroom', 3),
            (p, 'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800',
             'Heritage Dining Hall', 4),
            (p, 'https://images.unsplash.com/photo-1566195992011-5f6b21e539aa?w=800',
             'Rooftop Terrace — Sunset Views', 5),
        ]

    # ── Konkan Heritage Inn — Boutique mango-orchard stay ─────────────────────
    if p := place_map.get('Konkan Heritage Inn'):
        images += [
            (p, 'https://images.unsplash.com/photo-1618773928121-c32242e63f39?w=800',
             'Heritage Suite Interior', 1),
            (p, 'https://images.unsplash.com/photo-1540518614846-7eded433c457?w=800',
             'Cozy Malvani-Style Room', 2),
            (p, 'https://images.unsplash.com/photo-1505693314120-0d443867891c?w=800',
             'Mango Orchard Garden View', 3),
            (p, 'https://images.unsplash.com/photo-1496417263034-38ec4f0b665a?w=800',
             'Private Sitting Nook', 4),
            (p, 'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800',
             'Farm-to-Table Dining Area', 5),
        ]

    # ── Hotel Shreyas — Budget travellers' pick ───────────────────────────────
    if p := place_map.get('Hotel Shreyas'):
        images += [
            (p, 'https://images.unsplash.com/photo-1631049552057-403cdb8f0658?w=800',
             'Clean Standard Room', 1),
            (p, 'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800',
             'Hotel Reception & Lobby', 2),
            (p, 'https://images.unsplash.com/photo-1578683010236-d716f9a3f461?w=800',
             'Comfortable Twin Room', 3),
        ]

    # ── Sindhudurg Resorts and Spa — Luxury infinity pool resort ──────────────
    if p := place_map.get('Sindhudurg Resorts and Spa'):
        images += [
            (p, 'https://images.unsplash.com/photo-1540555700478-4be289fbecef?w=800',
             'Ayurvedic Spa Treatment Room', 1),
            (p, 'https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=800',
             'Infinity Pool with Valley Views', 2),
            (p, 'https://images.unsplash.com/photo-1506059612708-99d6128a6e72?w=800',
             'Premium Luxury Suite', 3),
            (p, 'https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800',
             'Resort Exterior & Manicured Gardens', 4),
            (p, 'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800',
             'Grand Pool Deck at Dusk', 5),
        ]

    # ── Hotel Pratap — Mid-range near toy market ───────────────────────────────
    if p := place_map.get('Hotel Pratap'):
        images += [
            (p, 'https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=800',
             'Standard Double Room', 1),
            (p, 'https://images.unsplash.com/photo-1586611292717-f828b167408c?w=800',
             'In-House Malvani Restaurant', 2),
            (p, 'https://images.unsplash.com/photo-1566773544914-4a4fe2f4e4fb?w=800',
             'Hotel Lobby & Check-in', 3),
        ]

    if images:
        cur.executemany(
            'INSERT INTO place_images (place_id, image_url, caption, display_order) VALUES (%s,%s,%s,%s)',
            images
        )
        print(f'[OK] Seeded {len(images)} hotel inside images across {len(set(i[0] for i in images))} hotels.')
    else:
        print('[WARN] No matching hotels found — check place names in DB.')

    cur.close()
    conn.close()
    print('[DONE] Hotel image migration complete.')


if __name__ == '__main__':
    run()
