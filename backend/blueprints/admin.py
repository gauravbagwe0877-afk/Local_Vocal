from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import query, execute
from auth_decorators import admin_required, log_activity
import datetime
import json
import bcrypt

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def get_hotel_settings():
    rows = query('SELECT setting_key, setting_val FROM hotel_settings')
    settings = {r['setting_key']: r['setting_val'] for r in rows}
    settings.setdefault('hotel_name', 'StaySmart Hotel & Suites')
    settings.setdefault('currency_symbol', '₹')
    settings.setdefault('gst_rate', '12')
    return settings

@admin_bp.context_processor
def inject_admin_globals():
    return {
        'hotel_settings': get_hotel_settings(),
        'today_date': datetime.date.today().isoformat()
    }


# ─── 1. ADMIN DASHBOARD OVERVIEW ──────────────────────────────────────────────

@admin_bp.route('/', endpoint='index')
@admin_bp.route('/dashboard', endpoint='dashboard')
@admin_bp.route('/dashboard_overview', endpoint='admin_dashboard')
@admin_required
def dashboard():
    today = datetime.date.today()

    # Room statistics
    rooms = query('''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate
        FROM rooms r
        LEFT JOIN room_types rt ON r.room_type_id = rt.id
        ORDER BY r.floor ASC, r.room_number ASC
    ''')
    total_rooms = len(rooms)
    available_rooms = sum(1 for r in rooms if r['status'] == 'available')
    occupied_rooms = sum(1 for r in rooms if r['status'] == 'occupied')
    reserved_rooms = sum(1 for r in rooms if r['status'] == 'reserved')
    cleaning_rooms = sum(1 for r in rooms if r['status'] in ('cleaning', 'inspected'))
    maintenance_rooms = sum(1 for r in rooms if r['status'] == 'maintenance')
    occupancy_rate = round((occupied_rooms / total_rooms * 100), 1) if total_rooms > 0 else 0

    # Bookings statistics
    total_bookings = query('SELECT COUNT(*) AS c FROM bookings', one=True)['c']
    active_bookings = query("SELECT COUNT(*) AS c FROM bookings WHERE status IN ('confirmed', 'checked_in')", one=True)['c']

    # Financial revenue summaries
    total_revenue_row = query('SELECT COALESCE(SUM(amount), 0) AS total_rev FROM payments', one=True)
    total_revenue = float(total_revenue_row['total_rev'])

    mtd_revenue_row = query('''
        SELECT COALESCE(SUM(amount), 0) AS mtd_rev FROM payments
        WHERE payment_date >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
    ''', one=True)
    mtd_revenue = float(mtd_revenue_row['mtd_rev'])

    pending_dues_row = query('''
        SELECT COALESCE(SUM(total - paid_amount), 0) AS pending_due
        FROM invoices WHERE status IN ('issued', 'partial')
    ''', one=True)
    pending_dues = float(pending_dues_row['pending_due'])

    # Customer & Staff counts
    total_customers = query("SELECT COUNT(*) AS c FROM users WHERE role IN ('customer', 'user')", one=True)['c']
    total_receptionists = query("SELECT COUNT(*) AS c FROM users WHERE role = 'receptionist'", one=True)['c']

    # Recent bookings
    recent_bookings = query('''
        SELECT b.*, g.full_name AS guest_name, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        ORDER BY b.created_at DESC LIMIT 6
    ''')

    # Recent receptionist & system activity logs
    recent_activities = query('''
        SELECT al.*, u.name AS user_name, u.role AS user_role
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC LIMIT 8
    ''')

    stats = {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'reserved_rooms': reserved_rooms,
        'cleaning_rooms': cleaning_rooms,
        'maintenance_rooms': maintenance_rooms,
        'occupancy_rate': occupancy_rate,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
        'total_revenue': total_revenue,
        'mtd_revenue': mtd_revenue,
        'pending_dues': pending_dues,
        'total_customers': total_customers,
        'total_receptionists': total_receptionists,
    }

    return render_template('admin/dashboard.html',
                           stats=stats,
                           rooms=rooms,
                           recent_bookings=recent_bookings,
                           recent_activities=recent_activities)


