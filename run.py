"""
StaySmart – Hotel Management System
Root Launcher

Usage:
    python run.py
"""
import sys
import os

# Ensure backend folder is in Python module path
BACKEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Import the configured Flask app from backend/run.py
from run import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"============================================================")
    print(f"  STAYSMART - HOTEL MANAGEMENT SYSTEM")
    print(f"  Running on: http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host='0.0.0.0', port=port, debug=True)

