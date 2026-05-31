"""Telegram bot wiring — build Application and register handlers."""
import logging
import os

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from bot.handlers import (
    cmd_start, cmd_help,
    cmd_harian, cmd_mingguan, cmd_bulanan,
    cmd_profit, cmd_capster,
    on_button,
)
from bot.scheduler import setup_daily_push

logger = logging.getLogger(__name__)


def build_app() -> Application:
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN belum diset di .env. "
            "Dapatkan token dari @BotFather lalu isi di file .env."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(CommandHandler('harian', cmd_harian))
    app.add_handler(CommandHandler('mingguan', cmd_mingguan))
    app.add_handler(CommandHandler('bulanan', cmd_bulanan))
    app.add_handler(CommandHandler('profit', cmd_profit))
    app.add_handler(CommandHandler('capster', cmd_capster))
    app.add_handler(CallbackQueryHandler(on_button))

    setup_daily_push(app)

    return app


def run() -> None:
    app = build_app()
    logger.info("Telegram bot starting (polling)...")
    app.run_polling(allowed_updates=['message', 'callback_query'])
