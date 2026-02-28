"""
Entry point — jalankan Flask Dashboard + Telegram Bot bersamaan.

Bot dikelola oleh BotManager (bisa di-start/stop dari web).
Flask berjalan di main thread.

Usage:
    python run_dashboard.py
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/dashboard.log', encoding='utf-8'),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger('run_dashboard')

# ── Database init (buat tabel + migrasi kolom baru jika belum ada) ────────────
from app.db.database import init_db
init_db()

# ── Flask App ─────────────────────────────────────────────────────────────────
from dashboard import create_app
flask_app = create_app()

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 5000))

    # Auto-start bot via BotManager
    from app.bot_manager import BotManager
    mgr = BotManager()
    mgr.start()
    logger.info("BotManager: bot thread dimulai (auto-start).")

    print()
    print("=" * 55)
    print(f"  Dashboard : http://localhost:{port}")
    print(f"  Password  : {os.getenv('DASHBOARD_PASSWORD', 'admin123')}")
    print(f"  Bot       : berjalan via BotManager (on/off dari web)")
    print(f"  Stop      : Ctrl+C")
    print("=" * 55)
    print()

    # Flask di main thread
    # use_reloader=False wajib: reloader fork-process akan duplikasi bot thread
    # debug=False wajib: debug mode tidak kompatibel dengan bot thread
    flask_app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
    )
