"""
seed_reviews_extra.py — Seed sample reviews for the new places (ids 12-29).

Run with:  python seed_reviews_extra.py

• Does NOT touch database.py, app.py, or any existing file.
• Uses INSERT IGNORE — completely safe to re-run multiple times.
• Reviews are distributed across the 4 seeded users so avg_rating
  is populated for every new place, making the detail page render
  correctly and the "Write a Review" form visible to logged-in users.
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

# ── Fetch place & user maps ────────────────────────────────────────────────────
cur.execute("SELECT id, name FROM places WHERE id >= 12")
place_map = {row['name']: row['id'] for row in cur.fetchall()}

cur.execute("SELECT id, username FROM users")
user_map  = {row['username']: row['id'] for row in cur.fetchall()}

def pid(n): return place_map.get(n)
def uid(u): return user_map.get(u)

print("[INFO] New places found:", list(place_map.keys()))

# ── Reviews for new places ─────────────────────────────────────────────────────
# Format: (place_name, username, rating, title, body)
reviews_data = [

    # ── HOTELS (ids 12-15) ────────────────────────────────────────────────────
    ('Hotel Malvan Darshan', 'priya_sawant', 4,
     'Solid base for Sindhudurg trips',
     'Clean rooms, helpful staff and very close to the fort jetty. Good value for money.'),
    ('Hotel Malvan Darshan', 'rahul_desai', 4,
     'Comfortable stay',
     'Decent AC rooms and quick checkout. Nothing fancy but exactly what a traveller needs.'),

    ('Tarkarli Beach Resort', 'arjun_naik', 5,
     'Paradise on the Karli River!',
     'Woke up to dolphins jumping outside our cottage. The SCUBA package was world-class. Must visit!'),
    ('Tarkarli Beach Resort', 'sneha_patil', 5,
     'Best resort in Konkan',
     'Spotless beach-front cottages, transparent kayaking and the most peaceful sunset I have ever seen.'),
    ('Tarkarli Beach Resort', 'priya_sawant', 4,
     'Great experience, slightly expensive',
     'The water sports and food were amazing. A little pricey but you get what you pay for.'),

    ('Konkan Nest Homestay', 'rahul_desai', 5,
     'Felt like home in the jungle',
     'Host aunty cooked the most authentic solkadhi and ukadiche modak. The cashew plantation walk is unforgettable.'),
    ('Konkan Nest Homestay', 'priya_sawant', 5,
     'Hidden gem homestay',
     'No wifi, no problem. Fresh coconuts from the garden, star-gazing on the terrace. Pure bliss.'),

    ('Green Valley Villa', 'arjun_naik', 4,
     'Stunning Sahyadri views',
     'The private sit-out with misty valley views was magical. Bonfire on the second night was a highlight.'),
    ('Green Valley Villa', 'sneha_patil', 5,
     'Perfect hill retreat',
     'Woke up to clouds rolling over the valley. Super clean villa with a fully-equipped kitchen.'),

    # ── CAFES (ids 16-18) ─────────────────────────────────────────────────────
    ('Chaitanya Chai Corner', 'rahul_desai', 5,
     'Best cutting chai in Konkan',
     'The masala chai here is a whole mood. Ginger-cardamom balance is perfect. Goes great with khari.'),
    ('Chaitanya Chai Corner', 'sneha_patil', 4,
     'Old-school charm',
     'Small and crowded but the chai is worth it. Open since dawn — perfect pre-trek fuel.'),

    ('The Konkan Brew Co.', 'priya_sawant', 5,
     'Single-origin coffee in Konkan? Yes!',
     'Had their Coorg natural process espresso and it blew my mind. The pour-over ritual is a beautiful experience.'),
    ('The Konkan Brew Co.', 'arjun_naik', 5,
     'Nitro coffee changes everything',
     'Nitro cold brew on tap in Sawantwadi — never expected this! Rich, creamy and absolutely zero bitterness.'),
    ('The Konkan Brew Co.', 'rahul_desai', 4,
     'Excellent beans, loved the vibe',
     'Great selection of origins and the staff knows their coffee. Takes a while but totally worth the wait.'),

    ('Seaside Sips Cafe', 'sneha_patil', 5,
     'Mango smoothie with sea view',
     'The freshest mango smoothie I have had, with waves crashing 20 metres away. What more do you want?'),
    ('Seaside Sips Cafe', 'priya_sawant', 4,
     'Perfect beach afternoon',
     'Avocado toast + tender coconut water = perfect Tarkarli afternoon. The sea view seating is gorgeous.'),

    # ── RESTAURANTS (ids 19-22) ───────────────────────────────────────────────
    ('Fish Tawa Restaurant', 'arjun_naik', 5,
     'Greatest Surmai of my life',
     'Surmai tawa fry is perfectly crisp outside, juicy inside. The masala coating is a closely guarded secret.'),
    ('Fish Tawa Restaurant', 'rahul_desai', 5,
     'Fresh catch, straight to the tawa',
     'They walk you to the fish counter to pick your catch. Does not get fresher than this. Absolute must.'),
    ('Fish Tawa Restaurant', 'sneha_patil', 4,
     'Loud, fun and delicious',
     'Communal tables, no frills and insanely good fish. Bangda fry was outstanding. Go hungry!'),

    ('Annapurna Bhojanalay', 'priya_sawant', 5,
     'Unlimited thali with heart',
     'Run by a self-help group of local women. Puranpoli, amti, rice, 8 other items — all unlimited. Incredible.'),
    ('Annapurna Bhojanalay', 'sneha_patil', 5,
     'Best value lunch in Sawantwadi',
     'Could not believe how much food I got for the price. The dal tadka and papad were perfect.'),

    ('Sindhudurg Spice Garden', 'rahul_desai', 5,
     'Dinner in a spice plantation',
     'Walked through cardamom and pepper vines before sitting down to the most fragrant mutton curry ever made.'),
    ('Sindhudurg Spice Garden', 'arjun_naik', 4,
     'Unique atmosphere, great food',
     'The outdoor setting is one of a kind. Whole-spice curry is intensely flavoured. Booking in advance is essential.'),

    ('Harbour View Seafood', 'priya_sawant', 5,
     'Grilled lobster with harbour lights',
     'Watching fishing boats return as we ate lobster on the open deck — best dinner of the entire Konkan trip.'),
    ('Harbour View Seafood', 'sneha_patil', 4,
     'Crab masala is a showstopper',
     'Fresh crab in thick coconut masala — messy, delicious and very addictive. Service was attentive.'),
    ('Harbour View Seafood', 'rahul_desai', 5,
     'Seafood lovers, this is it',
     'Ordered the mixed seafood platter. Everything — prawns, squid, fish, crab — was perfectly cooked.'),

    # ── BAKERIES (ids 23-25) ──────────────────────────────────────────────────
    ('Konkan Bake Studio', 'arjun_naik', 4,
     'Sourdough in Sawantwadi!',
     'Properly fermented sourdough with a great crust. Mango-coconut tart was creative and delicious.'),
    ('Konkan Bake Studio', 'priya_sawant', 5,
     'Modern bakery done right',
     'The focaccia with olive oil and rosemary was better than anything I had in Mumbai. Highly recommend.'),

    ("Grandma's Sweet Shoppe", 'rahul_desai', 5,
     'Chirote that tastes like childhood',
     'Three-generation recipe and you can taste the love. Chakli is perfectly crunchy, modak is divine.'),
    ("Grandma's Sweet Shoppe", 'sneha_patil', 5,
     'Traditional sweets done to perfection',
     'Bought a kg of chakli and it was gone before the train home. Absolutely authentic Malvani taste.'),
    ("Grandma's Sweet Shoppe", 'arjun_naik', 4,
     'A little piece of tradition',
     'Open only until stock lasts — go early. The modak filling is uniquely flavoured with coconut jaggery.'),

    ('Daily Bread Patisserie', 'priya_sawant', 5,
     'French pastry in Konkan — incredible!',
     'Buttery croissant, pistachio macaron and bebinca cheesecake. I did not expect this level of skill here.'),
    ('Daily Bread Patisserie', 'arjun_naik', 4,
     'The bebinca cheesecake is genius',
     'A fusion of Goan bebinca and New York cheesecake — rich, layered and unique. Worth every rupee.'),

    # ── STREET FOOD (ids 26-29) ───────────────────────────────────────────────
    ('Laxmi Misal Centre', 'sneha_patil', 5,
     'Kolhapuri misal done properly',
     'The dry misal with extra tarri was fire — literally. Crispy farsan, raw onion, lemon. Life complete.'),
    ('Laxmi Misal Centre', 'rahul_desai', 5,
     'Queue at 7:45 AM, no regrets',
     'Arrived before 8 and still had to wait 20 minutes. Worth every second. Best misal I have had.'),
    ('Laxmi Misal Centre', 'arjun_naik', 4,
     'Spicy and absolutely addictive',
     'Not for the faint-hearted but the heat is balanced by the sweet coconut chutney. Top class misal.'),

    ('Bhuteshwar Bhel Corner', 'priya_sawant', 4,
     'Mumbai-style bhel in Sawantwadi',
     'Tangy tamarind chutney, crispy sev, fresh onion and tomato. The sev puri is light and perfectly balanced.'),
    ('Bhuteshwar Bhel Corner', 'sneha_patil', 4,
     'Great evening snack spot',
     'Ragda pattice was my favourite — well-seasoned pattice with thick peas curry. Great street food.'),

    ('Konkan Corn & Chaat Stall', 'rahul_desai', 4,
     'Perfect lakefront evening',
     'Roasted corn slathered in butter, lime and paprika while watching the Sawantwadi lake reflect the sunset.'),
    ('Konkan Corn & Chaat Stall', 'arjun_naik', 4,
     'Masala peanuts are dangerously good',
     'One cone of masala peanuts turned into three. The chaat is fresh and loaded with chutneys.'),

    ('Malvan Pav Bhaji Wala', 'priya_sawant', 5,
     'Butter overload — 10/10',
     'The iron tawa is soaked in butter and the bhaji is thick, spiced and deeply satisfying. Show-stopping pav bhaji.'),
    ('Malvan Pav Bhaji Wala', 'sneha_patil', 5,
     'Open till 11 PM — lifesaver',
     'After a long beach day, this pav bhaji hit like nothing else. Huge portions, super friendly vendor.'),
    ('Malvan Pav Bhaji Wala', 'rahul_desai', 4,
     'Classic tawa pav bhaji done well',
     'Good balance of spices, generous butter and fresh pav. One of the best roadside pav bhajis in Konkan.'),
]

# ── Build insert list ──────────────────────────────────────────────────────────
insert_rows = []
skipped     = []

for place_name, username, rating, title, body in reviews_data:
    p = pid(place_name)
    u = uid(username)
    if p is None:
        skipped.append(f'PLACE NOT FOUND: {place_name}')
        continue
    if u is None:
        skipped.append(f'USER NOT FOUND: {username}')
        continue
    insert_rows.append((p, u, rating, title, body))

if skipped:
    print("[WARN] Skipped entries:")
    for s in skipped:
        print("       ", s)

# ── Insert with INSERT IGNORE (safe to re-run) ─────────────────────────────────
if insert_rows:
    cur.executemany(
        "INSERT IGNORE INTO reviews (place_id, user_id, rating, title, body) "
        "VALUES (%s, %s, %s, %s, %s)",
        insert_rows
    )
    print(f"[OK] Attempted to insert {len(insert_rows)} reviews for new places.")
    print("     Duplicates are silently skipped (INSERT IGNORE).")
else:
    print("[INFO] No rows to insert.")

cur.close()
conn.close()
