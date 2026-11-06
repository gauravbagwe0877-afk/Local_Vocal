from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database import query, execute
from auth_decorators import customer_required, log_activity
import datetime
import random
import string
import json

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

def get_hotel_settings():
    rows = query('SELECT setting_key, setting_val FROM hotel_settings')
    settings = {r['setting_key']: r['setting_val'] for r in rows}
    settings.setdefault('hotel_name', 'StaySmart Hotel & Suites')
    settings.setdefault('currency_symbol', '₹')
    settings.setdefault('gst_rate', '12')
    return settings

def get_current_guest():
    """Fetch the guest record corresponding to logged-in user."""
    uid = session.get('user_id')
    if not uid:
        return None
    guest = query('SELECT * FROM guests WHERE user_id = %s', (uid,), one=True)
    if not guest:
        user = query('SELECT * FROM users WHERE id = %s', (uid,), one=True)
        if user:
            gid = execute('''
                INSERT INTO guests (user_id, full_name, email, phone, total_stays)
                VALUES (%s, %s, %s, %s, 0)
            ''', (uid, user['name'], user['email'], user.get('phone', '')))
            guest = query('SELECT * FROM guests WHERE id = %s', (gid,), one=True)
    return guest

@customer_bp.context_processor
def inject_customer_globals():
    return {
        'hotel_settings': get_hotel_settings(),
        'today_date': datetime.date.today().isoformat(),
        'tomorrow_date': (datetime.date.today() + datetime.timedelta(days=1)).isoformat(),
        'current_guest': get_current_guest()
    }


# ─── 1. CUSTOMER DASHBOARD ────────────────────────────────────────────────────

@customer_bp.route('/', endpoint='index')
@customer_bp.route('/dashboard', endpoint='dashboard')
@customer_required
def dashboard():
    guest = get_current_guest()
    if not guest:
        flash('Guest profile could not be loaded.', 'danger')
        return redirect(url_for('main.index'))

    # Active/Upcoming bookings for this customer
    active_bookings = query('''
        SELECT b.*, r.room_number, rt.name AS room_type_name, rt.image_url
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.guest_id = %s AND b.status IN ('confirmed', 'checked_in')
        ORDER BY b.check_in_date ASC
    ''', (guest['id'],))

    # Past bookings
    past_bookings = query('''
        SELECT b.*, r.room_number, rt.name AS room_type_name
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.guest_id = %s AND b.status IN ('checked_out', 'cancelled')
        ORDER BY b.check_in_date DESC LIMIT 5
    ''', (guest['id'],))

    # Hotel Services & Facilities
    services = query('SELECT * FROM hotel_services WHERE is_active = 1 LIMIT 4')

    return render_template('customer/dashboard.html',
                           guest=guest,
                           active_bookings=active_bookings,
                           past_bookings=past_bookings,
                           services=services)


# ─── 2. REAL-TIME ROOM AVAILABILITY & SEARCH ──────────────────────────────────

