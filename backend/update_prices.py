"""
update_prices.py — Replace ₹-symbol price_range with real prices for all places.

Run with:  python update_prices.py

• Does NOT touch database.py, app.py, or any other existing file.
• Updates the existing `price_range` column — templates already display it
  via {{ place.price_range }} in .card-price and .featured-price badges.
• Safe to re-run — just UPDATEs by place name, no duplicates possible.

Price guide used:
  Hotels      → ₹X,XXX/night
  Cafes       → ₹XX/person
  Restaurants → ₹XXX/person
  Bakeries    → ₹XX/person
  Street Food → ₹XX/plate
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
cur  = conn.cursor(buffered=True)

# ── Price mapping: (place_name, new_price_display) ────────────────────────────
#    Format kept short so it fits the badge on the card image.
prices = [

    # ── Hotels (per night) ────────────────────────────────────────────────────
    ('Hotel Sawant Palace',         '₹3,500/night'),
    ('Konkan Heritage Inn',         '₹6,500/night'),
    ('Hotel Shreyas',               '₹800/night'),
    ('Sindhudurg Resorts and Spa',  '₹12,000/night'),
    ('Hotel Pratap',                '₹1,800/night'),
    ('Hotel Malvan Darshan',        '₹1,500/night'),
    ('Tarkarli Beach Resort',       '₹4,200/night'),
    ('Konkan Nest Homestay',        '₹2,200/night'),
    ('Green Valley Villa',          '₹3,800/night'),

    # ── Cafes (per person) ────────────────────────────────────────────────────
    ('The Wooden Cup Cafe',         '₹200/person'),
    ('Mango Grove Cafe',            '₹120/person'),
    ('Chaitanya Chai Corner',       '₹30/person'),
    ('The Konkan Brew Co.',         '₹280/person'),
    ('Seaside Sips Cafe',           '₹220/person'),

    # ── Restaurants (per person) ──────────────────────────────────────────────
    ('Malvani Khanaval',            '₹350/person'),
    ('Ratnadeep Pure Veg',          '₹180/person'),
    ('Fish Tawa Restaurant',        '₹450/person'),
    ('Annapurna Bhojanalay',        '₹150/person'),
    ('Sindhudurg Spice Garden',     '₹550/person'),
    ('Harbour View Seafood',        '₹800/person'),

    # ── Bakeries (per person) ─────────────────────────────────────────────────
    ('Goan Bake House',             '₹80/person'),
    ('Konkan Bake Studio',          '₹220/person'),
    ("Grandma's Sweet Shoppe",      '₹100/person'),
    ('Daily Bread Patisserie',      '₹350/person'),

    # ── Street Food (per plate) ───────────────────────────────────────────────
    ('Sawantwadi Vada Pav Corner',  '₹20/plate'),
    ('Laxmi Misal Centre',          '₹60/plate'),
    ('Bhuteshwar Bhel Corner',      '₹50/plate'),
    ('Konkan Corn & Chaat Stall',   '₹40/plate'),
    ('Malvan Pav Bhaji Wala',       '₹80/plate'),
]

# ── Apply updates ──────────────────────────────────────────────────────────────
updated  = 0
notfound = []

for name, price in prices:
    cur.execute(
        "UPDATE places SET price_range = %s WHERE name = %s",
        (price, name)
    )
    if cur.rowcount > 0:
        updated += 1
        print(f"  [OK] {name:40s} -> {price}")
    else:
        notfound.append(name)

print(f"\n[DONE] {updated}/{len(prices)} places updated.")

if notfound:
    print(f"[WARN] {len(notfound)} place(s) not found in DB (check name spelling):")
    for n in notfound:
        print(f"       • {n}")

cur.close()
conn.close()
