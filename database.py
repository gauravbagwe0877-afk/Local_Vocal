import sqlite3
import os

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'local_vocal.db')

def get_db():
    from flask import g
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db

def close_db(e=None):
    from flask import g
    db = g.pop('db', None)
    if db is not None:
        db.close()

SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL DEFAULT '🏠',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_admin INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS places (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    phone TEXT,
    website TEXT,
    price_range TEXT DEFAULT '₹₹',
    category_id INTEGER REFERENCES categories(id),
    image_url TEXT,
    is_active INTEGER DEFAULT 1,
    is_featured INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id INTEGER NOT NULL REFERENCES places(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(place_id, user_id)
);
"""

def seed_data(conn):
    c = conn.cursor()
    cats = [('Hotels','🏨'),('Cafes','☕'),('Restaurants','🍽️'),('Bakeries','🥐'),('Street Food','🌮')]
    c.executemany("INSERT OR IGNORE INTO categories(name,icon) VALUES(?,?)", cats)
    
    import hashlib
    def hp(p): return hashlib.sha256(p.encode()).hexdigest()
    
    users = [
        ('admin','Admin User','admin@localvocal.com',hp('admin123'),1),
        ('priya_sawant','Priya Sawant','priya@example.com',hp('test1234'),0),
        ('rahul_desai','Rahul Desai','rahul@example.com',hp('test1234'),0),
        ('sneha_patil','Sneha Patil','sneha@example.com',hp('test1234'),0),
        ('arjun_naik','Arjun Naik','arjun@example.com',hp('test1234'),0),
    ]
    c.executemany("INSERT OR IGNORE INTO users(username,name,email,password_hash,is_admin) VALUES(?,?,?,?,?)", users)
    
    def cat(name):
        return c.execute("SELECT id FROM categories WHERE name=?", (name,)).fetchone()[0]
    
    places = [
        ('Hotel Sawant Palace','A grand heritage-style hotel in the heart of Sawantwadi town, offering spacious rooms, impeccable service, and a rooftop terrace with stunning views of the Western Ghats. Perfect for leisure and business travellers alike.','Main Market Road, Sawantwadi, Sindhudurg 416510','+91 2363 272123','','₹₹₹',cat('Hotels'),'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800',1,1),
        ('Konkan Heritage Inn','Nestled amidst lush mango orchards, this boutique property celebrates authentic Malvani architecture with terracotta-tiled roofs, wooden furniture, and farm-to-table dining. An absolute gem for nature lovers.','Near Sawantwadi Lake, Off NH66, Sawantwadi 416510','+91 9876543210','','₹₹₹₹',cat('Hotels'),'https://images.unsplash.com/photo-1582719508461-905c673771fd?w=800',1,1),
        ('Hotel Shreyas','Budget-friendly accommodation with clean, comfortable rooms and a friendly staff. Located conveniently near the MSRTC bus stand. A reliable choice for solo travellers and backpackers exploring coastal Konkan.','Near Bus Stand, Sawantwadi 416510','+91 2363 272456','','₹',cat('Hotels'),'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800',1,0),
        ('Sindhudurg Resorts and Spa','A luxury resort spread across 5 acres with swimming pool, Ayurvedic spa, infinity deck, and gourmet restaurant. Experience Konkan royalty with modern comforts and personalised service.','Walaval Road, 4 km from Sawantwadi, Sindhudurg 416511','+91 9988776655','','₹₹₹₹₹',cat('Hotels'),'https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=800',1,1),
        ('Hotel Pratap','A mid-range hotel popular with families and traders visiting the famous Sawantwadi wooden toy market. Clean rooms, 24-hour reception, and a good attached restaurant serving local Malvani food.','Palace Road, Sawantwadi 416510','+91 2363 272789','','₹₹',cat('Hotels'),'https://images.unsplash.com/photo-1445019980597-93fa8acb246c?w=800',1,0),
        ('The Wooden Cup Cafe','Inspired by Sawantwadi famous lacquerware art, this artisanal cafe serves specialty pour-over coffees, organic teas, and freshly baked goods inside a space adorned with local handicrafts and warm lantern lighting.','Near Rajwada Palace, Sawantwadi 416510','+91 9823456789','','₹₹',cat('Cafes'),'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=800',1,1),
        ('Mango Grove Cafe','Sit under real mango trees in an open-air garden cafe. Specialises in raw mango drinks, kokum sarbat, and Malvani-spiced snacks. A blissful stop for breakfast and evening chai.','Gaondevi Naka, Sawantwadi 416510','+91 9765432100','','₹',cat('Cafes'),'https://images.unsplash.com/photo-1554118811-1e0d58224f24?w=800',1,0),
        ('Cafe Konkan Tales','A storyteller cafe with walls covered in old Konkan photographs, vintage maps, and folk art. Exceptional cold brew, Malvani chai, and a curated menu of fusion snacks.','Market Chowk, Sawantwadi 416510','+91 9712345678','','₹₹',cat('Cafes'),'https://images.unsplash.com/photo-1453614512568-c4024d13c247?w=800',1,0),
        ('The Pottery Brew','Unique cafe where you can try pottery-making while sipping your morning coffee. Owned by a local artisan family, it offers Goan-style bread, homemade jams, and single-origin coffee sourced from Coorg estates.','Handicraft Lane, Near Palace Road, Sawantwadi 416510','+91 9845678901','','₹₹',cat('Cafes'),'https://images.unsplash.com/photo-1600093463592-8e36ae95ef56?w=800',1,0),
        ('Malvani Khanaval','Authentic home-style Malvani cooking passed down through three generations. Must-tries: Sol Kadhi, Kombdi Vade, Bangda Fry, and the legendary Malvani fish curry. Book in advance on weekends!','Near Sawantwadi Lake, Sawantwadi 416510','+91 9834567890','','₹₹',cat('Restaurants'),'https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800',1,0),
        ('Ratnadeep Pure Veg','Beloved by locals for decades, this pure vegetarian restaurant serves Maharashtrian thalis with 12+ items, fresh chakli, puranpoli, and seasonal vegetables. The bhakri and pithla combo is legendary.','Main Road, Sawantwadi 416510','+91 2363 273456','','₹',cat('Restaurants'),'https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800',1,0),
        ('Goan Bake House','Fresh-baked Goan poi (local bread), bebinca, dodol, and neureos every morning. This family-run bakery has been the neighbourhood breakfast destination for over 35 years.','Near MSRTC Bus Stand, Sawantwadi 416510','+91 9823001122','','₹',cat('Bakeries'),'https://images.unsplash.com/photo-1509440159596-0249088772ff?w=800',1,0),
        ('Sawantwadi Vada Pav Corner','The crunchiest, most flavourful vada pav in all of Sindhudurg district. The secret chutney recipe has been guarded for 20+ years. Open from 7 AM to 2 PM only.','Palace Chowk, Main Market, Sawantwadi 416510','','','₹',cat('Street Food'),'https://images.unsplash.com/photo-1606491956689-2ea866880c84?w=800',1,0),
    ]
    c.executemany("INSERT OR IGNORE INTO places(name,description,address,phone,website,price_range,category_id,image_url,is_active,is_featured) VALUES(?,?,?,?,?,?,?,?,?,?)", places)
    
    conn.commit()
    
    # Get place IDs by name for reviews
    def pid(name):
        r = c.execute("SELECT id FROM places WHERE name=?", (name,)).fetchone()
        return r[0] if r else None
    
    def uid(username):
        r = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        return r[0] if r else None
    
    reviews = [
        (pid('Hotel Sawant Palace'),uid('priya_sawant'),5,'Best hotel experience in Konkan!','Stayed here for 3 nights and the experience was absolutely wonderful. The rooftop view of the Ghats at sunrise is something I will never forget. Staff was incredibly warm and helpful. The Malvani breakfast spread was exceptional. Highly recommend!'),
        (pid('Hotel Sawant Palace'),uid('rahul_desai'),4,'Great location, minor maintenance issues','The hotel is centrally located which is perfect for exploring Sawantwadi. Rooms are spacious and beds comfortable. Had a minor issue with the AC but staff resolved it quickly. The restaurant downstairs serves great local food.'),
        (pid('Hotel Sawant Palace'),uid('sneha_patil'),5,'Perfect for family vacation','Brought my parents here for their anniversary trip. The heritage decor reminded them of their travels decades ago. The staff arranged a lovely cake surprise — absolutely touched. Will definitely return!'),
        (pid('Konkan Heritage Inn'),uid('priya_sawant'),5,'Hidden paradise in the Konkan','I stumbled upon this property while searching for unique stays and I am so glad I did. The mango orchard setting is stunning. Farm-fresh food, birdwatching at dawn, and the kindest hosts I have met anywhere in Maharashtra.'),
        (pid('Konkan Heritage Inn'),uid('arjun_naik'),4,'Beautiful but slightly pricey','The ambience is unmatched — waking up to birds and fresh air is magical. Food quality is top-notch but the price point is a bit high for what you get in terms of room size. That said, the overall experience is still very memorable.'),
        (pid('The Wooden Cup Cafe'),uid('rahul_desai'),5,'The pour-over coffee changed my life','I am not exaggerating. The Ethiopian pour-over coffee here is the best I have had outside of a specialty cafe in Mumbai. The ambience with all the lacquerware art is truly unique to Sawantwadi. Love that they support local artists!'),
        (pid('The Wooden Cup Cafe'),uid('sneha_patil'),4,'Charming spot with great snacks','The cafe is beautifully designed — you can tell a lot of thought went into the decor. Coffee is excellent. The banana bread and kokum cheesecake were surprisingly great. A bit of a wait during peak hours but totally worth it.'),
        (pid('The Wooden Cup Cafe'),uid('arjun_naik'),5,'My go-to spot every visit','I visit Sawantwadi twice a year and The Wooden Cup is always my first stop. Consistent quality, friendly staff, and they keep introducing new menu items while keeping the classics. The loyalty card programme is a nice touch too.'),
        (pid('Mango Grove Cafe'),uid('priya_sawant'),4,'What a vibe!','The garden setting under real mango trees is so relaxing. I spent 2 hours here just reading and sipping kokum sarbat. The raw mango drink is seriously refreshing. Prices are very reasonable for such a lovely atmosphere.'),
        (pid('Malvani Khanaval'),uid('rahul_desai'),5,'Best Malvani food, period.','I have eaten Malvani food across the Konkan coast and Malvani Khanaval stands out. The kombdi vade is crispy and perfectly spiced. The fish curry uses fresh local catch. Grandma-level cooking that no restaurant in the city can replicate.'),
        (pid('Malvani Khanaval'),uid('arjun_naik'),5,'A true Konkan gem','Visited on a recommendation from our hotel. Three generations of cooking tradition is evident in every dish. The sol kadhi alone was worth the trip. Small place, so go early. The banana leaf thali on Sundays is a must-try!'),
        (pid('Ratnadeep Pure Veg'),uid('sneha_patil'),5,'Unbeatable thali value','Ratnadeep serves the most filling and authentic vegetarian thali I have had in Sawantwadi. 12 items, all freshly made, for an incredible price. The puranpoli and amti combo is divine. A must-visit for vegetarians.'),
        (pid('Goan Bake House'),uid('priya_sawant'),5,'Best Goan bread outside Goa','The poi here is fresh, soft, and authentic. I bought a bag to take back to Pune. The bebinca is rich and perfect. The old uncle who runs the place has been doing this for decades — you can taste the passion in every bite.'),
        (pid('Sawantwadi Vada Pav Corner'),uid('rahul_desai'),5,'The chutney is everything','I have had vada pav across Maharashtra but the chutney here is in a league of its own. The vada itself is crispy with a perfectly spiced aloo filling. For the price, this is an absolute steal. Come early — it sells out by noon!'),
        (pid('Sawantwadi Vada Pav Corner'),uid('arjun_naik'),4,'Worth the early wake-up','Had to set an alarm to get here before it sold out. Totally worth it. The vada pav is phenomenal. Only suggestion would be to extend the hours since many tourists miss it. But maybe the scarcity is part of the charm!'),
    ]
    valid = [(p,u,r,t,b) for p,u,r,t,b in reviews if p and u]
    c.executemany("INSERT OR IGNORE INTO reviews(place_id,user_id,rating,title,body) VALUES(?,?,?,?,?)", valid)
    conn.commit()

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.executescript(SCHEMA)
    seed_data(conn)
    conn.close()
    print('Database initialized with sample Sawantwadi data.')

if __name__ == '__main__':
    init_db()
