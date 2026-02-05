"""
Customer Menu Handler
"""
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.utils.decorators import require_auth, log_command, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.config.constants import *
from app.services.auth_service import AuthService
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)

# States for conversation
GET_NAME, GET_PHONE = range(2)

@handle_errors
@log_command
@require_auth
async def customer_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle customer menu"""
    user = update.effective_user
    
    keyboard = KeyboardBuilder.customer_menu(user.id)
    
    await update.callback_query.edit_message_text(
        text=MSG_CUSTOMER_MENU,
        reply_markup=keyboard
    )

@handle_errors
@log_command
@require_auth
async def add_customer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the add customer conversation."""
    await update.callback_query.message.reply_text(MSG_ADD_CUSTOMER_NAME)
    return GET_NAME

@handle_errors
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get customer name and ask for phone number."""
    context.user_data['customer_name'] = update.message.text
    await update.message.reply_text(MSG_ADD_CUSTOMER_PHONE)
    return GET_PHONE

@handle_errors
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get customer phone number and save the customer."""
    customer_name = context.user_data.get('customer_name')
    customer_phone = update.message.text

    customer_service = CustomerService()
    if customer_service.add_customer(customer_name, customer_phone):
        await update.message.reply_text(MSG_CUSTOMER_ADDED.format(name=customer_name, phone=customer_phone))
    else:
        await update.message.reply_text("❌ Gagal menambahkan pelanggan.")

    context.user_data.clear()
    return ConversationHandler.END

@handle_errors
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Penambahan pelanggan dibatalkan.")
    context.user_data.clear()
    return ConversationHandler.END

add_customer_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_customer_handler, pattern=f"^{CB_ADD_CUSTOMER}$")],
    states={
        GET_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
        GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)

@handle_errors
@log_command
@require_auth
async def list_customers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all customers (owner/admin only)."""
    user_id = update.effective_user.id
    if not AuthService.is_owner_or_admin(user_id):
        await update.callback_query.answer(MSG_UNAUTHORIZED_FEATURE, show_alert=True)
        return

    customer_service = CustomerService()
    customers = customer_service.get_all_customers()

    if not customers:
        await update.callback_query.edit_message_text("Tidak ada pelanggan terdaftar.")
        return

    report = f"{MSG_CUSTOMER_LIST_HEADER}\n\n"
    for i, customer in enumerate(customers, 1):
        report += f"{i}. {customer.name} - {customer.phone}\n"

    await update.callback_query.edit_message_text(report)
