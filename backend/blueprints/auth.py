from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database import query, execute
from auth_decorators import log_activity
import bcrypt

auth_bp = Blueprint('auth', __name__)

def handle_login(expected_role=None, redirect_override=None, template_name='login.html'):
    """Shared login handler with role checking, deactivation check, and activity logging."""
    if 'user_id' in session:
        user_role = session.get('role')
        if user_role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif user_role == 'receptionist':
            return redirect(url_for('receptionist.dashboard'))
        else:
            return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password   = request.form.get('password', '')

        if not identifier or not password:
            flash('Both username/email and password are required.', 'danger')
            return render_template(template_name, role=expected_role)

        user = query(
            'SELECT * FROM users WHERE username=%s OR email=%s',
            (identifier, identifier), one=True
        )

        if user and bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            # Check if account is active
            if user.get('is_active') == 0:
                flash('Your account has been deactivated. Please contact the Hotel Administrator.', 'danger')
                return render_template(template_name, role=expected_role)

            # Check role restriction if dedicated portal
            if expected_role and user['role'] != expected_role and not (expected_role == 'receptionist' and user['role'] == 'admin'):
                flash(f'Unauthorized for this portal. This portal is for {expected_role.title()}s only.', 'danger')
                return render_template(template_name, role=expected_role)

            # Successful login
            session['user_id']  = user['id']
            session['username'] = user['username']
            session['name']     = user['name']
            session['role']     = user['role']
            session['email']    = user['email']

            # Ensure customer is linked to guests table
            if user['role'] in ('customer', 'user'):
                guest = query('SELECT id FROM guests WHERE user_id = %s', (user['id'],), one=True)
                if not guest:
                    execute("""
                        INSERT INTO guests (user_id, full_name, email, phone, total_stays)
                        VALUES (%s, %s, %s, %s, 0)
                    """, (user['id'], user['name'], user['email'], user.get('phone', '')))

            log_activity('USER_LOGIN', f"{user['role'].title()} {user['name']} ({user['username']}) logged in.")
            flash(f'Welcome back, {user["name"]}!', 'success')

            next_url = request.args.get('next')
            if next_url:
                return redirect(next_url)

            # Role-based redirection
            if user['role'] == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user['role'] == 'receptionist':
                return redirect(url_for('receptionist.dashboard'))
            else:
                return redirect(url_for('customer.dashboard'))

        flash('Invalid username or password.', 'danger')

    return render_template(template_name, role=expected_role)


# ─── GENERAL AUTH ROUTES ──────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'], endpoint='login')
def general_login():
    return handle_login(template_name='auth/login.html')

@auth_bp.route('/logout', endpoint='logout')
def logout():
    uname = session.get('username')
    urole = session.get('role')
    if uname:
        log_activity('USER_LOGOUT', f"{urole} {uname} logged out.")
    session.clear()
    flash('You have been logged out safely.', 'info')
    return redirect(url_for('auth.login'))


# ─── A. ADMIN AUTHENTICATION ──────────────────────────────────────────────────

@auth_bp.route('/admin/login', methods=['GET', 'POST'], endpoint='admin_login')
def admin_login():
    return handle_login(expected_role='admin', template_name='auth/admin_login.html')

@auth_bp.route('/admin/logout', endpoint='admin_logout')
def admin_logout():
    return logout()


# ─── B. RECEPTIONIST AUTHENTICATION ───────────────────────────────────────────

@auth_bp.route('/receptionist/login', methods=['GET', 'POST'], endpoint='receptionist_login')
def receptionist_login():
    return handle_login(expected_role='receptionist', template_name='auth/receptionist_login.html')

@auth_bp.route('/receptionist/logout', endpoint='receptionist_logout')
def receptionist_logout():
    return logout()


# ─── C. CUSTOMER AUTHENTICATION & REGISTRATION ────────────────────────────────

@auth_bp.route('/customer/login', methods=['GET', 'POST'], endpoint='customer_login')
def customer_login():
    return handle_login(expected_role='customer', template_name='auth/customer_login.html')

@auth_bp.route('/register', methods=['GET', 'POST'], endpoint='register')
@auth_bp.route('/customer/register', methods=['GET', 'POST'], endpoint='customer_register')
def customer_register():
    if 'user_id' in session:
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip()
        phone    = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm  = request.form.get('confirm_password', '')

        errors = []
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters.')
        if not name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not phone or len(phone) < 10:
            errors.append('A valid 10-digit phone number is required.')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm:
            errors.append('Passwords do not match.')

        if not errors:
            existing = query(
                'SELECT id FROM users WHERE username=%s OR email=%s',
                (username, email), one=True
            )
            if existing:
                errors.append('Username or email is already registered.')
            else:
                pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                new_user_id = execute(
                    """INSERT INTO users (username, name, email, phone, password_hash, role, is_active)
                       VALUES (%s, %s, %s, %s, %s, 'customer', 1)""",
                    (username, name, email, phone, pw_hash)
                )

                # Link into guests table for hotel reservations
                execute(
                    """INSERT INTO guests (user_id, full_name, email, phone, total_stays)
                       VALUES (%s, %s, %s, %s, 0)""",
                    (new_user_id, name, email, phone)
                )

                log_activity('CUSTOMER_REGISTRATION', f"New customer account created: {name} ({username})", user_id=new_user_id)
                flash('Registration successful! Please login with your new account credentials.', 'success')
                return redirect(url_for('auth.customer_login'))

        for err in errors:
            flash(err, 'danger')

    return render_template('auth/customer_register.html')
