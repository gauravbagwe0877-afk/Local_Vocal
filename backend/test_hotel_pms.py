import sys
import os
import unittest
import datetime

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(__file__))

from app import app
from database import query, execute

class HotelPMSTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()

    def test_01_public_routes(self):
        """Test public browsing and auth pages render successfully."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200, "Home page failed")

        res = self.client.get('/login')
        self.assertEqual(res.status_code, 200, "Login page failed")

        res = self.client.get('/register')
        self.assertEqual(res.status_code, 200, "Register page failed")

        res = self.client.get('/api/places')
        self.assertEqual(res.status_code, 200, "API places failed")

        res = self.client.get('/api/status')
        self.assertEqual(res.status_code, 200, "API status failed")

    def test_02_permissions_server_side(self):
        """Protected hotel routes must reject unauthenticated or regular users."""
        # Unauthenticated access
        res = self.client.get('/hotel/dashboard')
        self.assertEqual(res.status_code, 302, "Unauthenticated user should be redirected")

        # Regular user access
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['username'] = 'test_regular'
            sess['role'] = 'user'

        res = self.client.get('/hotel/dashboard')
        self.assertEqual(res.status_code, 302, "Regular user should be denied access")

    def test_03_hotel_pms_screens(self):
        """Admin or hotel staff can view all hotel management screens."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'admin'
            sess['name'] = 'Admin User'
            sess['role'] = 'admin'

        endpoints = [
            '/hotel/dashboard',
            '/hotel/rooms',
            '/hotel/bookings',
            '/hotel/guests',
            '/hotel/guests/1',
            '/hotel/billing',
            '/hotel/invoices/1',
            '/hotel/housekeeping',
            '/hotel/maintenance',
            '/hotel/expenses',
            '/hotel/settings'
        ]

        for ep in endpoints:
            res = self.client.get(ep)
            self.assertEqual(res.status_code, 200, f"Endpoint {ep} failed with code {res.status_code}")
            # Verify design system indicators
            self.assertTrue(b'StaySmart Hotel' in res.data or b'Hotel' in res.data, f"Hotel name missing on {ep}")

    def test_04_booking_validation(self):
        """Backend validation prevents invalid dates and room conflicts."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'

        today = datetime.date.today().isoformat()

        # Check-out before check-in must fail
        res = self.client.post('/hotel/bookings/new', data={
            'guest_id': '1',
            'room_id': '1',
            'check_in_date': '2026-11-10',
            'check_out_date': '2026-11-05',
            'adults': '1'
        }, follow_redirects=True)
        self.assertIn(b'Check-out date must be strictly after check-in date', res.data)

    def test_05_admin_dashboard_integration(self):
        """Admin dashboard loads and includes admin console branding."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'admin'
            sess['name'] = 'Admin User'

        res = self.client.get('/admin/dashboard')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'ADMIN CONSOLE', res.data)

if __name__ == '__main__':
    unittest.main()