@customer_bp.route('/rooms', endpoint='rooms')
@customer_bp.route('/search', endpoint='search_rooms')
def search_rooms():
    today = datetime.date.today()
    check_in_str = request.args.get('check_in', today.isoformat())
    check_out_str = request.args.get('check_out', (today + datetime.timedelta(days=1)).isoformat())
    guests_count = request.args.get('guests', default=1, type=int)
    category_id = request.args.get('category_id', default='', type=str)

    # Validate dates
    try:
        check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
        if check_out <= check_in:
            check_out = check_in + datetime.timedelta(days=1)
    except (ValueError, TypeError):
        check_in = today
        check_out = today + datetime.timedelta(days=1)

    nights = max((check_out - check_in).days, 1)

    # Real-time room availability query
    sql = '''
        SELECT rt.*, COUNT(r.id) AS available_rooms_count
        FROM room_types rt
        JOIN rooms r ON r.room_type_id = rt.id
        WHERE rt.is_active = 1
          AND r.status NOT IN ('maintenance')
          AND r.id NOT IN (
              SELECT room_id FROM bookings
              WHERE room_id IS NOT NULL
                AND status IN ('confirmed', 'checked_in')
                AND NOT (check_out_date <= %s OR check_in_date >= %s)
          )
    '''
    params = [check_in, check_out]

    if guests_count and guests_count > 1:
        sql += ' AND (rt.max_adults + rt.max_children) >= %s'
        params.append(guests_count)

    if category_id:
        sql += ' AND rt.id = %s'
        params.append(category_id)

    sql += ' GROUP BY rt.id ORDER BY rt.base_rate ASC'
    available_room_types = query(sql, tuple(params))

    # Parse amenities
    for rt in available_room_types:
        if isinstance(rt.get('amenities'), str):
            try:
                rt['amenities_list'] = json.loads(rt['amenities'])
            except Exception:
                rt['amenities_list'] = [a.strip() for a in rt['amenities'].split(',') if a.strip()]
        else:
            rt['amenities_list'] = rt.get('amenities') or []

        # Cost breakdown for selected nights
        rate = float(rt['base_rate'])
        subtotal = rate * nights
        gst_rate = float(get_hotel_settings().get('gst_rate', 12))
        tax = round(subtotal * (gst_rate / 100.0), 2)
        rt['calc_nights'] = nights
        rt['calc_subtotal'] = subtotal
        rt['calc_tax'] = tax
        rt['calc_total'] = subtotal + tax

    all_categories = query('SELECT id, name FROM room_types WHERE is_active = 1 ORDER BY name ASC')

    return render_template('customer/rooms.html',
                           room_types=available_room_types,
                           categories=all_categories,
                           check_in=check_in.isoformat(),
                           check_out=check_out.isoformat(),
                           guests_count=guests_count,
                           selected_category=category_id,
                           nights=nights)


# ─── 3. BOOKING WORKFLOW & COST BREAKDOWN ─────────────────────────────────────

@customer_bp.route('/book/<int:room_type_id>', endpoint='book_room')
@customer_required
def book_room(room_type_id):
    today = datetime.date.today()
    check_in_str = request.args.get('check_in', today.isoformat())
    check_out_str = request.args.get('check_out', (today + datetime.timedelta(days=1)).isoformat())
    adults = request.args.get('adults', default=1, type=int)
    children = request.args.get('children', default=0, type=int)

    try:
        check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
        if check_out <= check_in:
            check_out = check_in + datetime.timedelta(days=1)
    except Exception:
        check_in = today
        check_out = today + datetime.timedelta(days=1)

    nights = max((check_out - check_in).days, 1)

    room_type = query('SELECT * FROM room_types WHERE id = %s AND is_active = 1', (room_type_id,), one=True)
    if not room_type:
        flash('Selected room category is not available.', 'danger')
        return redirect(url_for('customer.rooms'))

    if isinstance(room_type.get('amenities'), str):
        try:
            room_type['amenities_list'] = json.loads(room_type['amenities'])
        except Exception:
            room_type['amenities_list'] = [a.strip() for a in room_type['amenities'].split(',') if a.strip()]
    else:
        room_type['amenities_list'] = room_type.get('amenities') or []

    # Financial cost breakdown
    rate = float(room_type['base_rate'])
    subtotal = rate * nights
    gst_rate = float(get_hotel_settings().get('gst_rate', 12))
    tax_amount = round(subtotal * (gst_rate / 100.0), 2)
    grand_total = subtotal + tax_amount

    breakdown = {
        'nights': nights,
        'rate_per_night': rate,
        'subtotal': subtotal,
        'gst_rate': gst_rate,
        'tax_amount': tax_amount,
        'grand_total': grand_total
    }

    guest = get_current_guest()

    return render_template('customer/book_step.html',
                           room_type=room_type,
                           breakdown=breakdown,
                           check_in=check_in.isoformat(),
                           check_out=check_out.isoformat(),
                           adults=adults,
                           children=children,
                           guest=guest)


