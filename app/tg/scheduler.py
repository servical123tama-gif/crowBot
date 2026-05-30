"""Auto-push daily summary at 23:00 WIB to all OWNER_IDS."""
import logging
import os
from datetime import time as dt_time

import pytz
from telegram.ext import Application, ContextTypes

from app.tg.auth import owner_ids
from app.tg.reports import daily_report

logger = logging.getLogger(__name__)


async def _push_daily(context: ContextTypes.DEFAULT_TYPE):
    text = daily_report()
    for owner_id in owner_ids():
        try:
            await context.bot.send_message(chat_id=owner_id, text=text)
            logger.info("Daily push sent to owner %s", owner_id)
        except Exception as e:
            logger.error("Failed to push daily report to %s: %s", owner_id, e)


def setup_daily_push(app: Application) -> None:
    """Register the 23:00 daily job using the bot's JobQueue."""
    tz_name = os.getenv('TIMEZONE', 'Asia/Jakarta')
    try:
        tz = pytz.timezone(tz_name)
    except Exception:
        logger.warning("Invalid TIMEZONE=%s, falling back to Asia/Jakarta", tz_name)
        tz = pytz.timezone('Asia/Jakarta')

    job_queue = app.job_queue
    if job_queue is None:
        logger.warning(
            "JobQueue tidak tersedia. Pastikan python-telegram-bot[job-queue] terinstall."
        )
        return

    job_queue.run_daily(
        _push_daily,
        time=dt_time(hour=23, minute=0, tzinfo=tz),
        name='daily_push_23',
    )
    logger.info("Scheduled daily push at 23:00 %s", tz_name)
