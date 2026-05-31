"""Flask Dashboard — App Factory"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from dotenv import load_dotenv
load_dotenv()


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.secret_key = os.getenv('DASHBOARD_SECRET_KEY', 'barbershop-dashboard-2026')

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
