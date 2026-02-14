"""
Config Management Handler — CRUD for services and branch costs via bot.
"""
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

from app.utils.decorators import require_owner, handle_errors, log_command
from app.utils.keyboards import KeyboardBuilder
from app.config.constants import (
    CB_CONFIG_MENU,
    CB_CONFIG_SERVICES,
    CB_CONFIG_BRANCHES,
    CB_CONFIG_LIST_SERVICES,
    CB_CONFIG_ADD_SERVICE,
    CB_CONFIG_EDIT_SERVICE,
    CB_CONFIG_REMOVE_SERVICE,
    CB_CONFIG_CONFIRM_RM_SVC,
    CB_CONFIG_EDIT_BRANCH,
    CB_CONFIG_EDIT_BRANCH_COST,
    CB_CONFIG_EDIT_BRANCH_COMMISSION,
    CB_CONFIG_PRODUCTS,
    CB_CONFIG_LIST_PRODUCTS,
    CB_CONFIG_ADD_PRODUCT,
    CB_CONFIG_EDIT_PRODUCT,
    CB_CONFIG_REMOVE_PRODUCT,
    CB_CONFIG_CONFIRM_RM_PRD,
    MSG_CONFIG_MENU,
    MSG_CONFIG_SERVICES_MENU,
    MSG_CONFIG_BRANCHES_MENU,
    MSG_CONFIG_PRODUCTS_MENU,
    SERVICES_MAIN,
    SERVICES_COLORING,
    ALL_SERVICES,
    BRANCHES,
    PRODUCTS,
)

logger = logging.getLogger(__name__)

# Conversation states — Add Service
GET_SVC_NAME, GET_SVC_CATEGORY, GET_SVC_PRICE = range(20, 23)
# Conversation states — Edit Service Price
GET_NEW_PRICE = 25
# Conversation states — Edit Branch Cost
GET_NEW_COST_VALUE = 30
# Conversation states — Edit Branch Commission
GET_NEW_COMMISSION = 35
# Conversation states — Add Product
GET_PRD_NAME, GET_PRD_PRICE = range(40, 42)
# Conversation states — Edit Product Price
GET_NEW_PRD_PRICE = 45


# ------------------------------------------------------------------
# Menu handlers (exact callbacks)
# ------------------------------------------------------------------

@handle_errors
@log_command
@require_owner
async def config_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show config main menu."""
    await update.callback_query.edit_message_text(
        text=MSG_CONFIG_MENU,
        reply_markup=KeyboardBuilder.config_menu()
    )


@handle_errors
@log_command
@require_owner
async def config_services_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show services config menu."""
    await update.callback_query.edit_message_text(
        text=MSG_CONFIG_SERVICES_MENU,
        reply_markup=KeyboardBuilder.config_services_menu()
    )


@handle_errors
@log_command
@require_owner
async def config_list_services_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all services with edit/delete buttons."""
    query = update.callback_query
    await query.answer()

    text = "📋 Daftar Layanan\n\n"
    if SERVICES_MAIN:
        text += "Layanan Utama:\n"
        for sid, data in SERVICES_MAIN.items():
            text += f"  - {data['name']}: Rp {data['price']:,}\n"
    if SERVICES_COLORING:
        text += "\nLayanan Coloring:\n"
        for sid, data in SERVICES_COLORING.items():
            text += f"  - {data['name']}: Rp {data['price']:,}\n"
    text += "\nKlik ✏️ untuk edit harga, 🗑️ untuk hapus."

    keyboard = KeyboardBuilder.config_service_list(SERVICES_MAIN, SERVICES_COLORING)
    try:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception:
        pass


@handle_errors
@log_command
@require_owner
async def config_branches_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List branches for config editing."""
    query = update.callback_query
    await query.answer()

    text = MSG_CONFIG_BRANCHES_MENU + "\n\n"
    for bid, data in BRANCHES.items():
        costs = data.get('operational_cost', {})
        total_cost = sum(costs.values())
        commission = data.get('commission_rate', 0)
        text += f"🏢 {data['name']} ({data.get('short', '')})\n"
        text += f"   Biaya: Rp {total_cost:,} | Komisi: {commission * 100:.0f}%\n\n"

    keyboard = KeyboardBuilder.config_branch_list(BRANCHES)
    try:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception:
        pass


# ------------------------------------------------------------------
# Remove Service (prefix callbacks)
# ------------------------------------------------------------------