# ─── 2. ROOM MANAGEMENT (ADD, UPDATE, DELETE) ─────────────────────────────────

@admin_bp.route('/rooms', endpoint='rooms')
@admin_bp.route('/rooms_management', endpoint='admin_rooms')
@admin_required
def rooms():
    floor_filter = request.args.get('floor', '')
    status_filter = request.args.get('status', '')

    sql = '''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate,
               b.booking_ref, g.full_name AS current_guest_name
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
    room_types = query('SELECT * FROM room_types ORDER BY base_rate ASC')
    all_rooms = query('SELECT floor, status FROM rooms')
    floors = sorted(list(set(r['floor'] for r in all_rooms if r['floor'])))

    counts = {
        'all': len(all_rooms),
        'available': sum(1 for r in all_rooms if r['status'] == 'available'),
        'occupied': sum(1 for r in all_rooms if r['status'] == 'occupied'),
        'cleaning': sum(1 for r in all_rooms if r['status'] == 'cleaning'),
        'maintenance': sum(1 for r in all_rooms if r['status'] == 'maintenance'),
        'reserved': sum(1 for r in all_rooms if r['status'] == 'reserved'),
    }

    return render_template('admin/rooms.html',
                           rooms=room_list,
                           room_types=room_types,
                           floors=floors,
                           counts=counts,
                           selected_floor=floor_filter,
                           selected_status=status_filter)

@admin_bp.route('/rooms/add', methods=['POST'], endpoint='add_room')
@admin_required
def add_room():
    room_number = request.form.get('room_number', '').strip()
    floor = request.form.get('floor', '').strip()
    room_type_id = request.form.get('room_type_id')
    status = request.form.get('status', 'available')
    notes = request.form.get('notes', '').strip()

    if not room_number or not floor or not room_type_id:
        flash('Room number, floor, and category are required.', 'danger')
        return redirect(url_for('admin.rooms'))

    existing = query('SELECT id FROM rooms WHERE room_number = %s', (room_number,), one=True)
    if existing:
        flash(f'Room number {room_number} already exists.', 'danger')
        return redirect(url_for('admin.rooms'))

    execute('''
        INSERT INTO rooms (room_number, floor, room_type_id, status, housekeeping_status, notes)
        VALUES (%s, %s, %s, %s, 'clean', %s)
    ''', (room_number, floor, room_type_id, status, notes))

    log_activity('ADMIN_ADD_ROOM', f"Admin added Room {room_number} on {floor}.")
    flash(f'Room {room_number} added successfully!', 'success')
    return redirect(url_for('admin.rooms'))

@admin_bp.route('/rooms/<int:room_id>/edit', methods=['POST'], endpoint='edit_room')
@admin_required
def edit_room(room_id):
    room_number = request.form.get('room_number', '').strip()
    floor = request.form.get('floor', '').strip()
    room_type_id = request.form.get('room_type_id')
    status = request.form.get('status', 'available')
    housekeeping_status = request.form.get('housekeeping_status', 'clean')
    notes = request.form.get('notes', '').strip()

    execute('''
        UPDATE rooms
        SET room_number = %s, floor = %s, room_type_id = %s, status = %s, housekeeping_status = %s, notes = %s
        WHERE id = %s
    ''', (room_number, floor, room_type_id, status, housekeeping_status, notes, room_id))

    log_activity('ADMIN_UPDATE_ROOM', f"Admin updated Room {room_number} (Status: {status}).")
    flash(f'Room {room_number} updated successfully.', 'success')
    return redirect(url_for('admin.rooms'))

@admin_bp.route('/rooms/<int:room_id>/delete', methods=['POST'], endpoint='delete_room')
@admin_required
def delete_room(room_id):
    room = query('SELECT room_number FROM rooms WHERE id = %s', (room_id,), one=True)
    if room:
        execute('DELETE FROM rooms WHERE id = %s', (room_id,))
        log_activity('ADMIN_DELETE_ROOM', f"Admin deleted Room {room['room_number']}.")
        flash(f"Room {room['room_number']} deleted.", 'info')
    return redirect(url_for('admin.rooms'))


# ─── 3. ROOM CATEGORIES & PRICING ─────────────────────────────────────────────

@admin_bp.route('/room-types', endpoint='room_types')
@admin_required
def room_types():
    types = query('''
        SELECT rt.*, COUNT(r.id) AS room_count
        FROM room_types rt
        LEFT JOIN rooms r ON r.room_type_id = rt.id
        GROUP BY rt.id
        ORDER BY rt.base_rate ASC
    ''')
    for t in types:
        if isinstance(t.get('amenities'), str):
            try:
                t['amenities_list'] = json.loads(t['amenities'])
            except Exception:
                t['amenities_list'] = [a.strip() for a in t['amenities'].split(',') if a.strip()]
        else:
            t['amenities_list'] = t.get('amenities') or []
    return render_template('admin/room_types.html', room_types=types)

@admin_bp.route('/room-types/add', methods=['POST'], endpoint='add_room_type')
@admin_required
def add_room_type():
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    base_rate = request.form.get('base_rate', type=float)
    max_adults = request.form.get('max_adults', default=2, type=int)
    max_children = request.form.get('max_children', default=1, type=int)
    image_url = request.form.get('image_url', '').strip()
    amenities_raw = request.form.get('amenities', '').strip()
    amenities = [a.strip() for a in amenities_raw.split(',') if a.strip()]

    if not name or not base_rate or base_rate <= 0:
        flash('Category name and positive base rate are required.', 'danger')
        return redirect(url_for('admin.room_types'))

    execute('''
        INSERT INTO room_types (name, description, max_adults, max_children, base_rate, amenities, image_url, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 1)
    ''', (name, description, max_adults, max_children, base_rate, json.dumps(amenities), image_url))

    log_activity('ADMIN_ADD_ROOM_TYPE', f"Admin added room category: {name} (Rate: ₹{base_rate}).")
    flash(f'Room category {name} created successfully!', 'success')
    return redirect(url_for('admin.room_types'))

@admin_bp.route('/room-types/<int:type_id>/edit', methods=['POST'], endpoint='edit_room_type')
@admin_required
def edit_room_type(type_id):
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    base_rate = request.form.get('base_rate', type=float)
    max_adults = request.form.get('max_adults', default=2, type=int)
    max_children = request.form.get('max_children', default=1, type=int)
    image_url = request.form.get('image_url', '').strip()
    amenities_raw = request.form.get('amenities', '').strip()
    amenities = [a.strip() for a in amenities_raw.split(',') if a.strip()]

    execute('''
        UPDATE room_types
        SET name = %s, description = %s, max_adults = %s, max_children = %s,
            base_rate = %s, amenities = %s, image_url = %s
        WHERE id = %s
    ''', (name, description, max_adults, max_children, base_rate, json.dumps(amenities), image_url, type_id))

    log_activity('ADMIN_UPDATE_ROOM_TYPE', f"Admin updated room category: {name} (Rate: ₹{base_rate}).")
    flash(f'Room category {name} updated.', 'success')
    return redirect(url_for('admin.room_types'))


# ─── 4. CUSTOMER MANAGEMENT ───────────────────────────────────────────────────

@admin_bp.route('/customers', endpoint='customers')
@admin_required
def customers():
    search = request.args.get('search', '').strip()
    sql = '''
        SELECT g.*, u.username, u.is_active AS user_active,
               COUNT(b.id) AS bookings_count,
               COALESCE(SUM(b.total_amount), 0) AS lifetime_spent
        FROM guests g
        LEFT JOIN users u ON g.user_id = u.id
        LEFT JOIN bookings b ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if search:
        sql += ' AND (g.full_name LIKE %s OR g.phone LIKE %s OR g.email LIKE %s OR g.id_number LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
    sql += ' GROUP BY g.id ORDER BY lifetime_spent DESC, g.id DESC'

    customer_list = query(sql, tuple(params))
    return render_template('admin/customers.html', customers=customer_list, search=search)


