from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import query, execute
from auth_decorators import receptionist_required, log_activity
import datetime
import random
import string

receptionist_bp = Blueprint('receptionist', __name__, url_prefix='/receptionist')

def get_hotel_settings():
    rows = query('SELECT setting_key, setting_val FROM hotel_settings')
    settings = {r['setting_key']: r['setting_val'] for r in rows}
    settings.setdefault('hotel_name', 'StaySmart Hotel & Suites')
    settings.setdefault('currency_symbol', '₹')
    settings.setdefault('gst_rate', '12')
    return settings

@receptionist_bp.context_processor
def inject_receptionist_globals():
    return {
        'hotel_settings': get_hotel_settings(),
        'today_date': datetime.date.today().isoformat()
    }


# ─── 1. RECEPTIONIST DASHBOARD ────────────────────────────────────────────────

@receptionist_bp.route('/', endpoint='index')
@receptionist_bp.route('/dashboard', endpoint='dashboard')
@receptionist_required
def dashboard():
    today = datetime.date.today()

    # Room status count
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

    # Today's check-ins & check-outs
    checkins_today = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.check_in_date = %s AND b.status IN ('confirmed', 'pending')
        ORDER BY b.id DESC
    ''', (today,))

    checkouts_today = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.check_out_date = %s AND b.status = 'checked_in'
        ORDER BY b.id DESC
    ''', (today,))

    inhouse_guests = query('''
        SELECT b.*, g.full_name AS guest_name, r.room_number
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        JOIN rooms r ON b.room_id = r.id
        WHERE b.status = 'checked_in'
        ORDER BY r.room_number ASC
    ''')

    stats = {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'occupied_rooms': occupied_rooms,
        'reserved_rooms': reserved_rooms,
        'cleaning_rooms': cleaning_rooms,
        'checkins_today_count': len(checkins_today),
        'checkouts_today_count': len(checkouts_today),
        'inhouse_count': len(inhouse_guests),
    }

    return render_template('receptionist/dashboard.html',
                           stats=stats,
                           rooms=rooms,
                           checkins_today=checkins_today,
                           checkouts_today=checkouts_today,
                           inhouse_guests=inhouse_guests)


# ─── 2. CUSTOMER DIRECTORY & REGISTRATION ─────────────────────────────────────

