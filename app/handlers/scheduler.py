"""
Scheduled Jobs - Daily notification and other automated tasks
"""
import logging
from datetime import time

import pytz
from telegram.ext import ContextTypes

from app.config.settings import settings

logger = logging.getLogger(__name__)

TIMEZONE = pytz.timezone(settings.TIMEZONE)


async def send_daily_report_to_owners(context: ContextTypes.DEFAULT_TYPE):
    """
    Scheduled job: sends daily summary report to all owners every night.
    Triggered by JobQueue.run_daily().
    """
    logger.info("Running scheduled daily report notification...")

    report_service = context.bot_data.get('report_service')
    if not report_service:
        logger.error("ReportService not found in bot_data, skipping daily notification")
        return

    try:
        report = report_service.generate_daily_report()
    except Exception as e:
        logger.error(f"Failed to generate daily report for notification: {e}", exc_info=True)
        report = None

    if not report:
        report = "📊 Tidak ada transaksi hari ini."

    header = "🔔 *Ringkasan Harian Otomatis*\n\n"
    message = header + report

    sent_count = 0
    for owner_id in settings.OWNER_IDS:
        try:
            await context.bot.send_message(
                chat_id=owner_id,
                text=message,
                parse_mode="Markdown"
            )
            sent_count += 1
            logger.info(f"Daily report sent to owner {owner_id}")
        except Exception as e:
            # Retry without Markdown if parsing fails
            try:
                await context.bot.send_message(chat_id=owner_id, text=message)
                sent_count += 1
            except Exception as retry_err:
                logger.error(f"Failed to send daily report to owner {owner_id}: {retry_err}")

    logger.info(f"Daily report notification completed. Sent to {sent_count}/{len(settings.OWNER_IDS)} owners.")


def setup_scheduled_jobs(application):
    """
    Register all scheduled jobs to the application's JobQueue.
    Called during bot initialization.
    """
    job_queue = application.job_queue

    if not job_queue:
        logger.error("JobQueue is not available. Scheduled jobs will NOT run.")
        return

    if not settings.OWNER_IDS:
        logger.warning("No OWNER_IDS configured. Daily notification will not be scheduled.")
        return

    # Daily report at 23:00 WIB
    job_queue.run_daily(
        callback=send_daily_report_to_owners,
        time=time(hour=23, minute=0, second=0, tzinfo=TIMEZONE),
        name="daily_report_notification"
    )

    logger.info(f"Scheduled daily report notification at 23:00 {settings.TIMEZONE} for {len(settings.OWNER_IDS)} owner(s)")
