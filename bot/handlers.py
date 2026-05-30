"""Telegram command + callback handlers — admin-only."""
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.tg.auth import admin_only
from app.tg.reports import (
    daily_report, weekly_report, monthly_report,
    profit_report, capster_report,
)

logger = logging.getLogger(__name__)


# ── Keyboard ───────────────────────────────────────────────────────────────── #

def _main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📅 Harian', callback_data='rpt:daily'),
            InlineKeyboardButton('📊 Mingguan', callback_data='rpt:weekly'),
        ],
        [
            InlineKeyboardButton('🗓️ Bulanan', callback_data='rpt:monthly'),
            InlineKeyboardButton('💹 Profit', callback_data='rpt:profit'),
        ],
        [
            InlineKeyboardButton('💈 Per Capster', callback_data='rpt:capster'),
        ],
        [
            InlineKeyboardButton('🔄 Refresh', callback_data='rpt:menu'),
        ],
    ])


_REPORT_MAP = {
    'daily':   daily_report,
    'weekly':  weekly_report,
    'monthly': monthly_report,
    'profit':  profit_report,
    'capster': capster_report,
}


# ── Commands ───────────────────────────────────────────────────────────────── #

@admin_only
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    name = user.first_name if user else 'Owner'
    await update.message.reply_text(
        f"Halo {name}! 👋\n\n"
        "Bot laporan barbershop. Pilih laporan di bawah, "
        "atau pakai perintah:\n"
        "/harian — laporan hari ini\n"
        "/mingguan — 7 hari terakhir\n"
        "/bulanan — bulan ini\n"
        "/profit — profit per cabang\n"
        "/capster — breakdown per capster\n"
        "/help — bantuan",
        reply_markup=_main_keyboard(),
    )


@admin_only
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Perintah yang tersedia:\n"
        "/start — menu utama\n"
        "/harian — laporan hari ini\n"
        "/mingguan — 7 hari terakhir\n"
        "/bulanan — bulan ini\n"
        "/profit — profit per cabang (bulan ini)\n"
        "/capster — breakdown per capster (bulan ini)\n\n"
        "Notifikasi otomatis dikirim setiap jam 23:00 WIB.",
        reply_markup=_main_keyboard(),
    )


def _make_report_cmd(report_fn, label: str):
    @admin_only
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            text = report_fn()
        except Exception as e:
            logger.exception("Failed to build %s report", label)
            text = f"Gagal mengambil laporan {label}: {e}"
        await update.message.reply_text(text, reply_markup=_main_keyboard())
    return handler


cmd_harian   = _make_report_cmd(daily_report,   'harian')
cmd_mingguan = _make_report_cmd(weekly_report,  'mingguan')
cmd_bulanan  = _make_report_cmd(monthly_report, 'bulanan')
cmd_profit   = _make_report_cmd(profit_report,  'profit')
cmd_capster  = _make_report_cmd(capster_report, 'capster')


# ── Callback (inline buttons) ──────────────────────────────────────────────── #

@admin_only
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ''

    if not data.startswith('rpt:'):
        return

    action = data.split(':', 1)[1]

    if action == 'menu':
        await query.message.reply_text(
            "Pilih laporan:", reply_markup=_main_keyboard()
        )
        return

    fn = _REPORT_MAP.get(action)
    if not fn:
        await query.message.reply_text("Perintah tidak dikenal.")
        return

    try:
        text = fn()
    except Exception as e:
        logger.exception("Failed to build %s report", action)
        text = f"Gagal mengambil laporan {action}: {e}"

    await query.message.reply_text(text, reply_markup=_main_keyboard())
