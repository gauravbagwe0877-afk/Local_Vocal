from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from database import init_db, get_db
import hashlib
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'localvocal-sawantwadi-secret-2024')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('Admin access required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── PUBLIC ROUTES ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    category_id = request.args.get('category', '')
    search = request.args.get('search', '').strip()

    query = '''
        SELECT p.*, c.name as category_name, c.icon as category_icon,
               ROUND(AVG(r.rating), 1) as avg_rating,
               COUNT(r.id) as review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON r.place_id = p.id
        WHERE p.is_active = 1
    '''
    params = []
    if category_id:
        query += ' AND p.category_id = ?'
        params.append(category_id)
    if search:
        query += ' AND (p.name LIKE ? OR p.description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])
    query += ' GROUP BY p.id ORDER BY avg_rating DESC, p.created_at DESC'

    places = db.execute(query, params).fetchall()
    categories = db.execute('SELECT * FROM categories ORDER BY name').fetchall()

    featured = db.execute('''
        SELECT p.*, c.name as category_name, c.icon as category_icon,
               ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.id) as review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON r.place_id = p.id
        WHERE p.is_active = 1 AND p.is_featured = 1
        GROUP BY p.id ORDER BY avg_rating DESC LIMIT 3
    ''').fetchall()

    return render_template('index.html', places=places, categories=categories,
                           featured=featured, selected_category=category_id,
                           search=search)

@app.route('/place/<int:place_id>')
def place_detail(place_id):
    db = get_db()
    place = db.execute('''
        SELECT p.*, c.name as category_name, c.icon as category_icon,
               ROUND(AVG(r.rating), 1) as avg_rating, COUNT(r.id) as review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON r.place_id = p.id
        WHERE p.id = ? AND p.is_active = 1
        GROUP BY p.id
    ''', [place_id]).fetchone()

    if not place:
        flash('Place not found.', 'danger')
        return redirect(url_for('index'))

    reviews = db.execute('''
        SELECT r.*, u.username, u.name as user_name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.place_id = ?
        ORDER BY r.created_at DESC
    ''', [place_id]).fetchall()

    rating_dist = {}
    for i in range(1, 6):
        count = db.execute(
            'SELECT COUNT(*) FROM reviews WHERE place_id = ? AND rating = ?',
            [place_id, i]
        ).fetchone()[0]
        rating_dist[i] = count

    user_review = None
    if 'user_id' in session:
        user_review = db.execute(
            'SELECT * FROM reviews WHERE place_id = ? AND user_id = ?',
            [place_id, session['user_id']]
        ).fetchone()

    return render_template('place_detail.html', place=place, reviews=reviews,
                           rating_dist=rating_dist, user_review=user_review)

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')

        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if not errors:
            db = get_db()
            existing = db.execute(
                'SELECT id FROM users WHERE username = ? OR email = ?',
                [username, email]
            ).fetchone()
            if existing:
                errors.append('Username or email already exists.')
            else:
                db.execute(
                    'INSERT INTO users (username, name, email, password_hash) VALUES (?, ?, ?, ?)',
                    [username, name, email, hash_password(password)]
                )
                db.commit()
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))

        for err in errors:
            flash(err, 'danger')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE (username = ? OR email = ?) AND password_hash = ?',
            [username, username, hash_password(password)]
        ).fetchone()
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['is_admin'] = bool(user['is_admin'])
            flash(f'Welcome back, {user["name"]}!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url if next_url else url_for('index'))
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ─── REVIEW ROUTES ────────────────────────────────────────────────────────────

@app.route('/review/submit', methods=['POST'])
@login_required
def submit_review():
    place_id = request.form.get('place_id', type=int)
    rating = request.form.get('rating', type=int)
    title = request.form.get('title', '').strip()
    body = request.form.get('body', '').strip()

    if not all([place_id, rating, title, body]):
        flash('All review fields are required.', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))

    if not (1 <= rating <= 5):
        flash('Rating must be between 1 and 5.', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))

    db = get_db()
    existing = db.execute(
        'SELECT id FROM reviews WHERE place_id = ? AND user_id = ?',
        [place_id, session['user_id']]
    ).fetchone()

    if existing:
        flash('You have already reviewed this place.', 'warning')
        return redirect(url_for('place_detail', place_id=place_id))

    db.execute(
        'INSERT INTO reviews (place_id, user_id, rating, title, body) VALUES (?, ?, ?, ?, ?)',
        [place_id, session['user_id'], rating, title, body]
    )
    db.commit()
    flash('Your review has been submitted!', 'success')
    return redirect(url_for('place_detail', place_id=place_id))

