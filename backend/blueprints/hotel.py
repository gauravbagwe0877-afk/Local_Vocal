from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import query, execute
from auth_decorators import hotel_staff_required
import datetime
import json
import random
import string

hotel_bp = Blueprint('hotel', __name__, url_prefix='/hotel')

def get_hotel_settings():
    """Helper to fetch hotel configuration settings as a key-value dictionary."""
    rows = query('SELECT setting_key, setting_val FROM hotel_settings')
    settings = {r['setting_key']: r['setting_val'] for r in rows}
    # Set sensible defaults if keys are missing
    settings.setdefault('hotel_name', 'Hotel Sawant Palace')
    settings.setdefault('currency_symbol', '₹')
    settings.setdefault('gst_rate', '12')
    return settings

@hotel_bp.context_processor
def inject_hotel_globals():
    """Injects hotel settings and notifications count into all hotel templates."""
    settings = get_hotel_settings()
    # Notification count: urgent/high maintenance issues + pending checkout cleans
    alert_hk = query("""
        SELECT COUNT(*) AS c FROM housekeeping_tasks
        WHERE status IN ('pending', 'in_progress') AND priority IN ('urgent', 'high')
    """, one=True)
    alert_mr = query("""
        SELECT COUNT(*) AS c FROM maintenance_requests
        WHERE status IN ('open', 'in_progress') AND priority IN ('urgent', 'high')
    """, one=True)
    total_alerts = (alert_hk['c'] if alert_hk else 0) + (alert_mr['c'] if alert_mr else 0)

    return {
        'hotel_settings': settings,
        'hotel_alert_count': total_alerts,
        'today_date': datetime.date.today().isoformat()
    }


# ─── 1. DASHBOARD ─────────────────────────────────────────────────────────────

@hotel_bp.route('/', endpoint='index')
@hotel_bp.route('/dashboard', endpoint='dashboard')
@hotel_staff_required
def dashboard():
    today = datetime.date.today()

    # Total rooms & status breakdown
    rooms = query('''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate
        FROM rooms r
        LEFT JOIN room_types rt ON r.room_type_id = rt.id
        ORDER BY r.floor ASC, r.room_number ASC
    ''')

    total_rooms = len(rooms)
    occupied_count = sum(1 for r in rooms if r['status'] == 'occupied')
    available_count = sum(1 for r in rooms if r['status'] == 'available')
    cleaning_count = sum(1 for r in rooms if r['status'] in ('cleaning', 'inspected'))
    maintenance_count = sum(1 for r in rooms if r['status'] == 'maintenance')
    reserved_count = sum(1 for r in rooms if r['status'] == 'reserved')

    occupancy_rate = round((occupied_count / total_rooms * 100), 1) if total_rooms > 0 else 0

    # Today's check-ins & check-outs
    checkins_today = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        WHERE b.check_in_date = %s AND b.status IN ('confirmed', 'pending')
        ORDER BY b.id DESC
    ''', (today,))

    checkouts_today = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        WHERE b.check_out_date = %s AND b.status = 'checked_in'
        ORDER BY b.id DESC
    ''', (today,))

    # In-house guests count
    inhouse_count = query("""
        SELECT COUNT(*) AS c FROM bookings WHERE status = 'checked_in'
    """, one=True)['c']

    # Financials (All live from payments, invoices, expenses)
    total_revenue_row = query('SELECT COALESCE(SUM(amount), 0) AS total_rev FROM payments', one=True)
    total_revenue = float(total_revenue_row['total_rev']) if total_revenue_row else 0.0

    mtd_revenue_row = query('''
        SELECT COALESCE(SUM(amount), 0) AS mtd_rev FROM payments
        WHERE payment_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
    ''', one=True)
    mtd_revenue = float(mtd_revenue_row['mtd_rev']) if mtd_revenue_row else 0.0

    pending_dues_row = query('''
        SELECT COALESCE(SUM(total - paid_amount), 0) AS pending_due
        FROM invoices WHERE status IN ('issued', 'partial')
    ''', one=True)
    pending_dues = float(pending_dues_row['pending_due']) if pending_dues_row else 0.0

    mtd_expenses_row = query('''
        SELECT COALESCE(SUM(amount), 0) AS mtd_exp FROM expenses
        WHERE expense_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
    ''', one=True)
    mtd_expenses = float(mtd_expenses_row['mtd_exp']) if mtd_expenses_row else 0.0

    # Recent bookings
    recent_bookings = query('''
        SELECT b.*, g.full_name AS guest_name, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        ORDER BY b.created_at DESC LIMIT 6
    ''')

    # Pending housekeeping tasks
    pending_hk = query('''
        SELECT ht.*, r.room_number
        FROM housekeeping_tasks ht
        JOIN rooms r ON ht.room_id = r.id
        WHERE ht.status IN ('pending', 'in_progress')
        ORDER BY FIELD(ht.priority, 'urgent', 'high', 'normal', 'low'), ht.id DESC LIMIT 5
    ''')

    # Active maintenance requests
    active_maintenance = query('''
        SELECT mr.*, r.room_number
        FROM maintenance_requests mr
        LEFT JOIN rooms r ON mr.room_id = r.id
        WHERE mr.status IN ('open', 'in_progress')
        ORDER BY FIELD(mr.priority, 'urgent', 'high', 'normal', 'low'), mr.id DESC LIMIT 5
    ''')

    stats = {
        'total_rooms': total_rooms,
        'occupied_rooms': occupied_count,
        'available_rooms': available_count,
        'cleaning_rooms': cleaning_count,
        'maintenance_rooms': maintenance_count,
        'reserved_rooms': reserved_count,
        'occupancy_rate': occupancy_rate,
        'checkins_today_count': len(checkins_today),
        'checkouts_today_count': len(checkouts_today),
        'inhouse_count': inhouse_count,
        'total_revenue': total_revenue,
        'mtd_revenue': mtd_revenue,
        'pending_dues': pending_dues,
        'mtd_expenses': mtd_expenses
    }

    return render_template('hotel/dashboard.html',
                           stats=stats,
                           rooms=rooms,
                           checkins_today=checkins_today,
                           checkouts_today=checkouts_today,
                           recent_bookings=recent_bookings,
                           pending_hk=pending_hk,
                           active_maintenance=active_maintenance)


