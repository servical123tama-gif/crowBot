"""
Transaction Handlers
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from app.utils.decorators import require_auth, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.utils.formatters import Formatter
from app.models.transaction import Transaction
from app.config.constants import ALL_SERVICES, PAYMENT_METHODS, MSG_SELECT_PAYMENT, BRANCHES
from app.config.settings import settings

logger = logging.getLogger(__name__)

@handle_errors
@require_auth
async def handle_service_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, service_id: str):
    """Handle service selection - Show payment method menu"""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"User selected service: {service_id}")
    
    # Validate service
    if service_id not in ALL_SERVICES:
        await query.edit_message_text("❌ Layanan tidak valid")
        return
    
    service_data = ALL_SERVICES[service_id]
    service_name = service_data['name']
    price = service_data['price']
    
    # Show payment method selection
    message = MSG_SELECT_PAYMENT.format(
        service=service_name,
        currency=settings.CURRENCY,
        price=price
    )
    
    keyboard = KeyboardBuilder.payment_method_menu(service_id)
    
    await query.edit_message_text(message, reply_markup=keyboard)
    logger.info(f"Showed payment menu for service: {service_id}")

@handle_errors
@require_auth
async def handle_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, service_id: str, payment_id: str):
    """Handle payment method selection - Save transaction"""
    from app.services.sheets_service import SheetsService
    from app.services.branch_service import BranchService
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Validate service and payment
    if service_id not in ALL_SERVICES or payment_id not in PAYMENT_METHODS:
        await query.edit_message_text("❌ Data tidak valid")
        return
    
    # Get branch
    branch_id = BranchService.get_branch(user_id)
    if not branch_id:
        await query.edit_message_text("❌ Cabang belum dipilih. Silakan pilih cabang terlebih dahulu.")
        return
    
    # Get data
    service_data = ALL_SERVICES[service_id]
    payment_data = PAYMENT_METHODS[payment_id]
    branch_data = BRANCHES[branch_id]
    
    service_name = service_data['name']
    price = service_data['price']
    payment_name = payment_data['name']
    branch_name = branch_data['short']
    
    # Create transaction - PASTIKAN URUTAN PARAMETER SESUAI MODEL
    caster_name = query.from_user.first_name
    transaction = Transaction(
        caster=caster_name,
        service=service_name,
        price=price,
        branch=branch_name,
        payment_method=payment_name,  
        date=datetime.now()           
    )
    
    # Show loading
    loading_msg = await query.edit_message_text("⏳ Menyimpan transaksi...")
    
    # Save
    try:
        logger.info(f"Saving transaction: {transaction}")
        sheets_service = SheetsService()
        success = sheets_service.add_transaction(transaction)
        logger.info(f"Save result: {success}")
    except Exception as e:
        logger.error(f"Failed to save: {e}", exc_info=True)
        success = False
    
    # Response
    if success:
        message = Formatter.format_transaction_success({
            'service': service_name,
            'price': price,
            'payment_method': payment_name,
            'branch': branch_name,
            'caster': caster_name,
            'time': datetime.now()
        })
    else:
        message = "❌ Gagal menyimpan transaksi. Silakan coba lagi."
    
    keyboard = KeyboardBuilder.back_button()
    await loading_msg.edit_text(message, reply_markup=keyboard)