async def handle_remove_service(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Show confirmation before removing a service."""
    query = update.callback_query
    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    service_id = data.replace(f"{CB_CONFIG_REMOVE_SERVICE}_", "")
    service_data = ALL_SERVICES.get(service_id)
    if not service_data:
        await query.answer("❌ Layanan tidak ditemukan", show_alert=True)
        return

    await query.answer()
    keyboard = KeyboardBuilder.confirm_remove_service(service_id, service_data['name'])
    await query.edit_message_text(
        f"⚠️ Yakin ingin menghapus layanan **{service_data['name']}** (Rp {service_data['price']:,})?",
        reply_markup=keyboard
    )


async def handle_confirm_remove_service(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Actually remove service after confirmation."""
    query = update.callback_query
    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    service_id = data.replace(f"{CB_CONFIG_CONFIRM_RM_SVC}_", "")
    config_service = context.bot_data.get('config_service')

    service_data = ALL_SERVICES.get(service_id)
    service_name = service_data['name'] if service_data else service_id

    if config_service.remove_service(service_id):
        await query.answer(f"✅ Layanan '{service_name}' dihapus.")
        await config_list_services_handler(update, context)
    else:
        await query.answer("❌ Gagal menghapus layanan.", show_alert=True)


# ------------------------------------------------------------------
# Edit Branch — select branch → show costs
# ------------------------------------------------------------------

async def handle_edit_branch_select(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Show branch cost details with edit buttons."""
    query = update.callback_query
    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    branch_id = data.replace(f"{CB_CONFIG_EDIT_BRANCH}_", "")
    branch_data = BRANCHES.get(branch_id)
    if not branch_data:
        await query.answer("❌ Cabang tidak ditemukan", show_alert=True)
        return

    await query.answer()
    costs = branch_data.get('operational_cost', {})
    commission = branch_data.get('commission_rate', 0)
    text = f"🏢 {branch_data['name']}\n\n"
    text += "Biaya Operasional:\n"
    for key, val in costs.items():
        text += f"  - {key}: Rp {int(val):,}\n"
    text += f"\nKomisi: {commission * 100:.0f}%\n"
    text += f"Karyawan: {branch_data.get('employees', 0)}\n"
    text += "\nKlik untuk edit:"

    keyboard = KeyboardBuilder.config_branch_costs(branch_id, branch_data)
    await query.edit_message_text(text=text, reply_markup=keyboard)


# ------------------------------------------------------------------
# ConversationHandler — Add Service
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def add_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start add service conversation."""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "✍️ Masukkan nama layanan baru:\n\n💡 Ketik /cancel untuk membatalkan."
    )
    return GET_SVC_NAME


@handle_errors
async def add_service_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get service name, ask for category."""
    context.user_data['new_svc_name'] = update.message.text.strip()
    await update.message.reply_text(
        "📂 Pilih kategori:\n\n"
        "1. main (Layanan Utama)\n"
        "2. coloring (Layanan Coloring)\n\n"
        "Ketik `main` atau `coloring`:"
    )
    return GET_SVC_CATEGORY


@handle_errors
async def add_service_get_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get category, ask for price."""
    text = update.message.text.strip().lower()
    if text not in ('main', 'coloring'):
        await update.message.reply_text("❌ Kategori harus 'main' atau 'coloring'. Coba lagi:")
        return GET_SVC_CATEGORY
    context.user_data['new_svc_category'] = text
    await update.message.reply_text("💰 Masukkan harga (angka saja, contoh: 25000):")
    return GET_SVC_PRICE


@handle_errors
async def add_service_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get price, save service."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    try:
        price = int(text)
    except ValueError:
        await update.message.reply_text("❌ Harga harus angka. Coba lagi:")
        return GET_SVC_PRICE

    name = context.user_data.get('new_svc_name')
    category = context.user_data.get('new_svc_category')
    config_service = context.bot_data.get('config_service')

    if config_service.add_service(name, category, price):
        await update.message.reply_text(
            f"✅ Layanan berhasil ditambahkan!\n\n"
            f"Nama: {name}\n"
            f"Kategori: {category}\n"
            f"Harga: Rp {price:,}"
        )
    else:
        await update.message.reply_text("❌ Gagal menambahkan layanan. Silakan coba lagi.")

    context.user_data.pop('new_svc_name', None)
    context.user_data.pop('new_svc_category', None)
    return ConversationHandler.END


async def cancel_add_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel add service conversation."""
    await update.message.reply_text("Penambahan layanan dibatalkan.")
    context.user_data.pop('new_svc_name', None)
    context.user_data.pop('new_svc_category', None)
    return ConversationHandler.END


add_service_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_service_start, pattern=f"^{CB_CONFIG_ADD_SERVICE}$")],
    states={
        GET_SVC_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_get_name)],
        GET_SVC_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_get_category)],
        GET_SVC_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_service_get_price)],
    },
    fallbacks=[CommandHandler('cancel', cancel_add_service)],
)


# ------------------------------------------------------------------
# ConversationHandler — Edit Service Price
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def edit_service_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit service price conversation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    service_id = data.replace(f"{CB_CONFIG_EDIT_SERVICE}_", "")
    service_data = ALL_SERVICES.get(service_id)

    if not service_data:
        await query.message.reply_text("❌ Layanan tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['edit_svc_id'] = service_id
    await query.message.reply_text(
        f"✏️ Edit harga: {service_data['name']}\n"
        f"Harga saat ini: Rp {service_data['price']:,}\n\n"
        f"Masukkan harga baru (angka saja):\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return GET_NEW_PRICE


@handle_errors
async def edit_service_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new price and update."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    try:
        new_price = int(text)
    except ValueError:
        await update.message.reply_text("❌ Harga harus angka. Coba lagi:")
        return GET_NEW_PRICE

    service_id = context.user_data.get('edit_svc_id')
    config_service = context.bot_data.get('config_service')

    if config_service.update_service_price(service_id, new_price):
        service_data = ALL_SERVICES.get(service_id, {})
        await update.message.reply_text(
            f"✅ Harga berhasil diperbarui!\n\n"
            f"Layanan: {service_data.get('name', service_id)}\n"
            f"Harga baru: Rp {new_price:,}"
        )
    else:
        await update.message.reply_text("❌ Gagal memperbarui harga.")

    context.user_data.pop('edit_svc_id', None)
    return ConversationHandler.END


async def cancel_edit_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel edit service conversation."""
    await update.message.reply_text("Edit layanan dibatalkan.")
    context.user_data.pop('edit_svc_id', None)
    return ConversationHandler.END


edit_service_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_service_start, pattern=f"^{CB_CONFIG_EDIT_SERVICE}_")],
    states={
        GET_NEW_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_service_get_price)],
    },
    fallbacks=[CommandHandler('cancel', cancel_edit_service)],
)


