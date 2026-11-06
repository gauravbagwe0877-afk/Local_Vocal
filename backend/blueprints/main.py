from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import query, execute, get_db
from auth_decorators import login_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/', endpoint='index')
def index():
    category_id = request.args.get('category', '')
    search      = request.args.get('search', '').strip()

    sql = '''
        SELECT p.*, c.name AS category_name, c.icon AS category_icon,
               ROUND(AVG(r.rating), 1) AS avg_rating,
               COUNT(r.id) AS review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r    ON r.place_id = p.id
        WHERE p.is_active = 1
    '''
    params = []
    if category_id:
        sql += ' AND p.category_id = %s'
        params.append(category_id)
    if search:
        sql += ' AND (p.name LIKE %s OR p.description LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%'])
    sql += ' GROUP BY p.id ORDER BY avg_rating DESC, p.created_at DESC'

    places     = query(sql, tuple(params))
    categories = query('SELECT * FROM categories ORDER BY name')
    featured   = query('''
        SELECT p.*, c.name AS category_name, c.icon AS category_icon,
               ROUND(AVG(r.rating), 1) AS avg_rating, COUNT(r.id) AS review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r    ON r.place_id = p.id
        WHERE p.is_active = 1 AND p.is_featured = 1
        GROUP BY p.id ORDER BY avg_rating DESC LIMIT 3
    ''')

    return render_template('index.html', places=places, categories=categories,
                           featured=featured, selected_category=category_id,
                           search=search)


@main_bp.route('/place/<int:place_id>', endpoint='place_detail')
def place_detail(place_id):
    place = query('''
        SELECT p.*, c.name AS category_name, c.icon AS category_icon,
               ROUND(AVG(r.rating), 1) AS avg_rating, COUNT(r.id) AS review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r    ON r.place_id = p.id
        WHERE p.id = %s AND p.is_active = 1
        GROUP BY p.id
    ''', (place_id,), one=True)

    if not place:
        flash('Place not found.', 'danger')
        return redirect(url_for('index'))

    reviews = query('''
        SELECT r.*, u.username, u.name AS user_name
        FROM reviews r
        JOIN users u ON r.user_id = u.id
        WHERE r.place_id = %s
        ORDER BY r.created_at DESC
    ''', (place_id,))

    rating_dist = {}
    for i in range(1, 6):
        row = query('SELECT COUNT(*) AS c FROM reviews WHERE place_id=%s AND rating=%s',
                    (place_id, i), one=True)
        rating_dist[i] = row['c'] if row else 0

    user_review = None
    if 'user_id' in session:
        user_review = query(
            'SELECT * FROM reviews WHERE place_id=%s AND user_id=%s',
            (place_id, session['user_id']), one=True
        )

    return render_template('place_detail.html', place=place, reviews=reviews,
                           rating_dist=rating_dist, user_review=user_review)


@main_bp.route('/place/<int:place_id>/review', methods=['POST'], endpoint='submit_review')
@login_required
def submit_review(place_id):
    rating = request.form.get('rating', type=int)
    title  = request.form.get('title', '').strip()
    body   = request.form.get('body', '').strip()

    if not all([rating, title, body]):
        flash('All review fields are required.', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))
    if not (1 <= rating <= 5):
        flash('Rating must be between 1 and 5.', 'danger')
        return redirect(url_for('place_detail', place_id=place_id))

    existing = query('SELECT id FROM reviews WHERE place_id=%s AND user_id=%s',
                     (place_id, session['user_id']), one=True)
    if existing:
        flash('You have already reviewed this place.', 'warning')
        return redirect(url_for('place_detail', place_id=place_id))

    execute(
        'INSERT INTO reviews (place_id, user_id, rating, title, body) VALUES (%s,%s,%s,%s,%s)',
        (place_id, session['user_id'], rating, title, body)
    )
    flash('Your review has been submitted!', 'success')
    return redirect(url_for('place_detail', place_id=place_id))


@main_bp.route('/edit_review/<int:review_id>', methods=['GET', 'POST'], endpoint='edit_review')
@login_required
def edit_review(review_id):
    review = query('SELECT * FROM reviews WHERE id=%s', (review_id,), one=True)

    if not review or (review['user_id'] != session['user_id'] and session.get('role') != 'admin'):
        flash('Review not found or unauthorized.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        rating = request.form.get('rating', type=int)
        title  = request.form.get('title', '').strip()
        body   = request.form.get('body', '').strip()

        if not all([rating, title, body]):
            flash('All fields are required.', 'danger')
            return redirect(url_for('edit_review', review_id=review_id))
        if not (1 <= rating <= 5):
            flash('Rating must be between 1 and 5.', 'danger')
            return redirect(url_for('edit_review', review_id=review_id))

        execute(
            'UPDATE reviews SET rating=%s, title=%s, body=%s WHERE id=%s',
            (rating, title, body, review_id)
        )
        flash('Review updated successfully.', 'success')
        return redirect(url_for('place_detail', place_id=review['place_id']))

    place = query('SELECT * FROM places WHERE id=%s', (review['place_id'],), one=True)
    return render_template('edit_review.html', review=review, place=place)


@main_bp.route('/delete_review/<int:review_id>', methods=['POST'], endpoint='delete_review')
@login_required
def delete_review(review_id):
    review = query('SELECT * FROM reviews WHERE id=%s', (review_id,), one=True)
    if not review:
        flash('Review not found.', 'danger')
        return redirect(url_for('index'))

    if review['user_id'] != session['user_id'] and session.get('role') != 'admin':
        flash('Unauthorized.', 'danger')
        return redirect(url_for('index'))

    place_id = review['place_id']
    execute('DELETE FROM reviews WHERE id=%s', (review_id,))
    flash('Review deleted.', 'info')
    return redirect(url_for('place_detail', place_id=place_id))


@main_bp.route('/api/places', endpoint='api_places')
def api_places():
    places = query('''
        SELECT p.id, p.name, p.address, p.image_url, p.price_range,
               c.name AS category, c.icon AS category_icon,
               ROUND(AVG(r.rating),1) AS rating, COUNT(r.id) AS review_count
        FROM places p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN reviews r    ON r.place_id = p.id
        WHERE p.is_active = 1
        GROUP BY p.id
    ''')
    return jsonify(places)


@main_bp.route('/api/status', endpoint='api_status')
def api_status():
    try:
        db = get_db()
        if db.is_connected():
            return jsonify({'status': 'ok', 'database': 'MySQL connected'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@main_bp.route('/api/place/<int:place_id>/images', endpoint='place_images_gallery')
def place_images_gallery(place_id):
    """Return all inside images for a given place, ordered by display_order."""
    rows = query(
        """
        SELECT image_url, caption, display_order
        FROM   place_images
        WHERE  place_id = %s
        ORDER  BY display_order ASC
        """,
        (place_id,)
    )
    return jsonify(rows)

