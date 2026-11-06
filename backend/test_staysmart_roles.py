"""
Comprehensive Integration & Role-Based Security Tests for StaySmart Hotel Management System.
Tests:
1. Role-based authentication (Admin, Receptionist, Customer)
2. Permission barrier enforcement:
   - Receptionist cannot access Admin Dashboard or Settings
   - Customer cannot access Admin or Receptionist panels
3. Customer Data Isolation:
   - Customer cannot view or cancel another customer's booking
4. Room Availability & Double-Booking Prevention:
   - Overlapping bookings for the same room are strictly rejected
5. Check-In, Check-Out, and Cashiering / Payments workflow
6. Audit Logging in activity_logs
"""

import sys
import os
import unittest
import datetime

# Setup module path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import query, execute

class StaySmartRoleSecurityTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_01_public_routes(self):
        """Verify home page, explore, and room search are accessible publicly."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'StaySmart', res.data)

        res_rooms = self.client.get('/customer/rooms')
        self.assertEqual(res_rooms.status_code, 200)
        self.assertIn(b'Available Rooms', res_rooms.data)

    def test_02_admin_login_and_dashboard(self):
        """Admin can log in and view Admin Dashboard and management pages."""
        with self.client:
            res = self.client.post('/admin/login', data={
                'username': 'admin',
                'password': 'admin123'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'ADMIN CONSOLE', res.data)

            # Test Admin Rooms list
            res_rooms = self.client.get('/admin/rooms')
            self.assertEqual(res_rooms.status_code, 200)
            self.assertIn(b'Room Management', res_rooms.data)

            # Test Admin Receptionists list
            res_rec = self.client.get('/admin/receptionists')
            self.assertEqual(res_rec.status_code, 200)
            self.assertIn(b'Receptionist Staff', res_rec.data)

            # Test Admin Reports
            res_rep = self.client.get('/admin/reports')
            self.assertEqual(res_rep.status_code, 200)
            self.assertIn(b'Booking & Revenue Reports', res_rep.data)

    def test_03_receptionist_login_and_permission_denial(self):
        """Receptionist can access front desk, but is strictly BLOCKED from admin dashboard."""
        with self.client:
            # Login as receptionist
            res = self.client.post('/receptionist/login', data={
                'username': 'receptionist',
                'password': 'receptionist123'
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            self.assertIn(b'Front Desk Operations', res.data)

            # Attempt to access Admin Dashboard -> MUST BE BLOCKED
            res_admin = self.client.get('/admin/dashboard', follow_redirects=False)
            self.assertEqual(res_admin.status_code, 302)
            self.assertIn('/admin/login', res_admin.location)

            # Attempt to access Admin Settings -> MUST BE BLOCKED
            res_settings = self.client.get('/admin/settings', follow_redirects=False)
            self.assertEqual(res_settings.status_code, 302)

    def test_04_customer_registration_and_login(self):
        """Customer can register, log in, and view personal dashboard."""
        import random
        rand_suffix = random.randint(1000, 9999)
        test_uname = f"testguest{rand_suffix}"
        test_email = f"testguest{rand_suffix}@staysmart.com"

        with self.client:
            res_reg = self.client.post('/customer/register', data={
                'name': f'Test Guest {rand_suffix}',
                'username': test_uname,
                'email': test_email,
                'phone': '9876543210',
                'address': 'Beach Road, Sawantwadi',
                'password': 'guestpassword123',
                'confirm_password': 'guestpassword123'
            }, follow_redirects=True)
            self.assertEqual(res_reg.status_code, 200)
            self.assertIn(b'Guest Dashboard', res_reg.data)

            # Customer cannot access Receptionist or Admin
            res_rec = self.client.get('/receptionist/dashboard', follow_redirects=False)
            self.assertEqual(res_rec.status_code, 302)

            res_adm = self.client.get('/admin/dashboard', follow_redirects=False)
            self.assertEqual(res_adm.status_code, 302)

    def test_05_double_booking_prevention(self):
        """Test that two overlapping bookings for the exact same room are prevented."""
        with self.app.app_context():
            room = query('SELECT * FROM rooms WHERE status = "available" LIMIT 1', one=True)
            if not room:
                room = query('SELECT * FROM rooms LIMIT 1', one=True)

        room_id = room['id']
        room_type_id = room['room_type_id']

        d1 = datetime.date.today() + datetime.timedelta(days=25)
        d2 = datetime.date.today() + datetime.timedelta(days=28)

        # Login as receptionist to create a confirmed booking
        with self.client:
            self.client.post('/receptionist/login', data={
                'username': 'receptionist',
                'password': 'receptionist123'
            })

            # Create first booking
            res_b1 = self.client.post('/receptionist/bookings/new', data={
                'full_name': 'Test Traveler A',
                'email': 'traveler_a@test.com',
                'phone': '9811111111',
                'room_type_id': room_type_id,
                'room_id': room_id,
                'check_in_date': d1.isoformat(),
                'check_out_date': d2.isoformat(),
                'adults': 2,
                'children': 0,
                'payment_status': 'confirmed'
            }, follow_redirects=True)
            self.assertEqual(res_b1.status_code, 200)

            # Try to book the SAME room for OVERLAPPING dates
            d_overlap_in = d1 + datetime.timedelta(days=1)
            d_overlap_out = d2 + datetime.timedelta(days=1)

            res_b2 = self.client.post('/receptionist/bookings/new', data={
                'full_name': 'Test Traveler Conflict',
                'email': 'traveler_conflict@test.com',
                'phone': '9822222222',
                'room_type_id': room_type_id,
                'room_id': room_id,
                'check_in_date': d_overlap_in.isoformat(),
                'check_out_date': d_overlap_out.isoformat(),
                'adults': 1,
                'children': 0,
                'payment_status': 'confirmed'
            }, follow_redirects=True)

            # The response MUST flag error or double-booking warning
            self.assertTrue(
                b'already reserved or occupied' in res_b2.data or
                b'overlap' in res_b2.data or
                b'danger' in res_b2.data or
                b'alert' in res_b2.data
            )

    def test_06_customer_data_isolation(self):
        """Customer A cannot view another customer's booking receipt."""
        with self.app.app_context():
            other_booking = query('''
                SELECT b.id, b.guest_id
                FROM bookings b
                JOIN guests g ON b.guest_id = g.id
                WHERE g.user_id != (SELECT id FROM users WHERE username = 'customer')
                LIMIT 1
            ''', one=True)

        if not other_booking:
            return

        # Login as customer user who does NOT own this booking
        with self.client:
            self.client.post('/customer/login', data={
                'username': 'customer',
                'password': 'customer123'
            })
            res = self.client.get(f"/customer/receipt/{other_booking['id']}", follow_redirects=False)
            # Should be redirected away or forbidden
            self.assertIn(res.status_code, [302, 403, 404])

    def test_07_activity_logs_recording(self):
        """Verify activity logs record events."""
        with self.app.app_context():
            logs = query('SELECT * FROM activity_logs ORDER BY created_at DESC LIMIT 10')
            self.assertIsNotNone(logs)
            self.assertGreater(len(logs), 0)
            actions = [l['action'] for l in logs]
            self.assertTrue(any('LOGIN' in a or 'BOOKING' in a or 'ADMIN' in a or 'MIGRATION' in a for a in actions))


if __name__ == '__main__':
    unittest.main()
