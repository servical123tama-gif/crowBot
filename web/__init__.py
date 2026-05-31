"""Flask Dashboard — App Factory"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
load_dotenv()


# Limiter di-instantiate di module-level supaya bisa diimpor di route untuk decorator
# (storage default = in-memory; OK untuk single-process Flask dev server)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],                     # no global limit; per-route via @limiter.limit
    storage_uri="memory://",
    strategy="fixed-window",
)


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    # Cloudflare Tunnel forward request → localhost. Tanpa ProxyFix,
    # request.remote_addr selalu 127.0.0.1 dan rate limit jadi global, bukan per-IP.
    # x_for=1: trust 1 hop X-Forwarded-For (= cloudflared)
    # x_proto=1: trust X-Forwarded-Proto (untuk url_for scheme https)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    secret_key = os.getenv('DASHBOARD_SECRET_KEY')
    if not secret_key:
        raise RuntimeError(
            "DASHBOARD_SECRET_KEY belum diset di .env. "
            "Generate dengan: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    app.secret_key = secret_key

    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    app.config.update(
        SESSION_COOKIE_SECURE=not debug,   # True di prod (HTTPS via Cloudflare), False di dev (http://localhost)
        SESSION_COOKIE_HTTPONLY=True,      # JS tidak bisa baca cookie session
        SESSION_COOKIE_SAMESITE='Lax',     # mitigasi CSRF dasar — minimal kalau ada link dari domain lain
    )

    # Inisialisasi rate limiter (decorator @limiter.limit dipakai di route /login)
    limiter.init_app(app)

    # Currency filter for Jinja2
    app.jinja_env.filters['idr'] = lambda x: f"Rp {int(x or 0):,}".replace(',', '.')

    from web.routes.public import public_bp
    from web.routes.home import home_bp
    from web.routes.profit import profit_bp
    from web.routes.transactions import transactions_bp
    from web.routes.capsters import capsters_bp
    from web.routes.services import services_bp
    from web.routes.branches import branches_bp
    from web.routes.products import products_bp
    from web.routes.withdraw import withdraw_bp
    from web.routes.report_daily import report_daily_bp
    from web.routes.compare import compare_bp
    from web.routes.api import api_bp
    from web.routes.customers import customers_bp
    from web.routes.capster_portal import capster_portal_bp
    from web.routes.promos import promos_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(profit_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(capsters_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(branches_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(withdraw_bp)
    app.register_blueprint(report_daily_bp)
    app.register_blueprint(compare_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(capster_portal_bp)
    app.register_blueprint(promos_bp)

    return app
