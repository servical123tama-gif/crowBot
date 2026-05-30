"""
Entry point — jalankan Telegram bot (admin reports only).
  python run_bot.py

Bot ini terpisah dari dashboard web. Pastikan dependencies sudah terinstall:
  pip install -r requirements.txt
"""
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO').upper(),
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

# Database harus siap sebelum bot mulai polling
from app.db.database import init_db
init_db()
logger.info("Database initialized.")

from app.tg.bot import run
run()
