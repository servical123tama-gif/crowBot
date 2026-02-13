"""
Report Handlers
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

from app.utils.decorators import require_auth, require_owner_or_admin, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.utils.helpers import safe_edit_message
from app.config.constants import CB_MONTHLY_NAV, CB_PROFIT_NAV, MONTHS_ID # Import new constants

from typing import Optional

logger = logging.getLogger(__name__)


@handle_errors
@require_owner_or_admin
async def handle_weekly_breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly breakdown request - Owner only"""
    # from app.services.report_service import ReportService # Removed local import
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan per minggu...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_weekly_breakdown(is_owner=True)
        
        # Show week selection menu
        now = datetime.now()
        keyboard = KeyboardBuilder.week_selection_menu(now.year, now.month)
        
        # Add summary + menu
        message = report + "\n\n📋 Pilih minggu untuk detail:"
        
    except Exception as e:
        logger.error(f"Failed to generate weekly breakdown: {e}", exc_info=True)
        message = "❌ Gagal membuat laporan per minggu."
        keyboard = KeyboardBuilder.back_button()
    
    await safe_edit_message(query, message, reply_markup=keyboard)

@handle_errors
@require_owner_or_admin
async def handle_week_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, year: int, month: int, week_num: int):
    """Handle specific week detail request - Owner only"""
    # from app.services.report_service import ReportService # Removed local import
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, f"⏳ Memuat detail Minggu {week_num}...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_week_detail_report(year, month, week_num, is_owner=True)
    except Exception as e:
        logger.error(f"Failed to generate week detail: {e}", exc_info=True)
        report = "❌ Gagal membuat laporan detail minggu."
    
    # Back to weekly breakdown menu
    keyboard = [[
        InlineKeyboardButton("🔙 Kembali ke Daftar Minggu", callback_data='report_weekly_breakdown'),
        InlineKeyboardButton("🏠 Menu Utama", callback_data='back_main')
    ]]
    
    from telegram import InlineKeyboardMarkup
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await safe_edit_message(query, report, reply_markup=reply_markup)

@handle_errors
@require_owner_or_admin
async def handle_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily report request - Available for all capsters"""
    # from app.services.report_service import ReportService # Removed local import
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan harian...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_daily_report()
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)

@handle_errors
@require_owner_or_admin
async def handle_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly report request - Available for all capsters"""
    # from app.services.report_service import ReportService # Removed local import
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan mingguan...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_weekly_report()
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_owner_or_admin 
async def handle_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE, year: Optional[int] = None, month: Optional[int] = None):
    """Handle monthly report request with navigation - Owner/Admin only"""
    
    query = update.callback_query
    await query.answer()
    
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    
    month_name = MONTHS_ID.get(month, f"Bulan {month}")
    await safe_edit_message(query, f"⏳ Memuat laporan bulanan {month_name} {year}...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_monthly_report(year, month)
        keyboard = KeyboardBuilder.monthly_navigation_keyboard(year, month, CB_MONTHLY_NAV)
    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}", exc_info=True)
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
        keyboard = KeyboardBuilder.back_button()
    
    await safe_edit_message(query, report, reply_markup=keyboard)


@handle_errors
@require_owner_or_admin
async def handle_profit_report(update: Update, context: ContextTypes.DEFAULT_TYPE, year: Optional[int] = None, month: Optional[int] = None):
    """Handle monthly profit report request with navigation - Owner/Admin only"""
    
    query = update.callback_query
    await query.answer()
    
    if year is None or month is None:
        now = datetime.now()
        year = now.year
        month = now.month
    
    month_name = MONTHS_ID.get(month, f"Bulan {month}")
    await safe_edit_message(query, f"⏳ Menghitung laporan profit bulanan {month_name} {year}...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_monthly_profit_report(year, month)
        keyboard = KeyboardBuilder.monthly_navigation_keyboard(year, month, CB_PROFIT_NAV)
    except Exception as e:
        logger.error(f"Failed to generate monthly profit report: {e}", exc_info=True)
        report = "❌ Gagal membuat laporan profit. Silakan coba lagi."
        keyboard = KeyboardBuilder.back_button()
        
    await safe_edit_message(query, report, reply_markup=keyboard)


@handle_errors
@require_owner_or_admin
async def handle_stock_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stock report request - Owner/Admin only"""
    query = update.callback_query
    await query.answer()

    await safe_edit_message(query, "⏳ Memuat laporan stok produk...")

    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_stock_report()
    except Exception as e:
        logger.error(f"Failed to generate stock report: {e}", exc_info=True)
        report = "❌ Gagal membuat laporan stok. Silakan coba lagi."
        
    keyboard = KeyboardBuilder.back_button() # Assuming a back button is sufficient for stock report
    await safe_edit_message(query, report, reply_markup=keyboard)
    
    
# REPORT FOR CAPSTER 
@handle_errors
@require_auth
async def handle_capster_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily report request - Available for all capsters"""
    # from app.services.report_service import ReportService # Removed local import
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan harian...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_daily_report(user=username.first_name)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_auth
async def handle_capster_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly report request - Available for all capsters"""
    # from app.services.report_service import ReportService # Removed local import
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan mingguan...")
    
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_weekly_report(user=username.first_name)
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_auth
async def handle_capster_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle monthly report request - Owner/Admin only"""
    # from app.services.report_service import ReportService # Removed local import
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan bulanan...")
    
    now = datetime.now()
    try:
        report_service = context.bot_data['report_service']
        report = report_service.generate_monthly_report(
            user=username.first_name,
            year=now.year,
            month=now.month
        )
    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)