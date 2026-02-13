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
    handle_profit_report,
    handle_capster_weekly_report,
    handle_capster_daily_report,
    handle_capster_monthly_report,
    handle_week_detail,
    handle_weekly_breakdown,
)
from app.handlers.customer import customer_menu_handler, list_customers_handler

logger = logging.getLogger(__name__)

@handle_errors
@require_auth
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route callback queries to appropriate handlers using a dispatch dictionary."""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    logger.info(f"Callback from user {user_id}: {data}")

    # --- Handler Mappings ---
    # Exact matches are checked first, then prefixes.
    EXACT_HANDLERS = {
        CB_CHANGE_BRANCH: handle_change_branch,
        CB_CUSTOMER_MENU: customer_menu_handler,
        CB_LIST_CUSTOMERS: list_customers_handler,
        CB_COLORING_MENU: lambda u, c: u.callback_query.edit_message_text(
            "🎨 Pilih layanan Coloring:",
            reply_markup=KeyboardBuilder.coloring_menu()
        ),
        CB_BACK_SERVICE: lambda u, c: u.callback_query.edit_message_text(
            "📋 Pilih layanan:",
            reply_markup=KeyboardBuilder.service_menu()
        ),
        CB_REPORT_DAILY: handle_daily_report,
        CB_REPORT_WEEKLY: handle_weekly_report,
        CB_REPORT_MONTHLY: handle_monthly_report,
        CB_REPORT_PROFIT: handle_profit_report,
        CB_REPORT_DAILY_CAPSTER: handle_capster_daily_report,
        CB_REPORT_WEEKLY_CAPSTER: handle_capster_weekly_report,
        CB_REPORT_MONTHLY_CAPSTER: handle_capster_monthly_report,
        CB_REPORT_WEEKLY_BREAKDOWN: handle_weekly_breakdown,
        CB_BACK_MAIN: lambda u, c: u.callback_query.edit_message_text(
            "Silakan pilih menu:",
            reply_markup=KeyboardBuilder.main_menu(user_id=u.effective_user.id)
        ),
    }

    PREFIX_HANDLERS = {
        CB_BRANCH: lambda u, c, d: handle_branch_selection(u, c, d.replace(f"{CB_BRANCH}_", "")),
        CB_SERVICE_MAIN: lambda u, c, d: handle_service_selection(u, c, d.replace(f"{CB_SERVICE_MAIN}_", "")),
        CB_SERVICE_COLORING: lambda u, c, d: handle_service_selection(u, c, d.replace(f"{CB_SERVICE_COLORING}_", "")),
        CB_PAYMENT: lambda u, c, d: handle_payment_selection(u, c, *d.replace(f"{CB_PAYMENT}_", "").split("_", 1)),
        CB_MONTHLY_NAV: lambda u, c, d: handle_monthly_report(u, c, *map(int, d.replace(f"{CB_MONTHLY_NAV}_", "").split("_"))),
        CB_PROFIT_NAV: lambda u, c, d: handle_profit_report(u, c, *map(int, d.replace(f"{CB_PROFIT_NAV}_", "").split("_"))),
        CB_WEEK_SELECT: lambda u, c, d: handle_week_detail(u, c, *map(int, d.replace(f"{CB_WEEK_SELECT}_", "").split("_"))),
    }

    # --- Special Case: Add Transaction (requires pre-check) ---
    if data == CB_ADD_TRANSACTION:
        if not BranchService.has_branch_today(user_id):
            await show_branch_selection(update=update, context=context, is_first_time=True)
        else:
            await query.answer()
            await query.edit_message_text("📋 Pilih layanan:", reply_markup=KeyboardBuilder.service_menu())
        return

    # --- Routing Logic ---
    if data in EXACT_HANDLERS:
        await EXACT_HANDLERS[data](update, context)
        return

    for prefix, handler in PREFIX_HANDLERS.items():
        if data.startswith(prefix):
            await handler(update, context, data)
            return

    # --- Fallback for unknown callbacks ---
    await query.answer("⚠️ Aksi tidak dikenal")
    logger.warning(f"Unknown callback data: {data}")