# ------------------------------------------------------------------
# ConversationHandler — Edit Branch Cost
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def edit_branch_cost_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit branch cost conversation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    # Format: config_ebc_<branch_id>_<cost_key>
    rest = data.replace(f"{CB_CONFIG_EDIT_BRANCH_COST}_", "")
    parts = rest.split("_", 1)
    if len(parts) < 2:
        await query.message.reply_text("❌ Data tidak valid.")
        return ConversationHandler.END

    branch_id = parts[0]
    cost_key = parts[1]
    branch_data = BRANCHES.get(branch_id)

    if not branch_data:
        await query.message.reply_text("❌ Cabang tidak ditemukan.")
        return ConversationHandler.END

    current_value = branch_data.get('operational_cost', {}).get(cost_key, 0)
    context.user_data['edit_branch_id'] = branch_id
    context.user_data['edit_cost_key'] = cost_key

    await query.message.reply_text(
        f"✏️ Edit biaya: {branch_data['name']}\n"
        f"Item: {cost_key}\n"
        f"Nilai saat ini: Rp {int(current_value):,}\n\n"
        f"Masukkan nilai baru (angka saja):\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return GET_NEW_COST_VALUE


@handle_errors
async def edit_branch_cost_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new cost value and update."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    try:
        new_value = int(text)
    except ValueError:
        await update.message.reply_text("❌ Nilai harus angka. Coba lagi:")
        return GET_NEW_COST_VALUE

    branch_id = context.user_data.get('edit_branch_id')
    cost_key = context.user_data.get('edit_cost_key')
    config_service = context.bot_data.get('config_service')

    if config_service.update_branch_cost(branch_id, cost_key, new_value):
        branch_data = BRANCHES.get(branch_id, {})
        await update.message.reply_text(
            f"✅ Biaya berhasil diperbarui!\n\n"
            f"Cabang: {branch_data.get('name', branch_id)}\n"
            f"Item: {cost_key}\n"
            f"Nilai baru: Rp {new_value:,}"
        )
    else:
        await update.message.reply_text("❌ Gagal memperbarui biaya.")

    context.user_data.pop('edit_branch_id', None)
    context.user_data.pop('edit_cost_key', None)
    return ConversationHandler.END


async def cancel_edit_branch_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel edit branch cost conversation."""
    await update.message.reply_text("Edit biaya dibatalkan.")
    context.user_data.pop('edit_branch_id', None)
    context.user_data.pop('edit_cost_key', None)
    return ConversationHandler.END


edit_branch_cost_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_branch_cost_start, pattern=f"^{CB_CONFIG_EDIT_BRANCH_COST}_")],
    states={
        GET_NEW_COST_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_branch_cost_value)],
    },
    fallbacks=[CommandHandler('cancel', cancel_edit_branch_cost)],
)


# ------------------------------------------------------------------
# ConversationHandler — Edit Branch Commission
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def edit_branch_commission_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit branch commission conversation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    branch_id = data.replace(f"{CB_CONFIG_EDIT_BRANCH_COMMISSION}_", "")
    branch_data = BRANCHES.get(branch_id)

    if not branch_data:
        await query.message.reply_text("❌ Cabang tidak ditemukan.")
        return ConversationHandler.END

    current_rate = branch_data.get('commission_rate', 0)
    context.user_data['edit_commission_branch_id'] = branch_id

    await query.message.reply_text(
        f"✏️ Edit komisi: {branch_data['name']}\n"
        f"Rate saat ini: {current_rate * 100:.0f}%\n\n"
        f"Masukkan rate baru dalam persen (contoh: 50 untuk 50%):\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return GET_NEW_COMMISSION


@handle_errors
async def edit_branch_commission_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new commission rate and update."""
    text = update.message.text.strip().replace('%', '').replace(',', '.')
    try:
        rate_pct = float(text)
    except ValueError:
        await update.message.reply_text("❌ Rate harus angka (contoh: 50 untuk 50%). Coba lagi:")
        return GET_NEW_COMMISSION

    rate = rate_pct / 100.0
    branch_id = context.user_data.get('edit_commission_branch_id')
    config_service = context.bot_data.get('config_service')

    if config_service.update_branch_commission(branch_id, rate):
        branch_data = BRANCHES.get(branch_id, {})
        await update.message.reply_text(
            f"✅ Komisi berhasil diperbarui!\n\n"
            f"Cabang: {branch_data.get('name', branch_id)}\n"
            f"Rate baru: {rate_pct:.0f}%"
        )
    else:
        await update.message.reply_text("❌ Gagal memperbarui komisi.")

    context.user_data.pop('edit_commission_branch_id', None)
    return ConversationHandler.END


async def cancel_edit_commission(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel edit commission conversation."""
    await update.message.reply_text("Edit komisi dibatalkan.")
    context.user_data.pop('edit_commission_branch_id', None)
    return ConversationHandler.END


edit_branch_commission_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_branch_commission_start, pattern=f"^{CB_CONFIG_EDIT_BRANCH_COMMISSION}_")],
    states={
        GET_NEW_COMMISSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_branch_commission_value)],
    },
    fallbacks=[CommandHandler('cancel', cancel_edit_commission)],
)


# ==================================================================
# PRODUCT CONFIG CRUD (Owner)
# ==================================================================

@handle_errors
@log_command
@require_owner
async def config_products_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products config menu."""
    await update.callback_query.edit_message_text(
        text=MSG_CONFIG_PRODUCTS_MENU,
        reply_markup=KeyboardBuilder.config_products_menu()
    )


@handle_errors
@log_command
@require_owner
async def config_list_products_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all products with edit/delete buttons."""
    query = update.callback_query
    await query.answer()

    text = "🧴 Daftar Produk\n\n"
    if PRODUCTS:
        for pid, data in PRODUCTS.items():
            text += f"  - {data['name']}: Rp {data['price']:,}\n"
    else:
        text += "Belum ada produk terdaftar.\n"
    text += "\nKlik ✏️ untuk edit harga, 🗑️ untuk hapus."

    keyboard = KeyboardBuilder.config_product_list(PRODUCTS)
    try:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception:
        pass


# --- Remove Product (prefix callbacks) ---

async def handle_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Show confirmation before removing a product."""
    query = update.callback_query
    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    product_id = data.replace(f"{CB_CONFIG_REMOVE_PRODUCT}_", "")
    product_data = PRODUCTS.get(product_id)
    if not product_data:
        await query.answer("❌ Produk tidak ditemukan", show_alert=True)
        return

    await query.answer()
    keyboard = KeyboardBuilder.confirm_remove_product(product_id, product_data['name'])
    await query.edit_message_text(
        f"⚠️ Yakin ingin menghapus produk **{product_data['name']}** (Rp {product_data['price']:,})?",
        reply_markup=keyboard
    )


async def handle_confirm_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Actually remove product after confirmation."""
    query = update.callback_query
    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    product_id = data.replace(f"{CB_CONFIG_CONFIRM_RM_PRD}_", "")
    config_service = context.bot_data.get('config_service')

    product_data = PRODUCTS.get(product_id)
    product_name = product_data['name'] if product_data else product_id

    if config_service.remove_product(product_id):
        await query.answer(f"✅ Produk '{product_name}' dihapus.")
        await config_list_products_handler(update, context)
    else:
        await query.answer("❌ Gagal menghapus produk.", show_alert=True)


# ------------------------------------------------------------------
# ConversationHandler — Add Product
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start add product conversation."""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "✍️ Masukkan nama produk baru:\n\n💡 Ketik /cancel untuk membatalkan."
    )
    return GET_PRD_NAME


@handle_errors
async def add_product_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get product name, ask for price."""
    context.user_data['new_prd_name'] = update.message.text.strip()
    await update.message.reply_text("💰 Masukkan harga produk (angka saja, contoh: 55000):")
    return GET_PRD_PRICE


@handle_errors
async def add_product_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get price, save product."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    try:
        price = int(text)
    except ValueError:
        await update.message.reply_text("❌ Harga harus angka. Coba lagi:")
        return GET_PRD_PRICE

    name = context.user_data.get('new_prd_name')
    config_service = context.bot_data.get('config_service')

    if config_service.add_product(name, price):
        await update.message.reply_text(
            f"✅ Produk berhasil ditambahkan!\n\n"
            f"Nama: {name}\n"
            f"Harga: Rp {price:,}"
        )
    else:
        await update.message.reply_text("❌ Gagal menambahkan produk. Silakan coba lagi.")

    context.user_data.pop('new_prd_name', None)
    return ConversationHandler.END


async def cancel_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel add product conversation."""
    await update.message.reply_text("Penambahan produk dibatalkan.")
    context.user_data.pop('new_prd_name', None)
    return ConversationHandler.END


add_product_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_product_start, pattern=f"^{CB_CONFIG_ADD_PRODUCT}$")],
    states={
        GET_PRD_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_get_name)],
        GET_PRD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_get_price)],
    },
    fallbacks=[CommandHandler('cancel', cancel_add_product)],
)


