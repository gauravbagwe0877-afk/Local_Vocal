from flask import Flask, session, g, request
import os
import pathlib
from dotenv import load_dotenv

# Database teardown registration
from database import init_app, close_db

# Load environment
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Paths
BASE_DIR     = pathlib.Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / 'frontend'

def create_app():
    app = Flask(
        __name__,
        template_folder=str(FRONTEND_DIR / 'templates'),
        static_folder=str(FRONTEND_DIR / 'static')
    )
    app.secret_key = os.environ.get('SECRET_KEY', 'staysmart-hotel-super-secret-2024')

    # Register DB context teardown
    init_app(app)

    # ── REGISTER BLUEPRINTS ───────────────────────────────────────────────────
    from blueprints.auth import auth_bp
    from blueprints.main import main_bp
    from blueprints.admin import admin_bp
    from blueprints.receptionist import receptionist_bp
    from blueprints.customer import customer_bp
    from blueprints.hotel import hotel_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(receptionist_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(hotel_bp)

    # ── URL_FOR BACKWARD COMPATIBILITY HELPER ─────────────────────────────────
    import flask
    orig_url_for = flask.url_for

    def smart_url_for(endpoint, **values):
        try:
            return orig_url_for(endpoint, **values)
        except Exception:
            for prefix in ('main.', 'auth.', 'admin.', 'receptionist.', 'customer.', 'hotel.'):
                try:
                    return orig_url_for(prefix + endpoint, **values)
                except Exception:
                    continue
            return orig_url_for(endpoint, **values)

    app.jinja_env.globals['url_for'] = smart_url_for

    # Register endpoint aliases in view_functions for Python-level redirects
    legacy_endpoint_map = {
        'index': 'main.index',
        'place_detail': 'main.place_detail',
        'submit_review': 'main.submit_review',
        'edit_review': 'main.edit_review',
        'delete_review': 'main.delete_review',
        'api_places': 'main.api_places',
        'api_status': 'main.api_status',
        'place_images_gallery': 'main.place_images_gallery',
        'login': 'auth.login',
        'register': 'auth.register',
        'logout': 'auth.logout',
        'admin_login': 'auth.admin_login',
        'receptionist_login': 'auth.receptionist_login',
        'customer_login': 'auth.customer_login',
        'admin_dashboard': 'admin.dashboard',
        'receptionist_dashboard': 'receptionist.dashboard',
        'customer_dashboard': 'customer.dashboard',
        'admin_places': 'main.index',
    }

    with app.app_context():
        rules_to_add = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint in legacy_endpoint_map.values():
                short_names = [k for k, v in legacy_endpoint_map.items() if v == rule.endpoint]
                for short_name in short_names:
                    if short_name != rule.endpoint:
                        rules_to_add.append((rule, short_name))

        for orig_rule, short_name in rules_to_add:
            if short_name not in app.view_functions and orig_rule.endpoint in app.view_functions:
                view_func = app.view_functions[orig_rule.endpoint]
                app.add_url_rule(
                    orig_rule.rule,
                    endpoint=short_name,
                    view_func=view_func,
                    methods=orig_rule.methods
                )

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
