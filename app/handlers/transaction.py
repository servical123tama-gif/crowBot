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
from app.config.constants import (
    ALL_SERVICES, PAYMENT_METHODS, MSG_SELECT_PAYMENT, BRANCHES,
    PRODUCTS, MSG_PRODUCT_SELECT_PAYMENT, MSG_SELECT_PRODUCT,
)
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
    # from app.services.sheets_service import SheetsService # No longer need to import here
    from app.services.branch_service import BranchService
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Validate service and payment
    if service_id not in ALL_SERVICES or payment_id not in PAYMENT_METHODS:
        logger.warning(f"Invalid service/payment: service_id={service_id}, payment_id={payment_id}")
        await query.edit_message_text("❌ Data tidak valid. Silakan coba lagi.", reply_markup=KeyboardBuilder.back_button())
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
    
    # Create transaction - gunakan nama asli dari CapsterList, fallback ke first_name
    capster_service = context.bot_data.get('capster_service')
    capster_name = capster_service.get_real_name(user_id, fallback=query.from_user.first_name)
    transaction = Transaction(
        capster=capster_name,
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
        sheets_service = context.bot_data['sheets_service'] # Retrieve the SheetsService instance
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
            'capster': capster_name,
            'time': datetime.now()
        })
        keyboard = KeyboardBuilder.transaction_success()
    else:
        message = "❌ Gagal menyimpan transaksi. Silakan coba lagi."
        keyboard = KeyboardBuilder.back_button()

    await loading_msg.edit_text(message, reply_markup=keyboard)


# ==================================================================
# Product Transaction (Capster sells a product)
# ==================================================================

@handle_errors
@require_auth
async def handle_sell_product_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product selection menu for capster."""
    query = update.callback_query

    from app.services.branch_service import BranchService
    user_id = query.from_user.id

    if not BranchService.has_branch_today(user_id):
        from app.handlers.branch import show_branch_selection
        await show_branch_selection(update=update, context=context, is_first_time=True)
        return

    await query.answer()
    if not PRODUCTS:
        await query.edit_message_text(
            "📭 Belum ada produk tersedia.\n\nHubungi Owner untuk menambahkan produk.",
            reply_markup=KeyboardBuilder.back_button()
        )
        return
    await query.edit_message_text(MSG_SELECT_PRODUCT, reply_markup=KeyboardBuilder.product_menu())


@handle_errors
@require_auth
async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str):
    """Handle product selection — show payment method menu."""
    query = update.callback_query
    await query.answer()

    logger.info(f"User selected product: {product_id}")

    if product_id not in PRODUCTS:
        await query.edit_message_text("❌ Produk tidak valid")
        return

    product_data = PRODUCTS[product_id]
    message = MSG_PRODUCT_SELECT_PAYMENT.format(
        product=product_data['name'],
        currency=settings.CURRENCY,
        price=product_data['price']
    )
    keyboard = KeyboardBuilder.product_payment_menu(product_id)
    await query.edit_message_text(message, reply_markup=keyboard)


@handle_errors
@require_auth
async def handle_product_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: str, payment_id: str):
    """Handle product payment selection — save transaction."""
    from app.services.branch_service import BranchService

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if product_id not in PRODUCTS or payment_id not in PAYMENT_METHODS:
        await query.edit_message_text("❌ Data tidak valid.", reply_markup=KeyboardBuilder.back_button())
        return

    branch_id = BranchService.get_branch(user_id)
    if not branch_id:
        await query.edit_message_text("❌ Cabang belum dipilih. Silakan pilih cabang terlebih dahulu.")
        return

    product_data = PRODUCTS[product_id]
    payment_data = PAYMENT_METHODS[payment_id]
    branch_data = BRANCHES[branch_id]

    product_name = product_data['name']
    price = product_data['price']
    payment_name = payment_data['name']
    branch_name = branch_data['short']

    capster_service = context.bot_data.get('capster_service')
    capster_name = capster_service.get_real_name(user_id, fallback=query.from_user.first_name)

    # Record as transaction with service = "[Produk] <name>"
    transaction = Transaction(
        capster=capster_name,
        service=f"[Produk] {product_name}",
        price=price,
        branch=branch_name,
        payment_method=payment_name,
        date=datetime.now()
    )

    loading_msg = await query.edit_message_text("⏳ Menyimpan penjualan produk...")

    try:
        sheets_service = context.bot_data['sheets_service']
        success = sheets_service.add_transaction(transaction)
        logger.info(f"Product sale saved: {success} — {transaction}")
    except Exception as e:
        logger.error(f"Failed to save product sale: {e}", exc_info=True)
        success = False

    if success:
        message = (
            f"✅ Penjualan produk berhasil dicatat!\n\n"
            f"📋 Detail:\n"
            f"- Produk: {product_name}\n"
            f"- Harga: {settings.CURRENCY} {price:,}\n"
            f"- Capster: {capster_name}\n"
            f"- Branch: {branch_name}\n"
            f"- Payment: {payment_name}\n"
            f"- Waktu: {Formatter.format_time(datetime.now())}"
        )
        keyboard = KeyboardBuilder.product_sale_success()
    else:
        message = "❌ Gagal menyimpan penjualan produk. Silakan coba lagi."
        keyboard = KeyboardBuilder.back_button()

    await loading_msg.edit_text(message, reply_markup=keyboard)