@app.route('/review/<int:review_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    db = get_db()
    review = db.execute('SELECT * FROM reviews WHERE id = ?', [review_id]).fetchone()

    if not review or review['user_id'] != session['user_id']:
        flash('Review not found or unauthorized.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        db.execute(
            'UPDATE reviews SET rating=?, title=?, body=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
            [rating, title, body, review_id]
        )
        db.commit()
        flash('Review updated successfully.', 'success')
        return redirect(url_for('place_detail', place_id=review['place_id']))

    place = db.execute('SELECT * FROM places WHERE id = ?', [review['place_id']]).fetchone()
    return render_template('edit_review.html', review=review, place=place)

@app.route('/review/<int:review_id>/delete', methods=['POST'])
@login_required
def delete_review(review_id):
    db = get_db()
    review = db.execute('SELECT * FROM reviews WHERE id = ?', [review_id]).fetchone()

    if not review:
        flash('Review not found.', 'danger')
        return redirect(url_for('index'))

    if review['user_id'] != session['user_id'] and not session.get('is_admin'):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('index'))

    place_id = review['place_id']
    db.execute('DELETE FROM reviews WHERE id = ?', [review_id])
    db.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('place_detail', place_id=place_id))

# ─── ADMIN ROUTES ─────────────────────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        'total_places': db.execute('SELECT COUNT(*) FROM places').fetchone()[0],
        'total_reviews': db.execute('SELECT COUNT(*) FROM reviews').fetchone()[0],
        'total_users': db.execute('SELECT COUNT(*) FROM users WHERE is_admin=0').fetchone()[0],
        'total_categories': db.execute('SELECT COUNT(*) FROM categories').fetchone()[0],
    }
    recent_reviews = db.execute('''
        SELECT r.*, u.username, p.name as place_name
        FROM reviews r JOIN users u ON r.user_id = u.id
        JOIN places p ON r.place_id = p.id
        ORDER BY r.created_at DESC LIMIT 10
    ''').fetchall()
    top_places = db.execute('''
        SELECT p.name, c.name as category_name,
               ROUND(AVG(r.rating),1) as avg_rating, COUNT(r.id) as review_count
        FROM places p LEFT JOIN reviews r ON r.place_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        WHERE p.is_active=1 GROUP BY p.id
        ORDER BY avg_rating DESC LIMIT 5
    ''').fetchall()
    return render_template('admin/dashboard.html', stats=stats,
                           recent_reviews=recent_reviews, top_places=top_places)

@app.route('/admin/places')
@admin_required
def admin_places():
    db = get_db()
    places = db.execute('''
        SELECT p.*, c.name as category_name,
               COUNT(r.id) as review_count,
               ROUND(AVG(r.rating),1) as avg_rating
        FROM places p LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON r.place_id = p.id
        GROUP BY p.id ORDER BY p.created_at DESC
    ''').fetchall()
    categories = db.execute('SELECT * FROM categories').fetchall()
    return render_template('admin/places.html', places=places, categories=categories)

@app.route('/admin/places/add', methods=['POST'])
@admin_required
def admin_add_place():
    db = get_db()
    db.execute('''
        INSERT INTO places (name, description, address, phone, website,
                            price_range, category_id, image_url, is_featured)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
        request.form['name'], request.form['description'],
        request.form['address'], request.form.get('phone', ''),
        request.form.get('website', ''), request.form.get('price_range', '₹₹'),
        request.form['category_id'], request.form.get('image_url', ''),
        1 if request.form.get('is_featured') else 0
    ])
    db.commit()
    flash('Place added successfully!', 'success')
    return redirect(url_for('admin_places'))

@app.route('/admin/places/<int:place_id>/toggle', methods=['POST'])
@admin_required
def admin_toggle_place(place_id):
    db = get_db()
    db.execute('UPDATE places SET is_active = NOT is_active WHERE id = ?', [place_id])
    db.commit()
    return redirect(url_for('admin_places'))

@app.route('/admin/places/<int:place_id>/delete', methods=['POST'])
@admin_required
def admin_delete_place(place_id):
    db = get_db()
    db.execute('DELETE FROM reviews WHERE place_id = ?', [place_id])
    db.execute('DELETE FROM places WHERE id = ?', [place_id])
    db.commit()
    flash('Place deleted.', 'info')
    return redirect(url_for('admin_places'))

@app.route('/admin/reviews')
@admin_required
def admin_reviews():
    db = get_db()
    reviews = db.execute('''
        SELECT r.*, u.username, p.name as place_name
        FROM reviews r JOIN users u ON r.user_id = u.id
        JOIN places p ON r.place_id = p.id
        ORDER BY r.created_at DESC
    ''').fetchall()
    return render_template('admin/reviews.html', reviews=reviews)

@app.route('/admin/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def admin_delete_review(review_id):
    db = get_db()
    db.execute('DELETE FROM reviews WHERE id = ?', [review_id])
    db.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/users')
@admin_required
def admin_users():
    db = get_db()
    users = db.execute('''
        SELECT u.*, COUNT(r.id) as review_count
        FROM users u LEFT JOIN reviews r ON r.user_id = u.id
        GROUP BY u.id ORDER BY u.created_at DESC
    ''').fetchall()
    return render_template('admin/users.html', users=users)

# ─── API ──────────────────────────────────────────────────────────────────────

@app.route('/api/places')
def api_places():
    db = get_db()
    places = db.execute('''
        SELECT p.id, p.name, c.name as category, ROUND(AVG(r.rating),1) as rating
        FROM places p LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r ON r.place_id = p.id
        WHERE p.is_active=1 GROUP BY p.id
    ''').fetchall()
    return jsonify([dict(p) for p in places])

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