# ─── 5. RECEPTIONIST & STAFF MANAGEMENT ───────────────────────────────────────

@admin_bp.route('/receptionists', endpoint='receptionists')
@admin_required
def receptionists():
    staff_members = query('''
        SELECT u.*, 
               (SELECT COUNT(*) FROM activity_logs WHERE user_id = u.id) AS action_count,
               (SELECT MAX(created_at) FROM activity_logs WHERE user_id = u.id) AS last_active
        FROM users u
        WHERE u.role = 'receptionist'
        ORDER BY u.created_at DESC
    ''')
    return render_template('admin/receptionists.html', receptionists=staff_members)

@admin_bp.route('/receptionists/create', methods=['POST'], endpoint='create_receptionist')
@admin_required
def create_receptionist():
    name = request.form.get('name', '').strip()
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '')

    if not all([name, username, email, password]):
        flash('All required fields must be filled.', 'danger')
        return redirect(url_for('admin.receptionists'))

    existing = query('SELECT id FROM users WHERE username = %s OR email = %s', (username, email), one=True)
    if existing:
        flash('Username or email is already in use.', 'danger')
        return redirect(url_for('admin.receptionists'))

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    execute('''
        INSERT INTO users (name, username, email, phone, password_hash, role, is_active)
        VALUES (%s, %s, %s, %s, %s, 'receptionist', 1)
    ''', (name, username, email, phone, pw_hash))

    log_activity('ADMIN_CREATE_RECEPTIONIST', f"Admin created receptionist account: {name} ({username}).")
    flash(f"Receptionist account for {name} created successfully!", 'success')
    return redirect(url_for('admin.receptionists'))

