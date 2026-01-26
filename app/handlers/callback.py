"""
Callback Query Router
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.utils.decorators import require_auth, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.config.constants import *
from app.services.branch_service import BranchService
from app.handlers.branch import show_branch_selection, handle_branch_selection, handle_change_branch
from app.handlers.transaction import handle_service_selection, handle_payment_selection
from app.handlers.report import (
    handle_daily_report,
    handle_weekly_report,
    handle_monthly_report,
    handle_capster_weekly_report,
    handle_capster_daily_report,
    handle_capster_monthly_report
)

logger = logging.getLogger(__name__)

@handle_errors
@require_auth
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Callback from user {user_id}: {data}")
    
    #Branch selection
    if data.startswith(CB_BRANCH):
        branch_id = data.replace(f"{CB_BRANCH}_", "")
        await handle_branch_selection(update, context, branch_id)
    
    # Change branch
    elif data == CB_CHANGE_BRANCH:
        await handle_change_branch(update, context)
    
    # Add transaction - Show service menu
    elif data == CB_ADD_TRANSACTION:
        # Check if user has set branch today
        if not BranchService.has_branch_today(user_id):
            await show_branch_selection(update = update, context=context, is_first_time=True)
            return
        
        await query.answer()
        keyboard = KeyboardBuilder.service_menu()
        await query.edit_message_text(
            "📋 Pilih layanan:",
            reply_markup=keyboard
        )
    
    # Main service selection → Show payment menu
    elif data.startswith(CB_SERVICE_MAIN):
        service_id = data.replace(f"{CB_SERVICE_MAIN}_", "")
        await handle_service_selection(update, context, service_id)
    
    # Show coloring submenu
    elif data == CB_COLORING_MENU:
        await query.answer()
        keyboard = KeyboardBuilder.coloring_menu()
        await query.edit_message_text(
            "🎨 Pilih layanan Coloring:",
            reply_markup=keyboard
        )
    
    # Coloring service selection → Show payment menu
    elif data.startswith(CB_SERVICE_COLORING):
        service_id = data.replace(f"{CB_SERVICE_COLORING}_", "")
        await handle_service_selection(update, context, service_id)
    
    # Payment selection → Save transaction
    elif data.startswith(CB_PAYMENT):
        # Format: payment_<service_id>_<payment_id>
        parts = data.replace(f"{CB_PAYMENT}_", "").split("_", 1)
        if len(parts) == 2:
            service_id, payment_id = parts
            await handle_payment_selection(update, context, service_id, payment_id)
        else:
            await query.answer("⚠️ Format callback tidak valid")
    
    # Back to service menu
    elif data == CB_BACK_SERVICE:
        await query.answer()
        keyboard = KeyboardBuilder.service_menu()
        await query.edit_message_text(
            "📋 Pilih layanan:",
            reply_markup=keyboard
        )
    
    # Reports
    elif data == CB_REPORT_DAILY:
        await handle_daily_report(update, context)
    
    elif data == CB_REPORT_WEEKLY:
        await handle_weekly_report(update, context)
    
    elif data == CB_REPORT_MONTHLY:
        await handle_monthly_report(update, context)
        
    elif data == CB_REPORT_DAILY_CAPSTER:
        await handle_capster_daily_report(update, context)
    
    elif data == CB_REPORT_WEEKLY_CAPSTER:
        await handle_capster_weekly_report(update, context)
        
    elif data == CB_REPORT_MONTHLY_CAPSTER:
        await handle_capster_monthly_report(update, context)
    
    # Back to main menu
    elif data == CB_BACK_MAIN:
        await query.answer()
        keyboard = KeyboardBuilder.main_menu(user_id=user_id)
        await query.edit_message_text("Silakan pilih menu:", reply_markup=keyboard)
    
    
    else:
        await query.answer("⚠️ Aksi tidak dikenal")
        logger.warning(f"Unknown callback data: {data}")