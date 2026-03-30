"""
Entry point — jalankan Flask dashboard.
  python run_dashboard.py
  gunicorn run_dashboard:app
"""
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

from app.db.database import init_db
init_db()
logger.info("Database initialized.")

from dashboard import create_app
app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    print(f"\n  Dashboard : http://localhost:{port}")
    print(f"  Debug     : {debug}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)
