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

    from dashboard.routes.home import home_bp
    from dashboard.routes.profit import profit_bp
    from dashboard.routes.transactions import transactions_bp
    from dashboard.routes.capsters import capsters_bp
    from dashboard.routes.services import services_bp
    from dashboard.routes.branches import branches_bp
    from dashboard.routes.products import products_bp
    from dashboard.routes.withdraw import withdraw_bp
    from dashboard.routes.report_daily import report_daily_bp
    from dashboard.routes.compare import compare_bp
    from dashboard.routes.api import api_bp
    from dashboard.routes.bot_control import bot_control_bp

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
    app.register_blueprint(bot_control_bp)

    return app
