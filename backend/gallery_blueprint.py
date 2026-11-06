"""
gallery_blueprint.py — Flask Blueprint for hotel inside image gallery.

Provides:
  • GET /api/place/<id>/images   → returns JSON list of images from place_images table
  • inject_gallery_assets()      → after_request hook that auto-injects gallery
                                   CSS + JS into place detail HTML responses
                                   (register on app via run.py)
"""

import re
from flask import Blueprint, jsonify, request
from database import query

images_bp = Blueprint('images', __name__)


# ── API: Get inside images for a place ───────────────────────────────────────

@images_bp.route('/api/place/<int:place_id>/images')
def place_images(place_id):
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


# ── Middleware: inject gallery assets into place detail responses ─────────────

_PLACE_RE = re.compile(r'^/place/\d+$')

def inject_gallery_assets(response):
    """
    After-request hook: only runs for /place/<id> HTML responses.
    Injects <link> for gallery.css and <script> for gallery.js without
    touching any existing template files.
    """
    # Only HTML responses on place detail pages
    if not response.content_type.startswith('text/html'):
        return response
    if not _PLACE_RE.match(request.path):
        return response

    html = response.get_data(as_text=True)

    css_tag = '    <link rel="stylesheet" href="/static/css/gallery.css">\n'
    js_tag  = '    <script src="/static/js/gallery.js"></script>\n'

    # Inject CSS just before </head>
    if '</head>' in html:
        html = html.replace('</head>', css_tag + '</head>', 1)

    # Inject JS just before </body>
    if '</body>' in html:
        html = html.replace('</body>', js_tag + '</body>', 1)

    response.set_data(html)
    return response