@admin_bp.route('/receptionists/<int:user_id>/update', methods=['POST'], endpoint='update_receptionist')
@admin_required
def update_receptionist(user_id):
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    password = request.form.get('password', '').strip()

    if password:
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        execute('UPDATE users SET name=%s, email=%s, phone=%s, password_hash=%s WHERE id=%s AND role="receptionist"',
                (name, email, phone, pw_hash, user_id))
    else:
        execute('UPDATE users SET name=%s, email=%s, phone=%s WHERE id=%s AND role="receptionist"',
                (name, email, phone, user_id))

    log_activity('ADMIN_UPDATE_RECEPTIONIST', f"Admin updated receptionist ID #{user_id}.")
    flash('Receptionist account updated.', 'success')
    return redirect(url_for('admin.receptionists'))

@admin_bp.route('/receptionists/<int:user_id>/toggle-status', methods=['POST'], endpoint='toggle_receptionist_status')
@admin_required
def toggle_receptionist_status(user_id):
    user = query('SELECT name, is_active FROM users WHERE id = %s AND role = "receptionist"', (user_id,), one=True)
    if user:
        new_status = 0 if user['is_active'] else 1
        execute('UPDATE users SET is_active = %s WHERE id = %s', (new_status, user_id))
        status_text = 'activated' if new_status else 'deactivated'
        log_activity('ADMIN_TOGGLE_STAFF', f"Admin {status_text} receptionist account for {user['name']}.")
        flash(f"Account for {user['name']} has been {status_text}.", 'info')
    return redirect(url_for('admin.receptionists'))


# ─── 6. BOOKINGS & RESERVATION MANAGEMENT ─────────────────────────────────────