# ─── 4. PROCESS ONLINE BOOKING & DOUBLE-BOOKING PREVENTION ────────────────────

@customer_bp.route('/book/process', methods=['POST'], endpoint='process_booking')
@customer_required
def process_booking():
    room_type_id = request.form.get('room_type_id', type=int)
    check_in_str = request.form.get('check_in_date', '').strip()
    check_out_str = request.form.get('check_out_date', '').strip()
    adults = request.form.get('adults', default=1, type=int)
    children = request.form.get('children', default=0, type=int)
    payment_method = request.form.get('payment_method', 'card')
    special_requests = request.form.get('special_requests', '').strip()

    guest = get_current_guest()
    if not guest:
        flash('Customer profile not found. Please log in again.', 'danger')
        return redirect(url_for('auth.customer_login'))

    try:
        check_in = datetime.datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.datetime.strptime(check_out_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        flash('Invalid reservation dates.', 'danger')
        return redirect(url_for('customer.rooms'))

    if check_out <= check_in:
        flash('Check-out date must be strictly after check-in date.', 'danger')
        return redirect(url_for('customer.rooms'))

    nights = (check_out - check_in).days

    room_type = query('SELECT * FROM room_types WHERE id = %s', (room_type_id,), one=True)
    if not room_type:
        flash('Room type not found.', 'danger')
        return redirect(url_for('customer.rooms'))

    # Double Booking Prevention: Find an available room of this category that has NO overlapping active bookings
    available_room = query('''
        SELECT r.id, r.room_number
        FROM rooms r
        WHERE r.room_type_id = %s
          AND r.status NOT IN ('maintenance')
          AND r.id NOT IN (
              SELECT room_id FROM bookings
              WHERE room_id IS NOT NULL
                AND status IN ('confirmed', 'checked_in')
                AND NOT (check_out_date <= %s OR check_in_date >= %s)
          )
        ORDER BY r.room_number ASC
        LIMIT 1
    ''', (room_type_id, check_in, check_out), one=True)

    if not available_room:
        flash(f"Sorry, all rooms in '{room_type['name']}' are fully booked for {check_in_str} to {check_out_str}. Please choose alternative dates.", 'danger')
        return redirect(url_for('customer.rooms'))

    room_id = available_room['id']
    room_rate = float(room_type['base_rate'])
    subtotal = room_rate * nights
    gst_rate = float(get_hotel_settings().get('gst_rate', 12))
    tax_amount = round(subtotal * (gst_rate / 100.0), 2)
    grand_total = subtotal + tax_amount

    # Unique Booking Reference
    year = datetime.date.today().year
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    booking_ref = f"BK-{year}-{suffix}"
    uid = session.get('user_id')

    # Status: confirmed
    booking_id = execute('''
        INSERT INTO bookings
        (booking_ref, guest_id, room_id, room_type_id, check_in_date, check_out_date,
         nights, adults, children, status, room_rate, total_amount, paid_amount,
         special_requests, source, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'confirmed', %s, %s, %s, %s, 'online_portal', %s)
    ''', (booking_ref, guest['id'], room_id, room_type_id, check_in, check_out,
          nights, adults, children, room_rate, grand_total, grand_total if payment_method != 'hotel' else 0.0,
          special_requests, uid))

    # Update guest total stays count
    execute('UPDATE guests SET total_stays = total_stays + 1 WHERE id = %s', (guest['id'],))

    # Invoice creation
    inv_num = f"INV-{year}-{suffix}"
    inv_status = 'paid' if payment_method != 'hotel' else 'issued'
    paid_amt = grand_total if payment_method != 'hotel' else 0.0

    invoice_id = execute('''
        INSERT INTO invoices
        (invoice_number, booking_id, subtotal, tax_amount, discount, total, paid_amount, status, notes)
        VALUES (%s, %s, %s, %s, 0.0, %s, %s, %s, 'Online customer booking')
    ''', (inv_num, booking_id, subtotal, tax_amount, grand_total, paid_amt, inv_status))

    # Line items
    execute('''
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
        VALUES (%s, %s, %s, %s, %s, 'room')
    ''', (invoice_id, f"{room_type['name']} Stay ({nights} Nights @ ₹{room_rate:,.2f})", nights, room_rate, subtotal))

    execute('''
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, amount, item_type)
        VALUES (%s, %s, 1, %s, %s, 'tax')
    ''', (invoice_id, f"GST Tax ({gst_rate}%)", tax_amount, tax_amount))

    # Payment record if paid online
    if payment_method != 'hotel':
        txn_ref = f"GATEWAY-TEST-{random.randint(1000000, 9999999)}"
        execute('''
            INSERT INTO payments (invoice_id, booking_id, amount, method, reference, recorded_by, payment_date, notes)
            VALUES (%s, %s, %s, %s, %s, %s, CURDATE(), 'Online Test Payment Gateway Confirmation')
        ''', (invoice_id, booking_id, grand_total, payment_method, txn_ref, uid))

    log_activity('CUSTOMER_ONLINE_BOOKING', f"Customer {guest['full_name']} booked {booking_ref} (Total: ₹{grand_total:,.2f}).", user_id=uid)
    flash(f"🎉 Congratulations! Your booking {booking_ref} has been confirmed.", 'success')
    return redirect(url_for('customer.confirmation', booking_ref=booking_ref))


# ─── 5. BOOKING CONFIRMATION SCREEN ───────────────────────────────────────────

@customer_bp.route('/confirmation/<string:booking_ref>', endpoint='confirmation')
@customer_required
def confirmation(booking_ref):
    guest = get_current_guest()
    booking = query('''
        SELECT b.*, r.room_number, r.floor, rt.name AS room_type_name, rt.image_url,
               g.full_name AS guest_name, g.phone AS guest_phone, g.email AS guest_email
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.booking_ref = %s AND b.guest_id = %s
    ''', (booking_ref, guest['id']), one=True)

    if not booking:
        flash('Booking confirmation record could not be found.', 'danger')
        return redirect(url_for('customer.bookings'))

    invoice = query('SELECT * FROM invoices WHERE booking_id = %s', (booking['id'],), one=True)
    return render_template('customer/confirmation.html', booking=booking, invoice=invoice)


# ─── 6. MY BOOKINGS & RESERVATION HISTORY ─────────────────────────────────────

@customer_bp.route('/bookings', endpoint='bookings')
@customer_required
def bookings():
    guest = get_current_guest()
    bookings_list = query('''
        SELECT b.*, r.room_number, rt.name AS room_type_name, rt.image_url,
               inv.invoice_number, inv.status AS invoice_status
        FROM bookings b
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        LEFT JOIN invoices inv ON inv.booking_id = b.id
        WHERE b.guest_id = %s
        ORDER BY b.check_in_date DESC
    ''', (guest['id'],))

    return render_template('customer/bookings.html', bookings=bookings_list)


# ─── 7. BOOKING DETAILS & RECEIPT VIEW ────────────────────────────────────────

@customer_bp.route('/bookings/<int:booking_id>/receipt', endpoint='booking_receipt')
@customer_required
def booking_receipt(booking_id):
    guest = get_current_guest()
    # Security check: ensures booking belongs to this customer!
    booking = query('''
        SELECT b.*, r.room_number, r.floor, rt.name AS room_type_name,
               g.full_name AS guest_name, g.email AS guest_email, g.phone AS guest_phone,
               g.address AS guest_address, g.id_type, g.id_number
        FROM bookings b
        JOIN guests g ON b.guest_id = g.id
        LEFT JOIN rooms r ON b.room_id = r.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.id = %s AND b.guest_id = %s
    ''', (booking_id, guest['id']), one=True)

    if not booking:
        flash('Unauthorized access or booking not found.', 'danger')
        return redirect(url_for('customer.bookings'))

    invoice = query('SELECT * FROM invoices WHERE booking_id = %s', (booking_id,), one=True)
    items = query('SELECT * FROM invoice_items WHERE invoice_id = %s', (invoice['id'],)) if invoice else []
    payments = query('SELECT * FROM payments WHERE booking_id = %s ORDER BY payment_date DESC', (booking_id,))

    return render_template('customer/receipt.html',
                           booking=booking,
                           invoice=invoice,
                           items=items,
                           payments=payments)


# ─── 8. CANCEL BOOKING ACCORDING TO POLICY ────────────────────────────────────

@customer_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'], endpoint='cancel_booking')
@customer_required
def cancel_booking(booking_id):
    guest = get_current_guest()
    booking = query('''
        SELECT * FROM bookings WHERE id = %s AND guest_id = %s
    ''', (booking_id, guest['id']), one=True)

    if not booking:
        flash('Unauthorized or booking not found.', 'danger')
        return redirect(url_for('customer.bookings'))

    if booking['status'] not in ('confirmed', 'pending'):
        flash(f"Bookings with status '{booking['status']}' cannot be cancelled online.", 'warning')
        return redirect(url_for('customer.bookings'))

    execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
    if booking['room_id']:
        execute("UPDATE rooms SET status = 'available' WHERE id = %s AND status = 'reserved'", (booking['room_id'],))

    log_activity('CUSTOMER_CANCEL_BOOKING', f"Customer {guest['full_name']} cancelled booking {booking['booking_ref']}.")
    flash(f"Booking {booking['booking_ref']} has been successfully cancelled.", 'info')
    return redirect(url_for('customer.bookings'))


# ─── 9. CUSTOMER PAYMENTS HISTORY ─────────────────────────────────────────────

@customer_bp.route('/payments', endpoint='payments')
@customer_required
def payments():
    guest = get_current_guest()
    payments_list = query('''
        SELECT p.*, inv.invoice_number, b.booking_ref, rt.name AS room_type_name
        FROM payments p
        JOIN invoices inv ON p.invoice_id = inv.id
        JOIN bookings b ON p.booking_id = b.id
        LEFT JOIN room_types rt ON b.room_type_id = rt.id
        WHERE b.guest_id = %s
        ORDER BY p.payment_date DESC
    ''', (guest['id'],))

    return render_template('customer/payments.html', payments=payments_list)


# ─── 10. CUSTOMER PROFILE MANAGEMENT ──────────────────────────────────────────

@customer_bp.route('/profile', methods=['GET', 'POST'], endpoint='profile')
@customer_required
def profile():
    guest = get_current_guest()
    uid = session.get('user_id')

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()
        id_type = request.form.get('id_type', 'Aadhaar')
        id_number = request.form.get('id_number', '').strip()

        if not full_name or not phone:
            flash('Full name and phone are required.', 'danger')
            return redirect(url_for('customer.profile'))

        # Update users table
        execute('UPDATE users SET name = %s, phone = %s, email = %s WHERE id = %s',
                (full_name, phone, email, uid))
        session['name'] = full_name
        session['email'] = email

        # Update guests table
        execute('''
            UPDATE guests
            SET full_name = %s, phone = %s, email = %s, address = %s, id_type = %s, id_number = %s
            WHERE id = %s
        ''', (full_name, phone, email, address, id_type, id_number, guest['id']))

        log_activity('CUSTOMER_PROFILE_UPDATE', f"Customer {full_name} updated profile details.")
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('customer.profile'))

    return render_template('customer/profile.html', guest=guest)