# ─── 2. ROOM MANAGEMENT ───────────────────────────────────────────────────────

@hotel_bp.route('/rooms', endpoint='rooms')
@hotel_staff_required
def rooms():
    floor_filter = request.args.get('floor', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate, rt.amenities,
               b.booking_ref, b.guest_id, g.full_name AS current_guest_name,
               b.check_in_date, b.check_out_date
        FROM rooms r
        LEFT JOIN room_types rt ON r.room_type_id = rt.id
        LEFT JOIN bookings b ON b.room_id = r.id AND b.status = 'checked_in'
        LEFT JOIN guests g ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if floor_filter:
        sql += ' AND r.floor = %s'
        params.append(floor_filter)
    if status_filter:
        sql += ' AND r.status = %s'
        params.append(status_filter)

    sql += ' ORDER BY r.floor ASC, r.room_number ASC'
    room_list = query(sql, tuple(params))

    # Room types summary
    room_types = query('''
        SELECT rt.*, COUNT(r.id) AS room_count
        FROM room_types rt
        LEFT JOIN rooms r ON r.room_type_id = rt.id
        GROUP BY rt.id ORDER BY rt.base_rate ASC
    ''')

    # Parse JSON amenities for display
    for rt in room_types:
        if isinstance(rt.get('amenities'), str):
            try:
                rt['amenities_list'] = json.loads(rt['amenities'])
            except Exception:
                rt['amenities_list'] = []
        elif isinstance(rt.get('amenities'), list):
            rt['amenities_list'] = rt['amenities']
        else:
            rt['amenities_list'] = []

    # Count stats
    all_rooms = query('SELECT status, floor FROM rooms')
    floors = sorted(list(set(r['floor'] for r in all_rooms if r['floor'])))

    counts = {
        'all': len(all_rooms),
        'available': sum(1 for r in all_rooms if r['status'] == 'available'),
        'occupied': sum(1 for r in all_rooms if r['status'] == 'occupied'),
        'cleaning': sum(1 for r in all_rooms if r['status'] == 'cleaning'),
        'inspected': sum(1 for r in all_rooms if r['status'] == 'inspected'),
        'maintenance': sum(1 for r in all_rooms if r['status'] == 'maintenance'),
        'reserved': sum(1 for r in all_rooms if r['status'] == 'reserved'),
    }

    return render_template('hotel/rooms.html',
                           rooms=room_list,
                           room_types=room_types,
                           floors=floors,
                           counts=counts,
                           selected_floor=floor_filter,
                           selected_status=status_filter)


@hotel_bp.route('/rooms/add', methods=['POST'], endpoint='add_room')
@hotel_staff_required
def add_room():
    room_number = request.form.get('room_number', '').strip()
    floor = request.form.get('floor', '').strip()
    room_type_id = request.form.get('room_type_id')
    status = request.form.get('status', 'available')
    housekeeping_status = request.form.get('housekeeping_status', 'clean')
    notes = request.form.get('notes', '').strip()

    if not room_number or not floor or not room_type_id:
        flash('Room number, floor, and room type are required.', 'danger')
        return redirect(url_for('hotel.rooms'))

    # Check uniqueness
    existing = query('SELECT id FROM rooms WHERE room_number = %s', (room_number,), one=True)
    if existing:
        flash(f'Room number {room_number} already exists.', 'danger')
        return redirect(url_for('hotel.rooms'))

    execute('''
        INSERT INTO rooms (room_number, floor, room_type_id, status, housekeeping_status, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (room_number, floor, room_type_id, status, housekeeping_status, notes))

    flash(f'Room {room_number} added successfully!', 'success')
    return redirect(url_for('hotel.rooms'))


@hotel_bp.route('/rooms/<int:room_id>/status', methods=['POST'], endpoint='update_room_status')
@hotel_staff_required
def update_room_status(room_id):
    status = request.form.get('status')
    housekeeping_status = request.form.get('housekeeping_status')
    notes = request.form.get('notes')

    room = query('SELECT id, room_number FROM rooms WHERE id = %s', (room_id,), one=True)
    if not room:
        flash('Room not found.', 'danger')
        return redirect(url_for('hotel.rooms'))

    valid_statuses = ('available', 'reserved', 'occupied', 'cleaning', 'inspected', 'maintenance')
    valid_hk = ('clean', 'dirty', 'inspecting')

    updates = []
    params = []
    if status in valid_statuses:
        updates.append('status = %s')
        params.append(status)
    if housekeeping_status in valid_hk:
        updates.append('housekeeping_status = %s')
        params.append(housekeeping_status)
    if notes is not None:
        updates.append('notes = %s')
        params.append(notes.strip())

    if updates:
        params.append(room_id)
        execute(f"UPDATE rooms SET {', '.join(updates)} WHERE id = %s", tuple(params))
        flash(f"Room {room['room_number']} updated successfully.", 'success')

    return redirect(request.referrer or url_for('hotel.rooms'))


@hotel_bp.route('/room-types/add', methods=['POST'], endpoint='add_room_type')
@hotel_staff_required
def add_room_type():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    base_rate = request.form.get('base_rate', type=float)
    max_adults = request.form.get('max_adults', default=2, type=int)
    max_children = request.form.get('max_children', default=1, type=int)
    amenities_raw = request.form.get('amenities', '').strip()
    image_url = request.form.get('image_url', '').strip()

    if not name or base_rate is None or base_rate <= 0:
        flash('Room type name and a valid rate are required.', 'danger')
        return redirect(url_for('hotel.rooms'))

    amenities = [a.strip() for a in amenities_raw.split(',') if a.strip()]

    execute('''
        INSERT INTO room_types (name, description, max_adults, max_children, base_rate, amenities, image_url, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
    ''', (name, description, max_adults, max_children, base_rate, json.dumps(amenities), image_url))

    flash(f'Room type {name} created successfully!', 'success')
    return redirect(url_for('hotel.rooms'))


# ─── 3. BOOKINGS MANAGEMENT ───────────────────────────────────────────────────

@hotel_bp.route('/bookings', endpoint='bookings')
@hotel_staff_required
def bookings():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    sql = '''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, g.email AS guest_email,
               r.room_number, r.floor, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE 1=1
    '''
    params = []
    if status_filter and status_filter != 'all':
        sql += ' AND b.status = %s'
        params.append(status_filter)
    if search:
        sql += ' AND (b.booking_ref LIKE %s OR g.full_name LIKE %s OR g.phone LIKE %s OR r.room_number LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])

    sql += ' ORDER BY b.check_in_date DESC, b.id DESC'
    booking_list = query(sql, tuple(params))

    # Room types and available rooms for the new booking modal
    room_types = query('SELECT * FROM room_types WHERE is_active = 1 ORDER BY base_rate ASC')
    rooms_available = query('''
        SELECT r.id, r.room_number, r.floor, r.status, rt.name AS room_type_name, rt.base_rate, rt.id AS room_type_id
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.id
        ORDER BY r.room_number ASC
    ''')
    guests = query('SELECT id, full_name, phone, email FROM guests ORDER BY full_name ASC')

    counts = {
        'all': query('SELECT COUNT(*) AS c FROM bookings', one=True)['c'],
        'checked_in': query("SELECT COUNT(*) AS c FROM bookings WHERE status='checked_in'", one=True)['c'],
        'confirmed': query("SELECT COUNT(*) AS c FROM bookings WHERE status='confirmed'", one=True)['c'],
        'pending': query("SELECT COUNT(*) AS c FROM bookings WHERE status='pending'", one=True)['c'],
        'checked_out': query("SELECT COUNT(*) AS c FROM bookings WHERE status='checked_out'", one=True)['c'],
        'cancelled': query("SELECT COUNT(*) AS c FROM bookings WHERE status='cancelled'", one=True)['c'],
    }

    return render_template('hotel/bookings.html',
                           bookings=booking_list,
                           room_types=room_types,
                           rooms_available=rooms_available,
                           guests=guests,
                           counts=counts,
                           selected_status=status_filter,
                           search=search)


@hotel_bp.route('/bookings/new', methods=['POST'], endpoint='new_booking')
@hotel_staff_required
def new_booking():
    guest_id = request.form.get('guest_id')
    new_guest_name = request.form.get('new_guest_name', '').strip()
    new_guest_email = request.form.get('new_guest_email', '').strip()
    new_guest_phone = request.form.get('new_guest_phone', '').strip()
    new_guest_id_type = request.form.get('new_guest_id_type', '')
    new_guest_id_number = request.form.get('new_guest_id_number', '').strip()

    room_id = request.form.get('room_id', type=int)
    check_in_date_str = request.form.get('check_in_date', '').strip()
    check_out_date_str = request.form.get('check_out_date', '').strip()
    adults = request.form.get('adults', default=1, type=int)
    children = request.form.get('children', default=0, type=int)
    status = request.form.get('status', 'confirmed')
    source = request.form.get('source', 'walk_in')
    special_requests = request.form.get('special_requests', '').strip()
    advance_paid = request.form.get('advance_paid', default=0.0, type=float)
    payment_method = request.form.get('payment_method', 'cash')

    # Backend Validation: Guest
    if not guest_id or guest_id == 'new':
        if not new_guest_name or not new_guest_phone:
            flash('Guest name and phone number are required for new guest.', 'danger')
            return redirect(url_for('hotel.bookings'))
        guest_id = execute('''
            INSERT INTO guests (full_name, email, phone, id_type, id_number, total_stays)
            VALUES (%s, %s, %s, %s, %s, 1)
        ''', (new_guest_name, new_guest_email or f"{new_guest_phone}@guest.sawantpalace.com", new_guest_phone, new_guest_id_type, new_guest_id_number))
    else:
        guest_id = int(guest_id)

    # Backend Validation: Dates
    try:
        check_in = datetime.datetime.strptime(check_in_date_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Invalid check-in or check-out date format.', 'danger')
        return redirect(url_for('hotel.bookings'))

    if check_out <= check_in:
        flash('Check-out date must be strictly after check-in date.', 'danger')
        return redirect(url_for('hotel.bookings'))

    nights = (check_out - check_in).days

    # Room validation & rate calculation
    room = query('''
        SELECT r.*, rt.base_rate, rt.id AS rtid
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.id
        WHERE r.id = %s
    ''', (room_id,), one=True)

    if not room:
        flash('Selected room was not found.', 'danger')
        return redirect(url_for('hotel.bookings'))

    room_rate = float(room['base_rate'])
    room_type_id = room['rtid']
    total_amount = room_rate * nights

    # Overlapping booking check on confirmed/checked_in bookings for the same room
    overlap = query('''
        SELECT id, booking_ref FROM bookings
        WHERE room_id = %s
          AND status IN ('confirmed', 'checked_in')
          AND NOT (check_out_date <= %s OR check_in_date >= %s)
    ''', (room_id, check_in, check_out), one=True)

    if overlap:
        flash(f"Room {room['room_number']} already has an active booking ({overlap['booking_ref']}) for these dates.", 'danger')
        return redirect(url_for('hotel.bookings'))

    # Generate unique booking reference BK-YYYY-XXXX
    year = datetime.date.today().year
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    booking_ref = f"BK-{year}-{suffix}"

    user_id = session.get('user_id')

    booking_id = execute('''
        INSERT INTO bookings
        (booking_ref, guest_id, room_id, room_type_id, check_in_date, check_out_date,
         nights, adults, children, status, room_rate, total_amount, paid_amount,
         special_requests, source, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        booking_ref, guest_id, room_id, room_type_id, check_in, check_out,
        nights, adults, children, status, room_rate, total_amount, advance_paid,
        special_requests, source, user_id
    ))

    # Update guest total stays count
    execute('UPDATE guests SET total_stays = total_stays + 1 WHERE id = %s', (guest_id,))

    # Update room status if checking in immediately or if status is checked_in
    if status == 'checked_in':
        execute("UPDATE rooms SET status = 'occupied' WHERE id = %s", (room_id,))
    elif status == 'confirmed' and check_in == datetime.date.today():
        execute("UPDATE rooms SET status = 'reserved' WHERE id = %s", (room_id,))

    # Generate invoice & record initial payment if advance > 0
    gst_rate = float(get_hotel_settings().get('gst_rate', 12))
    subtotal = total_amount
    tax_amount = round(subtotal * (gst_rate / 100.0), 2)
    grand_total = subtotal + tax_amount

    inv_num = f"INV-{year}-{suffix}"
    inv_status = 'paid' if advance_paid >= grand_total else ('partial' if advance_paid > 0 else 'draft')

    invoice_id = execute('''
        INSERT INTO invoices
        (invoice_number, booking_id, subtotal, tax_amount, discount, total, paid_amount, status, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (inv_num, booking_id, subtotal, tax_amount, 0.0, grand_total, advance_paid, inv_status, f"Booking {booking_ref}"))

    # Invoice items
    execute('''
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
        VALUES (%s, %s, %s, %s, %s, 'room')
    ''', (invoice_id, f"Room {room['room_number']} Stay ({nights} Nights @ ₹{room_rate:,.2f})", nights, room_rate, subtotal))

    execute('''
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
        VALUES (%s, %s, 1, %s, %s, 'tax')
    ''', (invoice_id, f"GST Tax ({gst_rate}%)", tax_amount, tax_amount))

    if advance_paid > 0:
        execute('''
            INSERT INTO payments (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Advance payment at booking creation')
        ''', (invoice_id, booking_id, advance_paid, payment_method, f"ADV-{suffix}", user_id))

    flash(f"Booking {booking_ref} created successfully!", 'success')
    return redirect(url_for('hotel.bookings'))


@hotel_bp.route('/bookings/<int:booking_id>/check-in', methods=['POST'], endpoint='checkin_booking')
@hotel_staff_required
def checkin_booking(booking_id):
    booking = query('SELECT * FROM bookings WHERE id = %s', (booking_id,), one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('hotel.bookings'))

    if booking['status'] not in ('confirmed', 'pending'):
        flash(f"Cannot check in booking with status '{booking['status']}'.", 'warning')
        return redirect(url_for('hotel.bookings'))

    execute("UPDATE bookings SET status = 'checked_in' WHERE id = %s", (booking_id,))
    if booking['room_id']:
        execute("UPDATE rooms SET status = 'occupied', housekeeping_status = 'clean' WHERE id = %s", (booking['room_id'],))

    flash(f"Booking {booking['booking_ref']} checked in successfully!", 'success')
    return redirect(request.referrer or url_for('hotel.bookings'))


@hotel_bp.route('/bookings/<int:booking_id>/check-out', methods=['POST'], endpoint='checkout_booking')
@hotel_staff_required
def checkout_booking(booking_id):
    booking = query('SELECT * FROM bookings WHERE id = %s', (booking_id,), one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('hotel.bookings'))

    if booking['status'] != 'checked_in':
        flash('Only checked-in guests can be checked out.', 'warning')
        return redirect(url_for('hotel.bookings'))

    execute("UPDATE bookings SET status = 'checked_out' WHERE id = %s", (booking_id,))

    # Update room to cleaning and dirty, and automatically trigger checkout housekeeping task
    if booking['room_id']:
        execute("UPDATE rooms SET status = 'cleaning', housekeeping_status = 'dirty' WHERE id = %s", (booking['room_id'],))
        execute('''
            INSERT INTO housekeeping_tasks (room_id, assigned_to, status, priority, task_type, notes)
            VALUES (%s, %s, 'pending', 'urgent', 'checkout_clean', %s)
        ''', (booking['room_id'], session.get('user_id'), f"Checkout clean for {booking['booking_ref']}"))

    flash(f"Booking {booking['booking_ref']} checked out! Room set to cleaning.", 'success')
    return redirect(request.referrer or url_for('hotel.bookings'))


@hotel_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'], endpoint='cancel_booking')
@hotel_staff_required
def cancel_booking(booking_id):
    booking = query('SELECT * FROM bookings WHERE id = %s', (booking_id,), one=True)
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('hotel.bookings'))

    execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
    if booking['room_id'] and booking['status'] == 'confirmed':
        # Free up room if it was held
        execute("UPDATE rooms SET status = 'available' WHERE id = %s AND status = 'reserved'", (booking['room_id'],))

    flash(f"Booking {booking['booking_ref']} cancelled.", 'info')
    return redirect(request.referrer or url_for('hotel.bookings'))


# ─── 4. GUEST MANAGEMENT ──────────────────────────────────────────────────────

@hotel_bp.route('/guests', endpoint='guests')
@hotel_staff_required
def guests():
    search = request.args.get('search', '').strip()
    sql = '''
        SELECT g.*, COUNT(b.id) AS total_bookings_count,
               COALESCE(SUM(b.total_amount), 0) AS total_spent
        FROM guests g
        LEFT JOIN bookings b ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if search:
        sql += ' AND (g.full_name LIKE %s OR g.email LIKE %s OR g.phone LIKE %s OR g.id_number LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])

    sql += ' GROUP BY g.id ORDER BY total_spent DESC, g.id DESC'
    guest_list = query(sql, tuple(params))

    return render_template('hotel/guests.html', guests=guest_list, search=search)


@hotel_bp.route('/guests/add', methods=['POST'], endpoint='add_guest')
@hotel_staff_required
def add_guest():
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    address = request.form.get('address', '').strip()
    id_type = request.form.get('id_type', '')
    id_number = request.form.get('id_number', '').strip()
    notes = request.form.get('notes', '').strip()

    if not full_name or not phone:
        flash('Full name and phone are required.', 'danger')
        return redirect(url_for('hotel.guests'))

    execute('''
        INSERT INTO guests (full_name, email, phone, address, id_type, id_number, total_stays, notes)
        VALUES (%s, %s, %s, %s, %s, %s, 0, %s)
    ''', (full_name, email, phone, address, id_type, id_number, notes))

    flash(f'Guest {full_name} registered successfully!', 'success')
    return redirect(url_for('hotel.guests'))


@hotel_bp.route('/guests/<int:guest_id>', endpoint='guest_detail')
@hotel_staff_required
def guest_detail(guest_id):
    guest = query('SELECT * FROM guests WHERE id = %s', (guest_id,), one=True)
    if not guest:
        flash('Guest not found.', 'danger')
        return redirect(url_for('hotel.guests'))

    guest_bookings = query('''
        SELECT b.*, r.room_number, rt.name AS room_type_name
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.guest_id = %s
        ORDER BY b.check_in_date DESC
    ''', (guest_id,))

    return render_template('hotel/guest_detail.html', guest=guest, bookings=guest_bookings)


# ─── 5. BILLING & INVOICES ────────────────────────────────────────────────────

@hotel_bp.route('/billing', endpoint='billing')
@hotel_staff_required
def billing():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    sql = '''
        SELECT inv.*, b.booking_ref, b.check_in_date, b.check_out_date,
               g.full_name AS guest_name, g.phone AS guest_phone,
               (inv.total - inv.paid_amount) AS balance_due
        FROM invoices inv
        JOIN bookings b ON inv.booking_id = b.id
        JOIN guests g   ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if status_filter and status_filter != 'all':
        sql += ' AND inv.status = %s'
        params.append(status_filter)
    if search:
        sql += ' AND (inv.invoice_number LIKE %s OR b.booking_ref LIKE %s OR g.full_name LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%'])

    sql += ' ORDER BY inv.issued_at DESC'
    invoice_list = query(sql, tuple(params))

    # Totals
    total_billed = query('SELECT COALESCE(SUM(total), 0) AS s FROM invoices', one=True)['s']
    total_collected = query('SELECT COALESCE(SUM(paid_amount), 0) AS s FROM invoices', one=True)['s']
    total_outstanding = query("SELECT COALESCE(SUM(total - paid_amount), 0) AS s FROM invoices WHERE status IN ('issued', 'partial')", one=True)['s']

    # Bookings that need invoices
    unbilled_bookings = query('''
        SELECT b.id, b.booking_ref, b.total_amount, g.full_name AS guest_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN invoices inv ON inv.booking_id = b.id
        WHERE inv.id IS NULL
    ''')

    return render_template('hotel/billing.html',
                           invoices=invoice_list,
                           total_billed=float(total_billed),
                           total_collected=float(total_collected),
                           total_outstanding=float(total_outstanding),
                           unbilled_bookings=unbilled_bookings,
                           selected_status=status_filter,
                           search=search)


@hotel_bp.route('/invoices/<int:invoice_id>', endpoint='invoice_detail')
@hotel_staff_required
def invoice_detail(invoice_id):
    invoice = query('''
        SELECT inv.*, b.booking_ref, b.check_in_date, b.check_out_date, b.nights,
               g.full_name AS guest_name, g.email AS guest_email, g.phone AS guest_phone,
               g.address AS guest_address, g.id_type, g.id_number,
               r.room_number, rt.name AS room_type_name
        FROM invoices inv
        JOIN bookings b ON inv.booking_id = b.id
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE inv.id = %s
    ''', (invoice_id,), one=True)

    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('hotel.billing'))

    items = query('SELECT * FROM invoice_items WHERE invoice_id = %s ORDER BY id ASC', (invoice_id,))
    payments = query('''
        SELECT p.*, u.name AS recorded_by_name
        FROM payments p
        LEFT JOIN users u ON p.recorded_by = u.id
        WHERE p.invoice_id = %s
        ORDER BY p.payment_date DESC, p.id DESC
    ''', (invoice_id,))

    return render_template('hotel/invoice_view.html',
                           invoice=invoice,
                           items=items,
                           payments=payments)


@hotel_bp.route('/invoices/<int:invoice_id>/pay', methods=['POST'], endpoint='add_payment')
@hotel_staff_required
def add_payment(invoice_id):
    amount = request.form.get('amount', type=float)
    method = request.form.get('method', 'cash')
    reference = request.form.get('reference', '').strip()
    payment_date = request.form.get('payment_date', datetime.date.today().isoformat())
    notes = request.form.get('notes', '').strip()

    invoice = query('SELECT * FROM invoices WHERE id = %s', (invoice_id,), one=True)
    if not invoice:
        flash('Invoice not found.', 'danger')
        return redirect(url_for('hotel.billing'))

    if not amount or amount <= 0:
        flash('Payment amount must be greater than zero.', 'danger')
        return redirect(url_for('hotel.invoice_detail', invoice_id=invoice_id))

    user_id = session.get('user_id')

    # Execute insert payment
    execute('''
        INSERT INTO payments (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ''', (invoice_id, invoice['booking_id'], amount, method, reference or f"PAY-{random.randint(10000,99999)}", user_id, payment_date, notes))

    # Recalculate invoice totals
    new_paid = float(invoice['paid_amount']) + amount
    total = float(invoice['total'])
    new_status = 'paid' if new_paid >= total else 'partial'

    execute('UPDATE invoices SET paid_amount = %s, status = %s WHERE id = %s', (new_paid, new_status, invoice_id))
    execute('UPDATE bookings SET paid_amount = paid_amount + %s WHERE id = %s', (amount, invoice['booking_id']))

    flash(f"Payment of ₹{amount:,.2f} recorded successfully!", 'success')
    return redirect(url_for('hotel.invoice_detail', invoice_id=invoice_id))


# ─── 6. HOUSEKEEPING ──────────────────────────────────────────────────────────

@hotel_bp.route('/housekeeping', endpoint='housekeeping')
@hotel_staff_required
def housekeeping():
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT ht.*, r.room_number, r.floor, r.housekeeping_status,
               u.name AS staff_name
        FROM housekeeping_tasks ht
        JOIN rooms r ON ht.room_id = r.id
        LEFT JOIN users u ON ht.assigned_to = u.id
        WHERE 1=1
    '''
    params = []
    if status_filter and status_filter != 'all':
        sql += ' AND ht.status = %s'
        params.append(status_filter)

    sql += ' ORDER BY FIELD(ht.priority, "urgent", "high", "normal", "low"), ht.id DESC'
    tasks = query(sql, tuple(params))

    # Room hygiene status overview
    rooms = query('''
        SELECT r.id, r.room_number, r.floor, r.status, r.housekeeping_status, rt.name AS room_type_name
        FROM rooms r
        LEFT JOIN room_types rt ON r.room_type_id = rt.id
        ORDER BY r.floor ASC, r.room_number ASC
    ''')
    staff_users = query("SELECT id, name, username FROM users ORDER BY name ASC")

    counts = {
        'all': query('SELECT COUNT(*) AS c FROM housekeeping_tasks', one=True)['c'],
        'pending': query("SELECT COUNT(*) AS c FROM housekeeping_tasks WHERE status='pending'", one=True)['c'],
        'in_progress': query("SELECT COUNT(*) AS c FROM housekeeping_tasks WHERE status='in_progress'", one=True)['c'],
        'completed': query("SELECT COUNT(*) AS c FROM housekeeping_tasks WHERE status='completed'", one=True)['c'],
        'inspected': query("SELECT COUNT(*) AS c FROM housekeeping_tasks WHERE status='inspected'", one=True)['c'],
    }

    return render_template('hotel/housekeeping.html',
                           tasks=tasks,
                           rooms=rooms,
                           staff=staff_users,
                           counts=counts,
                           selected_status=status_filter)


@hotel_bp.route('/housekeeping/add', methods=['POST'], endpoint='add_housekeeping_task')
@hotel_staff_required
def add_housekeeping_task():
    room_id = request.form.get('room_id', type=int)
    assigned_to = request.form.get('assigned_to', type=int) or session.get('user_id')
    task_type = request.form.get('task_type', 'daily_clean')
    priority = request.form.get('priority', 'normal')
    notes = request.form.get('notes', '').strip()

    if not room_id:
        flash('Please select a room.', 'danger')
        return redirect(url_for('hotel.housekeeping'))

    execute('''
        INSERT INTO housekeeping_tasks (room_id, assigned_to, status, priority, task_type, notes)
        VALUES (%s, %s, 'pending', %s, %s, %s)
    ''', (room_id, assigned_to, priority, task_type, notes))

    # Update room housekeeping status
    execute("UPDATE rooms SET housekeeping_status = 'dirty' WHERE id = %s", (room_id,))

    flash('Housekeeping task created!', 'success')
    return redirect(url_for('hotel.housekeeping'))


@hotel_bp.route('/housekeeping/<int:task_id>/update', methods=['POST'], endpoint='update_housekeeping_status')
@hotel_staff_required
def update_housekeeping_status(task_id):
    status = request.form.get('status')
    valid = ('pending', 'in_progress', 'completed', 'inspected')
    if status not in valid:
        flash('Invalid task status.', 'danger')
        return redirect(url_for('hotel.housekeeping'))

    task = query('SELECT * FROM housekeeping_tasks WHERE id = %s', (task_id,), one=True)
    if not task:
        flash('Task not found.', 'danger')
        return redirect(url_for('hotel.housekeeping'))

    now = datetime.datetime.now()
    if status == 'in_progress':
        execute('UPDATE housekeeping_tasks SET status = %s, started_at = %s WHERE id = %s', (status, now, task_id))
        execute("UPDATE rooms SET housekeeping_status = 'inspecting' WHERE id = %s", (task['room_id'],))
    elif status in ('completed', 'inspected'):
        execute('UPDATE housekeeping_tasks SET status = %s, completed_at = %s WHERE id = %s', (status, now, task_id))
        # If room was cleaning, mark as available and clean!
        execute('''
            UPDATE rooms
            SET housekeeping_status = 'clean',
                status = CASE WHEN status = 'cleaning' THEN 'available' ELSE status END
            WHERE id = %s
        ''', (task['room_id'],))

    flash(f"Task status changed to {status.replace('_', ' ').title()}.", 'success')
    return redirect(request.referrer or url_for('hotel.housekeeping'))


# ─── 7. MAINTENANCE ──────────────────────────────────────────────────────────

@hotel_bp.route('/maintenance', endpoint='maintenance')
@hotel_staff_required
def maintenance():
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT mr.*, r.room_number, r.floor,
               u_rep.name AS reporter_name, u_ass.name AS assignee_name
        FROM maintenance_requests mr
        LEFT JOIN rooms r ON mr.room_id = r.id
        LEFT JOIN users u_rep ON mr.reported_by = u_rep.id
        LEFT JOIN users u_ass ON mr.assigned_to = u_ass.id
        WHERE 1=1
    '''
    params = []
    if status_filter and status_filter != 'all':
        sql += ' AND mr.status = %s'
        params.append(status_filter)

    sql += ' ORDER BY FIELD(mr.priority, "urgent", "high", "normal", "low"), mr.id DESC'
    requests_list = query(sql, tuple(params))

    rooms = query('SELECT id, room_number, floor FROM rooms ORDER BY room_number ASC')
    staff = query('SELECT id, name FROM users ORDER BY name ASC')

    counts = {
        'all': query('SELECT COUNT(*) AS c FROM maintenance_requests', one=True)['c'],
        'open': query("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='open'", one=True)['c'],
        'in_progress': query("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='in_progress'", one=True)['c'],
        'resolved': query("SELECT COUNT(*) AS c FROM maintenance_requests WHERE status='resolved'", one=True)['c'],
    }

    return render_template('hotel/maintenance.html',
                           requests=requests_list,
                           rooms=rooms,
                           staff=staff,
                           counts=counts,
                           selected_status=status_filter)


@hotel_bp.route('/maintenance/add', methods=['POST'], endpoint='add_maintenance_request')
@hotel_staff_required
def add_maintenance_request():
    room_id = request.form.get('room_id', type=int) or None
    issue = request.form.get('issue', '').strip()
    priority = request.form.get('priority', 'normal')
    assigned_to = request.form.get('assigned_to', type=int) or None
    notes = request.form.get('notes', '').strip()

    if not issue:
        flash('Issue description is required.', 'danger')
        return redirect(url_for('hotel.maintenance'))

    reporter_id = session.get('user_id')

    execute('''
        INSERT INTO maintenance_requests (room_id, reported_by, assigned_to, issue, priority, status, notes)
        VALUES (%s, %s, %s, %s, %s, 'open', %s)
    ''', (room_id, reporter_id, assigned_to, issue, priority, notes))

    # If priority is urgent and linked to a room, place room under maintenance
    if room_id and priority in ('urgent', 'high'):
        execute("UPDATE rooms SET status = 'maintenance' WHERE id = %s", (room_id,))

    flash('Maintenance ticket created!', 'success')
    return redirect(url_for('hotel.maintenance'))


@hotel_bp.route('/maintenance/<int:req_id>/update', methods=['POST'], endpoint='update_maintenance_status')
@hotel_staff_required
def update_maintenance_status(req_id):
    status = request.form.get('status')
    valid = ('open', 'in_progress', 'resolved', 'closed')
    if status not in valid:
        flash('Invalid status.', 'danger')
        return redirect(url_for('hotel.maintenance'))

    req = query('SELECT * FROM maintenance_requests WHERE id = %s', (req_id,), one=True)
    if not req:
        flash('Maintenance ticket not found.', 'danger')
        return redirect(url_for('hotel.maintenance'))

    now = datetime.datetime.now() if status in ('resolved', 'closed') else None
    execute('UPDATE maintenance_requests SET status = %s, resolved_at = %s WHERE id = %s', (status, now, req_id))

    # If resolved, and room was under maintenance, revert room to available
    if status in ('resolved', 'closed') and req['room_id']:
        execute("UPDATE rooms SET status = 'available' WHERE id = %s AND status = 'maintenance'", (req['room_id'],))

    flash(f"Maintenance ticket #{req_id} marked as {status}.", 'success')
    return redirect(request.referrer or url_for('hotel.maintenance'))


# ─── 8. EXPENSES ──────────────────────────────────────────────────────────────

@hotel_bp.route('/expenses', endpoint='expenses')
@hotel_staff_required
def expenses():
    category_filter = request.args.get('category', '')

    sql = '''
        SELECT e.*, u.name AS recorder_name
        FROM expenses e
        LEFT JOIN users u ON e.recorded_by = u.id
        WHERE 1=1
    '''
    params = []
    if category_filter:
        sql += ' AND e.category = %s'
        params.append(category_filter)

    sql += ' ORDER BY e.expense_date DESC, e.id DESC'
    expense_list = query(sql, tuple(params))

    # Category summaries
    category_totals = query('''
        SELECT category, COUNT(*) AS count, SUM(amount) AS total
        FROM expenses
        GROUP BY category ORDER BY total DESC
    ''')

    grand_total = query('SELECT COALESCE(SUM(amount), 0) AS total FROM expenses', one=True)['total']

    categories = [
        'Linen & Laundry',
        'Kitchen Supplies',
        'Utilities',
        'Maintenance & Repairs',
        'Housekeeping Supplies',
        'Toiletries & Amenities',
        'Internet & Telecom',
        'Garden & Landscaping',
        'Stationery & Office',
        'Beverages & Minibar',
        'Other'
    ]

    return render_template('hotel/expenses.html',
                           expenses=expense_list,
                           category_totals=category_totals,
                           grand_total=float(grand_total),
                           categories=categories,
                           selected_category=category_filter)


@hotel_bp.route('/expenses/add', methods=['POST'], endpoint='add_expense')
@hotel_staff_required
def add_expense():
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    amount = request.form.get('amount', type=float)
    method = request.form.get('method', 'cash')
    expense_date = request.form.get('expense_date', datetime.date.today().isoformat())

    if not category or not description or not amount or amount <= 0:
        flash('Category, description, and valid amount are required.', 'danger')
        return redirect(url_for('hotel.expenses'))

    user_id = session.get('user_id')
    execute('''
        INSERT INTO expenses (category, description, amount, method, expense_date, recorded_by)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (category, description, amount, method, expense_date, user_id))

    flash(f"Expense of ₹{amount:,.2f} recorded.", 'success')
    return redirect(url_for('hotel.expenses'))


# ─── 9. HOTEL SETTINGS ────────────────────────────────────────────────────────

@hotel_bp.route('/settings', endpoint='settings')
@hotel_staff_required
def settings():
    current_settings = get_hotel_settings()
    return render_template('hotel/settings.html', settings=current_settings)


@hotel_bp.route('/settings/update', methods=['POST'], endpoint='update_settings')
@hotel_staff_required
def update_settings():
    keys = ['hotel_name', 'hotel_address', 'hotel_phone', 'hotel_email',
            'check_in_time', 'check_out_time', 'gst_rate', 'currency', 'currency_symbol']

    for k in keys:
        val = request.form.get(k, '').strip()
        if val:
            execute('''
                INSERT INTO hotel_settings (setting_key, setting_val)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE setting_val = VALUES(setting_val)
            ''', (k, val))

    flash('Hotel settings updated successfully!', 'success')
    return redirect(url_for('hotel.settings'))

