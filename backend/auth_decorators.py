from functools import wraps
from flask import session, flash, redirect, url_for, request
from database import execute

def log_activity(action, details=None, user_id=None):
    """Helper to record system and receptionist/admin activities."""
    try:
        uid = user_id or session.get('user_id')
        ip = request.remote_addr or '127.0.0.1'
        execute(
            """INSERT INTO activity_logs (user_id, action, details, ip_address)
               VALUES (%s, %s, %s, %s)""",
            (uid, action, details or '', ip)
        )
    except Exception as e:
        print(f"[LOG_ACTIVITY_ERROR] {e}")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to continue.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Admin only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in as Administrator.', 'warning')
            return redirect(url_for('auth.admin_login', next=request.url))
        if session.get('role') != 'admin':
            flash('Access denied: Administrator privileges required.', 'danger')
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated

def receptionist_required(f):
    """Receptionist or Admin (Admin has master privileges)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in with your staff / receptionist account.', 'warning')
            return redirect(url_for('auth.receptionist_login', next=request.url))
        role = session.get('role')
        if role not in ('receptionist', 'admin'):
            flash('Access restricted to front desk and hotel operations staff.', 'danger')
            return redirect(url_for('auth.receptionist_login'))
        return f(*args, **kwargs)
    return decorated

def customer_required(f):
    """Customer only (regular logged-in guest)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to your customer account to continue.', 'warning')
            return redirect(url_for('auth.customer_login', next=request.url))
        # Admin or receptionist can also browse or book if needed, but customers definitely have access
        return f(*args, **kwargs)
    return decorated

def hotel_staff_required(f):
    """Legacy helper: allows admin or receptionist."""
    return receptionist_required(f)
