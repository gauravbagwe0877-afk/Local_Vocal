"""
run.py — Local Vocal entry point with hotel gallery support.

Usage:
    cd backend
    python run.py

Adds (without modifying any existing file):
  • GET /api/place/<id>/images  — returns inside images from place_images table
  • after_request hook          — injects gallery.css + gallery.js into
                                  /place/<id> HTML responses automatically
"""

import sys
import os
import re

# Ensure backend directory is in path whether executed from root or backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from database import query
from flask import jsonify, request

# ── New route: hotel inside images API ───────────────────────────────────────

if 'place_images_gallery' not in app.view_functions and 'main.place_images_gallery' not in app.view_functions:
    @app.route('/api/place/<int:place_id>/images')
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


# ── After-request: inject gallery CSS + JS on place detail pages ──────────────

_PLACE_PATH = re.compile(r'^/place/\d+$')


@app.after_request
def inject_gallery_assets(response):
    """
    Inject gallery.css and gallery.js into /place/<id> HTML responses
    without touching any existing template file.
    """
    if not response.content_type.startswith('text/html'):
        return response
    if not _PLACE_PATH.match(request.path):
        return response

    html = response.get_data(as_text=True)

    css_tag = '    <link rel="stylesheet" href="/static/css/gallery.css">\n'
    js_tag  = '    <script src="/static/js/gallery.js"></script>\n'

    if '</head>' in html:
        html = html.replace('</head>', css_tag + '</head>', 1)
    if '</body>' in html:
        html = html.replace('</body>', js_tag + '</body>', 1)

    response.set_data(html)
    return response


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(debug=True, port=5000)

