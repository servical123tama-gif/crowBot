"""
Report Handlers
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.utils.decorators import require_auth, require_owner_or_admin, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.utils.helpers import safe_edit_message

logger = logging.getLogger(__name__)

@handle_errors
@require_owner_or_admin
async def handle_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily report request - Available for all casters"""
    from app.services.report_service import ReportService
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan harian...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_daily_report()
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)

@handle_errors
@require_owner_or_admin
async def handle_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly report request - Available for all casters"""
    from app.services.report_service import ReportService
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan mingguan...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_weekly_report()
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_owner_or_admin 
async def handle_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle monthly report request - Owner/Admin only"""
    from app.services.report_service import ReportService
    
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan bulanan...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_monthly_report()
    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    
    
# REPORT FOR CAPSTER 
@handle_errors
@require_auth
async def handle_capster_daily_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle daily report request - Available for all casters"""
    from app.services.report_service import ReportService
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan harian...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_daily_report_capster(user=username.first_name)
    except Exception as e:
        logger.error(f"Failed to generate daily report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_auth
async def handle_capster_weekly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle weekly report request - Available for all casters"""
    from app.services.report_service import ReportService
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan mingguan...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_weekly_report_capster(user=username.first_name)
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)
    

@handle_errors
@require_auth
async def handle_capster_monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle monthly report request - Owner/Admin only"""
    from app.services.report_service import ReportService
    username = update.effective_user
    query = update.callback_query
    await query.answer()
    
    await safe_edit_message(query, "⏳ Memuat laporan bulanan...")
    
    try:
        report_service = ReportService()
        report = report_service.generate_monthly_report_capster(user=username.first_name)
    except Exception as e:
        logger.error(f"Failed to generate monthly report: {e}")
        report = "❌ Gagal membuat laporan. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await safe_edit_message(query, report, reply_markup=keyboard)