@admin_bp.route('/bookings', endpoint='bookings')
@admin_required
def bookings():
    status = request.args.get('status', '')
    search = request.args.get('search', '').strip()

    sql = '''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone,
               r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE 1=1
    '''
    params = []
    if status and status != 'all':
        sql += ' AND b.status = %s'
        params.append(status)
    if search:
        sql += ' AND (b.booking_ref LIKE %s OR g.full_name LIKE %s OR g.phone LIKE %s OR r.room_number LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
    sql += ' ORDER BY b.check_in_date DESC, b.id DESC'

    booking_list = query(sql, tuple(params))
    counts = {
        'all': query('SELECT COUNT(*) AS c FROM bookings', one=True)['c'],
        'confirmed': query("SELECT COUNT(*) AS c FROM bookings WHERE status='confirmed'", one=True)['c'],
        'checked_in': query("SELECT COUNT(*) AS c FROM bookings WHERE status='checked_in'", one=True)['c'],
        'checked_out': query("SELECT COUNT(*) AS c FROM bookings WHERE status='checked_out'", one=True)['c'],
        'cancelled': query("SELECT COUNT(*) AS c FROM bookings WHERE status='cancelled'", one=True)['c'],
    }

    return render_template('admin/bookings.html',
                           bookings=booking_list,
                           counts=counts,
                           selected_status=status,
                           search=search)

@admin_bp.route('/bookings/<int:booking_id>/update-status', methods=['POST'], endpoint='update_booking_status')
@admin_required
def update_booking_status(booking_id):
    new_status = request.form.get('status')
    valid = ('pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled', 'no_show')
    if new_status in valid:
        b = query('SELECT booking_ref, room_id FROM bookings WHERE id = %s', (booking_id,), one=True)
        execute('UPDATE bookings SET status = %s WHERE id = %s', (new_status, booking_id))

        # Room status sync
        if b and b['room_id']:
            if new_status == 'checked_in':
                execute("UPDATE rooms SET status = 'occupied' WHERE id = %s", (b['room_id'],))
            elif new_status == 'checked_out':
                execute("UPDATE rooms SET status = 'cleaning', housekeeping_status = 'dirty' WHERE id = %s", (b['room_id'],))
            elif new_status == 'cancelled':
                execute("UPDATE rooms SET status = 'available' WHERE id = %s AND status = 'reserved'", (b['room_id'],))

        log_activity('ADMIN_BOOKING_UPDATE', f"Admin set booking {b['booking_ref']} to {new_status}.")
        flash(f"Booking {b['booking_ref']} updated to {new_status.replace('_', ' ').capitalize()}.", 'success')

    return redirect(request.referrer or url_for('admin.bookings'))


# ─── 7. PAYMENT MANAGEMENT & TRANSACTION STATUS ───────────────────────────────

@admin_bp.route('/payments', endpoint='payments')
@admin_required
def payments():
    method_filter = request.args.get('method', '')
    sql = '''
        SELECT p.*, inv.invoice_number, inv.status AS invoice_status,
               b.booking_ref, g.full_name AS guest_name, u.name AS recorded_by_name
        FROM payments p
        JOIN invoices inv ON p.invoice_id = inv.id
        LEFT JOIN bookings b ON p.booking_id = b.id
        LEFT JOIN guests g ON b.guest_id = g.id
        LEFT JOIN users u ON p.recorded_by = u.id
        WHERE 1=1
    '''
    params = []
    if method_filter:
        sql += ' AND p.method = %s'
        params.append(method_filter)
    sql += ' ORDER BY p.payment_date DESC, p.id DESC'

    payment_list = query(sql, tuple(params))
    total_collected = query('SELECT COALESCE(SUM(amount), 0) AS total FROM payments', one=True)['total']

    return render_template('admin/payments.html',
                           payments=payment_list,
                           total_collected=float(total_collected),
                           selected_method=method_filter)


# ─── 8. COMPREHENSIVE REPORTS (DAILY, WEEKLY, MONTHLY) ─────────────────────────