@receptionist_bp.route('/customers', endpoint='customers')
@receptionist_required
def customers():
    search = request.args.get('search', '').strip()
    booking_id = request.args.get('booking_id', '').strip()

    sql = '''
        SELECT g.*, COUNT(b.id) AS stays_count,
               COALESCE(SUM(b.total_amount), 0) AS total_spent,
               (SELECT b2.booking_ref FROM bookings b2 WHERE b2.guest_id = g.id ORDER BY b2.id DESC LIMIT 1) AS last_booking_ref
        FROM guests g
        LEFT JOIN bookings b ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if search:
        sql += ' AND (g.full_name LIKE %s OR g.phone LIKE %s OR g.email LIKE %s OR g.id_number LIKE %s)'
        params.extend([f'%{search}%', f'%{search}%', f'%{search}%', f'%{search}%'])
    if booking_id:
        sql += ' AND g.id IN (SELECT guest_id FROM bookings WHERE booking_ref LIKE %s)'
        params.append(f'%{booking_id}%')

    sql += ' GROUP BY g.id ORDER BY g.id DESC'
    customer_list = query(sql, tuple(params))

    return render_template('receptionist/customers.html',
                           customers=customer_list,
                           search=search,
                           booking_id=booking_id)

@receptionist_bp.route('/customers/new', methods=['POST'], endpoint='new_customer')
@receptionist_required
def new_customer():
    name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()
    email = request.form.get('email', '').strip()
    id_type = request.form.get('id_type', 'Aadhaar')
    id_number = request.form.get('id_number', '').strip()
    address = request.form.get('address', '').strip()
    notes = request.form.get('notes', '').strip()

    if not name or not phone:
        flash('Full name and mobile phone number are required.', 'danger')
        return redirect(url_for('receptionist.customers'))

    guest_id = execute('''
        INSERT INTO guests (full_name, phone, email, id_type, id_number, address, notes, total_stays)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
    ''', (name, phone, email, id_type, id_number, address, notes))

    log_activity('RECEPTIONIST_REGISTER_CUSTOMER', f"Receptionist registered new guest: {name} ({phone}).")
    flash(f"Guest {name} registered successfully!", 'success')
    return redirect(url_for('receptionist.customers'))


# ─── 3. ROOM AVAILABILITY & RACK ──────────────────────────────────────────────

@receptionist_bp.route('/rooms', endpoint='rooms')
@receptionist_required
def rooms():
    status = request.args.get('status', '')
    floor = request.args.get('floor', '')

    sql = '''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate, rt.amenities, rt.description AS type_desc,
               b.booking_ref, g.full_name AS current_guest_name, b.check_in_date, b.check_out_date
        FROM rooms r
        LEFT JOIN room_types rt ON r.room_type_id = rt.id
        LEFT JOIN bookings b ON b.room_id = r.id AND b.status = 'checked_in'
        LEFT JOIN guests g ON b.guest_id = g.id
        WHERE 1=1
    '''
    params = []
    if status:
        sql += ' AND r.status = %s'
        params.append(status)
    if floor:
        sql += ' AND r.floor = %s'
        params.append(floor)
    sql += ' ORDER BY r.floor ASC, r.room_number ASC'

    room_list = query(sql, tuple(params))
    room_types = query('SELECT * FROM room_types WHERE is_active = 1 ORDER BY base_rate ASC')

    return render_template('receptionist/rooms.html',
                           rooms=room_list,
                           room_types=room_types,
                           selected_status=status,
                           selected_floor=floor)


# ─── 4. NEW BOOKING & RESERVATION CREATION ────────────────────────────────────

@receptionist_bp.route('/bookings/new', methods=['GET', 'POST'], endpoint='new_booking')
@receptionist_required
def new_booking():
    if request.method == 'POST':
        guest_id = request.form.get('guest_id')
        new_name = request.form.get('new_guest_name', '').strip()
        new_phone = request.form.get('new_guest_phone', '').strip()
        new_email = request.form.get('new_guest_email', '').strip()

        room_id = request.form.get('room_id', type=int)
        check_in_str = request.form.get('check_in_date', '').strip()
        check_out_str = request.form.get('check_out_date', '').strip()
        adults = request.form.get('adults', default=1, type=int)
        children = request.form.get('children', default=0, type=int)
        advance_paid = request.form.get('advance_paid', default=0.0, type=float)
        payment_method = request.form.get('payment_method', 'cash')
        special_requests = request.form.get('special_requests', '').strip()

        # Resolve Guest
        if not guest_id or guest_id == 'new':
            if not new_name or not new_phone:
                flash('Guest name and phone are required for a new guest.', 'danger')
                return redirect(url_for('receptionist.new_booking'))
            guest_id = execute('''
                INSERT INTO guests (full_name, phone, email, total_stays)
                VALUES (%s, %s, %s, 1)
            ''', (new_name, new_phone, new_email or f"{new_phone}@guest.sawantpalace.com"))
        else:
            guest_id = int(guest_id)

        # Dates validation
        try:
            check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid check-in or check-out dates format.', 'danger')
            return redirect(url_for('receptionist.new_booking'))

        if check_out <= check_in:
            flash('Check-out date must be strictly after check-in date.', 'danger')
            return redirect(url_for('receptionist.new_booking'))

        nights = (check_out - check_in).days

        # Verify Room & Double Booking Prevention
        room = query('''
            SELECT r.*, rt.base_rate, rt.id AS rtid, rt.name AS rt_name
            FROM rooms r
            JOIN room_types rt ON r.room_type_id = rt.id
            WHERE r.id = %s
        ''', (room_id,), one=True)

        if not room:
            flash('Selected room was not found.', 'danger')
            return redirect(url_for('receptionist.new_booking'))

        # Check overlapping active bookings
        overlap = query('''
            SELECT id, booking_ref FROM bookings
            WHERE room_id = %s
              AND status IN ('confirmed', 'checked_in')
              AND NOT (check_out_date <= %s OR check_in_date >= %s)
        ''', (room_id, check_in, check_out), one=True)

        if overlap:
            flash(f"Room {room['room_number']} already has an active reservation ({overlap['booking_ref']}) for these dates. Please select an available room.", 'danger')
            return redirect(url_for('receptionist.new_booking'))

        room_rate = float(room['base_rate'])
        subtotal = room_rate * nights
        gst_rate = float(get_hotel_settings().get('gst_rate', 12))
        tax_amount = round(subtotal * (gst_rate / 100.0), 2)
        grand_total = subtotal + tax_amount

        # Generate unique Booking ID
        year = datetime.date.today().year
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        booking_ref = f"BK-{year}-{suffix}"
        user_id = session.get('user_id')

        # Insert booking
        booking_id = execute('''
            INSERT INTO bookings
            (booking_ref, guest_id, room_id, room_type_id, check_in_date, check_out_date,
             nights, adults, children, status, room_rate, total_amount, paid_amount,
             special_requests, source, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed', %s, %s, %s, %s, 'front_desk', %s)
        ''', (booking_ref, guest_id, room_id, room['rtid'], check_in, check_out,
              nights, adults, children, room_rate, grand_total, advance_paid,
              special_requests, user_id))

        execute('UPDATE guests SET total_stays = total_stays + 1 WHERE id = %s', (guest_id,))

        # Update room status if arriving today
        if check_in == datetime.date.today():
            execute("UPDATE rooms SET status = 'reserved' WHERE id = %s", (room_id,))

        # Create Invoice
        inv_num = f"INV-{year}-{suffix}"
        inv_status = 'paid' if advance_paid >= grand_total else ('partial' if advance_paid > 0 else 'issued')
        invoice_id = execute('''
            INSERT INTO invoices
            (invoice_number, booking_id, subtotal, tax_amount, discount, total, paid_amount, status, notes)
            VALUES (%s, %s, %s, %s, 0.0, %s, %s, %s, %s)
        ''', (inv_num, booking_id, subtotal, tax_amount, grand_total, advance_paid, inv_status, f"Front desk reservation {booking_ref}"))

        execute('''
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
            VALUES (%s, %s, %s, %s, %s, 'room')
        ''', (invoice_id, f"Room {room['room_number']} Stay ({nights} Nights @ ₹{room_rate:,.2f})", nights, room_rate, subtotal))

        execute('''
            INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
            VALUES (%s, %s, 1, %s, %s, 'tax')
        ''', (invoice_id, f"GST Tax ({gst_rate}%)", tax_amount, tax_amount))

        # Record advance payment if provided
        if advance_paid > 0:
            execute('''
                INSERT INTO payments (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
                VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Front desk advance payment')
            ''', (invoice_id, booking_id, advance_paid, payment_method, f"TXN-{suffix}", user_id))

        log_activity('RECEPTIONIST_CREATE_BOOKING', f"Created Booking {booking_ref} for Room {room['room_number']} (Advance: ₹{advance_paid}).")
        flash(f"Booking {booking_ref} confirmed successfully!", 'success')
        return redirect(url_for('receptionist.booking_receipt', booking_id=booking_id))

    # GET request
    rooms_available = query('''
        SELECT r.*, rt.name AS room_type_name, rt.base_rate
        FROM rooms r
        JOIN room_types rt ON r.room_type_id = rt.id
        ORDER BY r.room_number ASC
    ''')
    guests = query('SELECT id, full_name, phone, email FROM guests ORDER BY full_name ASC')

    return render_template('receptionist/new_booking.html',
                           rooms=rooms_available,
                           guests=guests)


# ─── 5. MANAGE RESERVATIONS & BOOKINGS ─────────────────────────────────────────

@receptionist_bp.route('/bookings', endpoint='bookings')
@receptionist_required
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
    return render_template('receptionist/bookings.html',
                           bookings=booking_list,
                           selected_status=status,
                           search=search)

@receptionist_bp.route('/bookings/<int:booking_id>/confirm', methods=['POST'], endpoint='confirm_booking')
@receptionist_required
def confirm_booking(booking_id):
    b = query('SELECT booking_ref FROM bookings WHERE id = %s', (booking_id,), one=True)
    if b:
        execute("UPDATE bookings SET status = 'confirmed' WHERE id = %s", (booking_id,))
        log_activity('RECEPTIONIST_CONFIRM_BOOKING', f"Confirmed reservation {b['booking_ref']}.")
        flash(f"Booking {b['booking_ref']} has been confirmed.", 'success')
    return redirect(request.referrer or url_for('receptionist.bookings'))

@receptionist_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'], endpoint='cancel_booking')
@receptionist_required
def cancel_booking(booking_id):
    b = query('SELECT booking_ref, room_id FROM bookings WHERE id = %s', (booking_id,), one=True)
    if b:
        execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
        if b['room_id']:
            execute("UPDATE rooms SET status = 'available' WHERE id = %s AND status = 'reserved'", (b['room_id'],))
        log_activity('RECEPTIONIST_CANCEL_BOOKING', f"Cancelled reservation {b['booking_ref']}.")
        flash(f"Booking {b['booking_ref']} has been cancelled according to hotel policy.", 'info')
    return redirect(request.referrer or url_for('receptionist.bookings'))


# ─── 6. CHECK-IN / CHECK-OUT OPERATIONS ────────────────────────────────────────

@receptionist_bp.route('/checkin-checkout', endpoint='checkin_checkout')
@receptionist_required
def checkin_checkout():
    today = datetime.date.today()
    pending_checkins = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.status IN ('confirmed', 'pending')
        ORDER BY b.check_in_date ASC
    ''')

    active_stays = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone, r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.status = 'checked_in'
        ORDER BY b.check_out_date ASC
    ''')

    return render_template('receptionist/checkin_checkout.html',
                           checkins=pending_checkins,
                           stays=active_stays,
                           today=today)

@receptionist_bp.route('/bookings/<int:booking_id>/checkin', methods=['POST'], endpoint='process_checkin')
@receptionist_required
def process_checkin(booking_id):
    b = query('SELECT booking_ref, room_id FROM bookings WHERE id = %s', (booking_id,), one=True)
    if b:
        execute("UPDATE bookings SET status = 'checked_in' WHERE id = %s", (booking_id,))
        if b['room_id']:
            execute("UPDATE rooms SET status = 'occupied', housekeeping_status = 'clean' WHERE id = %s", (b['room_id'],))
        log_activity('RECEPTIONIST_CHECKIN', f"Guest checked into Room for Booking {b['booking_ref']}.")
        flash(f"Check-in processed successfully for {b['booking_ref']}!", 'success')
    return redirect(request.referrer or url_for('receptionist.checkin_checkout'))

@receptionist_bp.route('/bookings/<int:booking_id>/checkout', methods=['POST'], endpoint='process_checkout')
@receptionist_required
def process_checkout(booking_id):
    b = query('SELECT booking_ref, room_id FROM bookings WHERE id = %s', (booking_id,), one=True)
    if b:
        execute("UPDATE bookings SET status = 'checked_out' WHERE id = %s", (booking_id,))
        if b['room_id']:
            execute("UPDATE rooms SET status = 'cleaning', housekeeping_status = 'dirty' WHERE id = %s", (b['room_id'],))
            execute('''
                INSERT INTO housekeeping_tasks (room_id, assigned_to, status, priority, task_type, notes)
                VALUES (%s, %s, 'pending', 'urgent', 'checkout_clean', %s)
            ''', (b['room_id'], session.get('user_id'), f"Checkout clean for {b['booking_ref']}"))
        log_activity('RECEPTIONIST_CHECKOUT', f"Guest checked out for Booking {b['booking_ref']}. Room flagged for cleaning.")
        flash(f"Check-out completed for {b['booking_ref']}. Room dispatched to housekeeping.", 'success')
    return redirect(request.referrer or url_for('receptionist.checkin_checkout'))


# ─── 7. PAYMENT PROCESSING & INVOICES ─────────────────────────────────────────

@receptionist_bp.route('/payments', endpoint='payments')
@receptionist_required
def payments():
    invoices = query('''
        SELECT inv.*, b.booking_ref, g.full_name AS guest_name, g.phone AS guest_phone,
               (inv.total - inv.paid_amount) AS balance_due
        FROM invoices inv
        JOIN bookings b ON inv.booking_id = b.id
        JOIN guests g ON b.guest_id = g.id
        ORDER BY inv.issued_at DESC
    ''')
    return render_template('receptionist/payments.html', invoices=invoices)

@receptionist_bp.route('/payments/record', methods=['POST'], endpoint='record_payment')
@receptionist_required
def record_payment():
    invoice_id = request.form.get('invoice_id', type=int)
    amount = request.form.get('amount', type=float)
    method = request.form.get('method', 'cash')
    reference = request.form.get('reference', '').strip()

    inv = query('SELECT * FROM invoices WHERE id = %s', (invoice_id,), one=True)
    if not inv or not amount or amount <= 0:
        flash('Invalid invoice or payment amount.', 'danger')
        return redirect(url_for('receptionist.payments'))

    user_id = session.get('user_id')
    ref = reference or f"REC-{random.randint(100000, 999999)}"

    execute('''
        INSERT INTO payments (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
        VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Front desk collection')
    ''', (invoice_id, inv['booking_id'], amount, method, ref, user_id))

    new_paid = float(inv['paid_amount']) + amount
    new_status = 'paid' if new_paid >= float(inv['total']) else 'partial'
    execute('UPDATE invoices SET paid_amount = %s, status = %s WHERE id = %s', (new_paid, new_status, invoice_id))
    execute('UPDATE bookings SET paid_amount = paid_amount + %s WHERE id = %s', (amount, inv['booking_id']))

    log_activity('RECEPTIONIST_PAYMENT', f"Recorded payment of ₹{amount:,.2f} via {method.upper()} for Invoice {inv['invoice_number']}.")
    flash(f"Payment of ₹{amount:,.2f} recorded successfully!", 'success')
    return redirect(url_for('receptionist.payments'))


# ─── 8. BOOKING RECEIPT & CONFIRMATION DOCUMENT ───────────────────────────────

@receptionist_bp.route('/bookings/<int:booking_id>/receipt', endpoint='booking_receipt')
@receptionist_required
def booking_receipt(booking_id):
    booking = query('''
        SELECT b.*, g.full_name AS guest_name, g.email AS guest_email, g.phone AS guest_phone,
               g.address AS guest_address, g.id_type, g.id_number,
               r.room_number, r.floor, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.id = %s
    ''', (booking_id,), one=True)

    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('receptionist.bookings'))

    invoice = query('SELECT * FROM invoices WHERE booking_id = %s', (booking_id,), one=True)
    items = query('SELECT * FROM invoice_items WHERE invoice_id = %s', (invoice['id'],)) if invoice else []
    payments = query('SELECT * FROM payments WHERE booking_id = %s ORDER BY payment_date DESC', (booking_id,))

    return render_template('receptionist/receipt.html',
                           booking=booking,
                           invoice=invoice,
                           items=items,
                           payments=payments)


# ─── 9. BOOKING HISTORY ARCHIVE ───────────────────────────────────────────────

@receptionist_bp.route('/history', endpoint='history')
@receptionist_required
def history():
    past_bookings = query('''
        SELECT b.*, g.full_name AS guest_name, g.phone AS guest_phone,
               r.room_number, rt.name AS room_type_name
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.status IN ('checked_out', 'cancelled', 'no_show')
        ORDER BY b.check_out_date DESC LIMIT 100
    ''')
    return render_template('receptionist/history.html', bookings=past_bookings)


# ─── 10. DAILY BOOKING REPORT ─────────────────────────────────────────────────

@receptionist_bp.route('/reports', endpoint='reports')
@receptionist_required
def reports():
    today = datetime.date.today()
    daily_stats = {
        'date': today.isoformat(),
        'arrivals': query('SELECT COUNT(*) AS c FROM bookings WHERE check_in_date = %s', (today,), one=True)['c'],
        'departures': query("SELECT COUNT(*) AS c FROM bookings WHERE check_out_date = %s AND status = 'checked_out'", (today,), one=True)['c'],
        'revenue_collected': float(query('SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE payment_date = %s', (today,), one=True)['s']),
        'occupied_rooms': query("SELECT COUNT(*) AS c FROM rooms WHERE status = 'occupied'", one=True)['c'],
        'available_rooms': query("SELECT COUNT(*) AS c FROM rooms WHERE status = 'available'", one=True)['c'],
    }
    today_payments = query('''
        SELECT p.*, b.booking_ref, g.full_name AS guest_name
        FROM payments p
        JOIN bookings b ON p.booking_id = b.id
        JOIN guests g ON b.guest_id = g.id
        WHERE p.payment_date = %s
    ''', (today,))

    return render_template('receptionist/reports.html', stats=daily_stats, payments=today_payments)

