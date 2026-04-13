# 🏘️ Local Vocal — Sawantwadi's Hotel & Cafe Review Platform

A full-stack Flask web application for discovering and reviewing hotels, cafes, restaurants, bakeries and street food spots in **Sawantwadi, Sindhudurg, Maharashtra**.

---

## ✨ Features

### Public (No Login Required)
- Browse all places with card-based layout
- Filter by category (Hotels, Cafes, Restaurants, Bakeries, Street Food)
- Search places by name or description
- View detailed place pages with photos, info, and reviews
- Visual star rating breakdowns with bar charts
- Featured / Editor's Picks section on homepage

### Authenticated Users
- Register and login with session-based auth
- Submit reviews (rating + title + body)
- Edit and delete your own reviews
- One review per user per place

### Admin Dashboard
- Overview stats (places, reviews, users, categories)
- Manage places: Add, Show/Hide, Delete
- Manage reviews: View all, Delete any
- Manage users: View all registered users
- Top rated places and recent reviews summary

---

## 🗂️ Project Structure

```
local_vocal/
├── app.py              # Flask application, all routes
├── database.py         # DB init, schema, seed data
├── local_vocal.db      # SQLite database (auto-created)
├── requirements.txt
│
├── static/
│   ├── css/
│   │   └── style.css   # Complete design system (Konkan-inspired)
│   └── js/
│       └── main.js     # Interactions, animations, nav
│
└── templates/
    ├── base.html           # Base layout (navbar, flash, footer)
    ├── index.html          # Homepage with hero, featured, browse
    ├── place_detail.html   # Place page with reviews
    ├── login.html
    ├── register.html
    ├── edit_review.html
    └── admin/
        ├── dashboard.html
        ├── places.html
        ├── reviews.html
        └── users.html
```

---

## 🗄️ Database Schema

```sql
categories  (id, name, icon, created_at)
users       (id, username, name, email, password_hash, is_admin, created_at)
places      (id, name, description, address, phone, website, price_range,
             category_id, image_url, is_active, is_featured, created_at)
reviews     (id, place_id, user_id, rating, title, body,
             created_at, updated_at)
             UNIQUE(place_id, user_id)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.8+

### 2. Install dependencies
```bash
pip install flask
```
or
```bash
pip install -r requirements.txt
```

### 3. Initialize the database
```bash
python database.py
```
This creates `local_vocal.db` with:
- 5 categories
- 5 users (1 admin + 4 regular)
- 13 real Sawantwadi places
- 16 sample reviews

### 4. Run the app
```bash
python app.py
```

Open your browser at → **http://localhost:5000**

---

## 🔑 Demo Accounts

| Role  | Username       | Password  |
|-------|---------------|-----------|
| Admin | `admin`       | `admin123`|
| User  | `priya_sawant`| `test1234`|
| User  | `rahul_desai` | `test1234`|
| User  | `sneha_patil` | `test1234`|
| User  | `arjun_naik`  | `test1234`|

**Admin Panel:** http://localhost:5000/admin

---

## 🏨 Sample Places Included

| Name                        | Category    | Rating |
|-----------------------------|-------------|--------|
| Hotel Sawant Palace         | Hotels      | 4.7 ⭐ |
| Konkan Heritage Inn         | Hotels      | 4.5 ⭐ |
| Sindhudurg Resorts & Spa    | Hotels      | —      |
| Hotel Shreyas               | Hotels      | 4.0 ⭐ |
| Hotel Pratap                | Hotels      | —      |
| The Wooden Cup Cafe         | Cafes       | 4.7 ⭐ |
| Mango Grove Cafe            | Cafes       | 4.0 ⭐ |
| Cafe Konkan Tales           | Cafes       | —      |
| The Pottery Brew            | Cafes       | —      |
| Malvani Khanaval            | Restaurants | 5.0 ⭐ |
| Ratnadeep Pure Veg          | Restaurants | 5.0 ⭐ |
| Goan Bake House             | Bakeries    | 5.0 ⭐ |
| Sawantwadi Vada Pav Corner  | Street Food | 4.5 ⭐ |

---

## 🎨 Design System

| Token           | Value                    |
|-----------------|--------------------------|
| Primary         | `#E8832A` (Saffron)      |
| Accent          | `#C4582A` (Terracotta)   |
| Forest          | `#2D5A3D`                |
| Background      | `#FBF7F0` (Warm Cream)   |
| Display Font    | Playfair Display (serif) |
| Body Font       | DM Sans                  |
| Mono Font       | DM Mono                  |

---

## 🔒 Security Notes

- Passwords are SHA-256 hashed
- Session-based authentication (Flask sessions)
- Admin routes protected by `@admin_required` decorator
- User routes protected by `@login_required` decorator
- SQL injection prevented via parameterised queries
- One review per user per place (DB-level UNIQUE constraint)

> **For production:** Use bcrypt for hashing, set `SECRET_KEY` via env var, enable HTTPS.

---

## 📡 API Endpoint

```
GET /api/places
```
Returns JSON list of all active places with name, category, and average rating.

---

Made with ♥ for Sawantwadi, Sindhudurg, Maharashtra.