@admin_bp.route('/reports', endpoint='reports')
@admin_required
def reports():
    period = request.args.get('period', 'daily') # daily, weekly, monthly
    today = datetime.date.today()

    if period == 'weekly':
        start_date = today - datetime.timedelta(days=7)
    elif period == 'monthly':
        start_date = today - datetime.timedelta(days=30)
    else: # daily
        start_date = today

    report_data = {
        'period': period,
        'start_date': start_date.isoformat(),
        'end_date': today.isoformat(),
        'bookings_count': query('''
            SELECT COUNT(*) AS c FROM bookings
            WHERE check_in_date BETWEEN %s AND %s
        ''', (start_date, today), one=True)['c'],
        'revenue_total': float(query('''
            SELECT COALESCE(SUM(amount), 0) AS s FROM payments
            WHERE payment_date BETWEEN %s AND %s
        ''', (start_date, today), one=True)['s']),
        'expenses_total': float(query('''
            SELECT COALESCE(SUM(amount), 0) AS s FROM expenses
            WHERE expense_date BETWEEN %s AND %s
        ''', (start_date, today), one=True)['s']),
    }
    report_data['net_profit'] = report_data['revenue_total'] - report_data['expenses_total']

    # Bookings list for period
    period_bookings = query('''
        SELECT b.*, g.full_name AS guest_name, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.check_in_date BETWEEN %s AND %s
        ORDER BY b.check_in_date DESC
    ''', (start_date, today))

    # Revenue by payment method
    method_breakdown = query('''
        SELECT method, COUNT(*) AS count, SUM(amount) AS total
        FROM payments
        WHERE payment_date BETWEEN %s AND %s
        GROUP BY method
    ''', (start_date, today))

    return render_template('admin/reports.html',
                           report=report_data,
                           bookings=period_bookings,
                           methods=method_breakdown,
                           period=period)


# ─── 9. HOTEL INFORMATION & SERVICES MANAGEMENT ───────────────────────────────

@admin_bp.route('/services', endpoint='services')
@admin_required
def services():
    services_list = query('SELECT * FROM hotel_services ORDER BY category ASC, id ASC')
    return render_template('admin/services.html', services=services_list)

@admin_bp.route('/services/add', methods=['POST'], endpoint='add_service')
@admin_required
def add_service():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', 'general').strip()
    price = request.form.get('price', default=0.0, type=float)
    icon = request.form.get('icon', '🛎️').strip()
    description = request.form.get('description', '').strip()

    execute('''
        INSERT INTO hotel_services (name, description, price, category, icon, is_active)
        VALUES (%s, %s, %s, %s, %s, 1)
    ''', (name, description, price, category, icon))

    log_activity('ADMIN_ADD_SERVICE', f"Admin added hotel service: {name} (₹{price}).")
    flash(f"Service {name} added.", 'success')
    return redirect(url_for('admin.services'))

@admin_bp.route('/services/<int:service_id>/toggle', methods=['POST'], endpoint='toggle_service')
@admin_required
def toggle_service(service_id):
    execute('UPDATE hotel_services SET is_active = NOT is_active WHERE id = %s', (service_id,))
    flash('Service status updated.', 'info')
    return redirect(url_for('admin.services'))


# ─── 10. RECEPTIONIST & STAFF ACTIVITY LOGS ───────────────────────────────────

@admin_bp.route('/activity-logs', endpoint='activity_logs')
@admin_required
def activity_logs():
    logs = query('''
        SELECT al.*, u.name AS user_name, u.username, u.role AS user_role
        FROM activity_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.created_at DESC LIMIT 100
    ''')
    return render_template('admin/activity_logs.html', logs=logs)


# ─── 11. HOTEL SETTINGS ───────────────────────────────────────────────────────

@admin_bp.route('/settings', methods=['GET', 'POST'], endpoint='settings')
@admin_required
def settings():
    if request.method == 'POST':
        keys = ['hotel_name', 'hotel_address', 'hotel_phone', 'hotel_email',
                'check_in_time', 'check_out_time', 'gst_rate', 'currency', 'currency_symbol']
        for k in keys:
            v = request.form.get(k, '').strip()
            if v:
                execute('''
                    INSERT INTO hotel_settings (setting_key, setting_val)
                    VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE setting_val = VALUES(setting_val)
                ''', (k, v))
        log_activity('ADMIN_SETTINGS_UPDATE', "Admin updated hotel settings and policies.")
        flash('Hotel settings updated successfully!', 'success')
        return redirect(url_for('admin.settings'))

    current_settings = get_hotel_settings()
    return render_template('admin/settings.html', settings=current_settings)