# ------------------------------------------------------------------
# ConversationHandler — Edit Product Price
# ------------------------------------------------------------------

@handle_errors
@require_owner
async def edit_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit product price conversation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    product_id = data.replace(f"{CB_CONFIG_EDIT_PRODUCT}_", "")
    product_data = PRODUCTS.get(product_id)

    if not product_data:
        await query.message.reply_text("❌ Produk tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['edit_prd_id'] = product_id
    await query.message.reply_text(
        f"✏️ Edit harga: {product_data['name']}\n"
        f"Harga saat ini: Rp {product_data['price']:,}\n\n"
        f"Masukkan harga baru (angka saja):\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return GET_NEW_PRD_PRICE


@handle_errors
async def edit_product_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new price and update."""
    text = update.message.text.strip().replace('.', '').replace(',', '')
    try:
        new_price = int(text)
    except ValueError:
        await update.message.reply_text("❌ Harga harus angka. Coba lagi:")
        return GET_NEW_PRD_PRICE

    product_id = context.user_data.get('edit_prd_id')
    config_service = context.bot_data.get('config_service')

    if config_service.update_product_price(product_id, new_price):
        product_data = PRODUCTS.get(product_id, {})
        await update.message.reply_text(
            f"✅ Harga produk berhasil diperbarui!\n\n"
            f"Produk: {product_data.get('name', product_id)}\n"
            f"Harga baru: Rp {new_price:,}"
        )
    else:
        await update.message.reply_text("❌ Gagal memperbarui harga.")

    context.user_data.pop('edit_prd_id', None)
    return ConversationHandler.END


async def cancel_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel edit product conversation."""
    await update.message.reply_text("Edit produk dibatalkan.")
    context.user_data.pop('edit_prd_id', None)
    return ConversationHandler.END


edit_product_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_product_start, pattern=f"^{CB_CONFIG_EDIT_PRODUCT}_")],
    states={
        GET_NEW_PRD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_get_price)],
    },
    fallbacks=[CommandHandler('cancel', cancel_edit_product)],
)
