"""
Capster Management Handler
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
    CB_ADD_CAPSTER,
    CB_REMOVE_CAPSTER,
    CB_CONFIRM_REMOVE_CAPSTER,
    CB_EDIT_CAPSTER,
    MSG_CAPSTER_MENU,
    MSG_ADD_CAPSTER_NAME,
    MSG_ADD_CAPSTER_ID,
    MSG_ADD_CAPSTER_ALIAS,
    MSG_CAPSTER_ADDED,
    MSG_CAPSTER_REMOVED,
    MSG_CAPSTER_LIST_HEADER,
    MSG_CAPSTER_LIST_EMPTY,
    MSG_EDIT_CAPSTER_NAME,
    MSG_EDIT_CAPSTER_ALIAS,
    MSG_CAPSTER_UPDATED,
)

logger = logging.getLogger(__name__)

# Conversation states - Add capster
GET_CAPSTER_NAME, GET_CAPSTER_TELEGRAM_ID, GET_CAPSTER_ALIAS = range(3)
# Conversation states - Edit capster
EDIT_CAPSTER_NAME, EDIT_CAPSTER_ALIAS = range(10, 12)


@handle_errors
@log_command
@require_owner
async def capster_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show capster management menu."""
    keyboard = KeyboardBuilder.capster_menu()
    await update.callback_query.edit_message_text(
        text=MSG_CAPSTER_MENU,
        reply_markup=keyboard
    )


@handle_errors
@log_command
@require_owner
async def list_capsters_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all capsters from sheets."""
    query = update.callback_query
    await query.answer()

    capster_service = context.bot_data.get('capster_service')
    capsters = capster_service.get_all_capsters()

    if not capsters:
        text = MSG_CAPSTER_LIST_EMPTY
        keyboard = KeyboardBuilder.capster_menu()
    else:
        text = f"{MSG_CAPSTER_LIST_HEADER}\n\n"
        for i, c in enumerate(capsters, 1):
            alias_part = f" (alias: {c.alias})" if c.alias else ""
            text += f"{i}. {c.name}{alias_part} - ID: {c.telegram_id}\n"
        text += "\n✏️ Klik nama untuk edit | 🗑️ Klik ikon untuk hapus"
        keyboard = KeyboardBuilder.capster_list_keyboard(capsters)

    try:
        await query.edit_message_text(text=text, reply_markup=keyboard)
    except Exception:
        # Message content identical — ignore
        pass


@handle_errors
@log_command
@require_owner
async def add_capster_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start add capster conversation."""
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(MSG_ADD_CAPSTER_NAME)
    return GET_CAPSTER_NAME


@handle_errors
async def get_capster_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get capster name and ask for Telegram ID."""
    context.user_data['capster_name'] = update.message.text.strip()
    await update.message.reply_text(MSG_ADD_CAPSTER_ID)
    return GET_CAPSTER_TELEGRAM_ID


@handle_errors
async def get_capster_telegram_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get Telegram ID and ask for alias."""
    text = update.message.text.strip()

    try:
        telegram_id = int(text)
    except ValueError:
        await update.message.reply_text("❌ ID tidak valid. Masukkan angka Telegram User ID.\nCoba lagi:")
        return GET_CAPSTER_TELEGRAM_ID

    # Check duplicate
    capster_service = context.bot_data.get('capster_service')
    existing = capster_service.get_all_capsters()
    for c in existing:
        if c.telegram_id == telegram_id:
            await update.message.reply_text(
                f"⚠️ Telegram ID {telegram_id} sudah terdaftar sebagai '{c.name}'.\n"
                "Gunakan fitur Edit untuk mengubah data, atau masukkan ID lain:"
            )
            return GET_CAPSTER_TELEGRAM_ID

    context.user_data['capster_telegram_id'] = telegram_id
    await update.message.reply_text(MSG_ADD_CAPSTER_ALIAS)
    return GET_CAPSTER_ALIAS


@handle_errors
async def get_capster_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get alias (Telegram name) and save capster."""
    text = update.message.text.strip()
    alias = '' if text.startswith('/skip') else text

    capster_name = context.user_data.get('capster_name')
    telegram_id = context.user_data.get('capster_telegram_id')
    capster_service = context.bot_data.get('capster_service')

    if capster_service.add_capster(capster_name, telegram_id, alias=alias):
        # Update query parser so /tanya recognizes the new name + alias
        query_parser = context.bot_data.get('query_parser_service')
        if query_parser:
            current = query_parser._capster_list
            new_names = [n for n in [capster_name, alias] if n and n not in current]
            if new_names:
                query_parser.update_capster_list(current + new_names)

        alias_info = f" (alias: {alias})" if alias else ""
        await update.message.reply_text(
            MSG_CAPSTER_ADDED.format(name=capster_name, telegram_id=telegram_id) + alias_info
        )
    else:
        await update.message.reply_text("❌ Gagal menambahkan capster. Silakan coba lagi.")

    context.user_data.pop('capster_name', None)
    context.user_data.pop('capster_telegram_id', None)
    return ConversationHandler.END


async def skip_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip alias and save capster without alias."""
    context.user_data['_skip_alias'] = True
    # Reuse get_capster_alias with /skip text
    update.message.text = '/skip'
    return await get_capster_alias(update, context)


async def cancel_capster(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel add capster conversation."""
    await update.message.reply_text("Penambahan capster dibatalkan.")
    context.user_data.pop('capster_name', None)
    return ConversationHandler.END


add_capster_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(add_capster_start, pattern=f"^{CB_ADD_CAPSTER}$")],
    states={
        GET_CAPSTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_capster_name)],
        GET_CAPSTER_TELEGRAM_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_capster_telegram_id)],
        GET_CAPSTER_ALIAS: [
            CommandHandler('skip', skip_alias),
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_capster_alias),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_capster)],
)


# --- Edit Capster ConversationHandler ---

@handle_errors
@require_owner
async def edit_capster_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start edit capster conversation from callback."""
    query = update.callback_query
    await query.answer()

    data = query.data
    try:
        telegram_id = int(data.replace(f"{CB_EDIT_CAPSTER}_", ""))
    except ValueError:
        await query.message.reply_text("❌ Data tidak valid.")
        return ConversationHandler.END

    capster_service = context.bot_data.get('capster_service')
    capsters = capster_service.get_all_capsters()
    target = None
    for c in capsters:
        if c.telegram_id == telegram_id:
            target = c
            break

    if not target:
        await query.message.reply_text("❌ Capster tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['edit_capster_id'] = telegram_id
    context.user_data['edit_capster_old'] = {'name': target.name, 'alias': target.alias}

    await query.message.reply_text(
        f"✏️ Edit capster: **{target.name}** (ID: {telegram_id})\n"
        f"Alias saat ini: {target.alias or '-'}\n\n"
        f"{MSG_EDIT_CAPSTER_NAME}\n\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return EDIT_CAPSTER_NAME


@handle_errors
async def edit_capster_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new name for capster."""
    text = update.message.text.strip()
    if text.startswith('/skip'):
        context.user_data['edit_new_name'] = None
    else:
        context.user_data['edit_new_name'] = text
    await update.message.reply_text(MSG_EDIT_CAPSTER_ALIAS)
    return EDIT_CAPSTER_ALIAS


@handle_errors
async def edit_capster_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get new alias and save updates."""
    text = update.message.text.strip()
    new_alias = None if text.startswith('/skip') else text

    telegram_id = context.user_data.get('edit_capster_id')
    new_name = context.user_data.get('edit_new_name')
    capster_service = context.bot_data.get('capster_service')

    if new_name is None and new_alias is None:
        await update.message.reply_text("Tidak ada perubahan.")
    elif capster_service.update_capster(telegram_id, name=new_name, alias=new_alias):
        # Update query parser
        query_parser = context.bot_data.get('query_parser_service')
        if query_parser:
            current = query_parser._capster_list
            new_names = [n for n in [new_name, new_alias] if n and n not in current]
            if new_names:
                query_parser.update_capster_list(current + new_names)

        old = context.user_data.get('edit_capster_old', {})
        parts = []
        if new_name:
            parts.append(f"Nama: {old.get('name')} → {new_name}")
        if new_alias:
            parts.append(f"Alias: {old.get('alias') or '-'} → {new_alias}")
        await update.message.reply_text(f"{MSG_CAPSTER_UPDATED}\n\n" + "\n".join(parts))
    else:
        await update.message.reply_text("❌ Gagal memperbarui capster.")

    context.user_data.pop('edit_capster_id', None)
    context.user_data.pop('edit_new_name', None)
    context.user_data.pop('edit_capster_old', None)
    return ConversationHandler.END


async def skip_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip name edit."""
    context.user_data['edit_new_name'] = None
    await update.message.reply_text(MSG_EDIT_CAPSTER_ALIAS)
    return EDIT_CAPSTER_ALIAS


async def skip_edit_alias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip alias edit and save."""
    update.message.text = '/skip'
    return await edit_capster_alias(update, context)


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel edit conversation."""
    await update.message.reply_text("Edit capster dibatalkan.")
    context.user_data.pop('edit_capster_id', None)
    context.user_data.pop('edit_new_name', None)
    context.user_data.pop('edit_capster_old', None)
    return ConversationHandler.END


edit_capster_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(edit_capster_start, pattern=f"^{CB_EDIT_CAPSTER}_")],
    states={
        EDIT_CAPSTER_NAME: [
            CommandHandler('skip', skip_edit_name),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_capster_name),
        ],
        EDIT_CAPSTER_ALIAS: [
            CommandHandler('skip', skip_edit_alias),
            MessageHandler(filters.TEXT & ~filters.COMMAND, edit_capster_alias),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_edit)],
)


@handle_errors
@log_command
@require_owner
async def handle_migrate_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Migrate old transaction capster names (alias → real name)."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⏳ Memproses migrasi nama capster di transaksi lama...")

    capster_service = context.bot_data.get('capster_service')
    results = capster_service.migrate_old_transaction_names()

    if not results:
        text = "ℹ️ Tidak ada transaksi yang perlu dimigrasi.\n\nPastikan kolom Alias di CapsterList sudah terisi."
    else:
        text = "✅ Migrasi selesai!\n\n"
        total = 0
        for sheet_name, count in results.items():
            text += f"📄 {sheet_name}: {count} transaksi diperbarui\n"
            total += count
        text += f"\nTotal: {total} transaksi"

    keyboard = KeyboardBuilder.capster_menu()
    await query.edit_message_text(text, reply_markup=keyboard)


async def handle_remove_capster(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Show confirmation before removing a capster."""
    query = update.callback_query

    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    try:
        telegram_id = int(data.replace(f"{CB_REMOVE_CAPSTER}_", ""))
    except ValueError:
        await query.answer("❌ Data tidak valid", show_alert=True)
        return

    capster_service = context.bot_data.get('capster_service')
    capsters = capster_service.get_all_capsters()
    capster_name = "Unknown"
    for c in capsters:
        if c.telegram_id == telegram_id:
            capster_name = c.name
            break

    await query.answer()
    keyboard = KeyboardBuilder.confirm_remove_capster(telegram_id, capster_name)
    await query.edit_message_text(
        f"⚠️ Yakin ingin menghapus capster **{capster_name}** (ID: {telegram_id})?\n\n"
        "Capster ini tidak akan bisa mengakses bot lagi.",
        reply_markup=keyboard
    )


async def handle_confirm_remove_capster(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Actually remove capster after confirmation."""
    query = update.callback_query

    from app.services.auth_service import AuthService
    if not AuthService.is_owner(update.effective_user.id):
        await query.answer("⛔ Fitur ini hanya untuk Owner!", show_alert=True)
        return

    try:
        telegram_id = int(data.replace(f"{CB_CONFIRM_REMOVE_CAPSTER}_", ""))
    except ValueError:
        await query.answer("❌ Data tidak valid", show_alert=True)
        return

    capster_service = context.bot_data.get('capster_service')
    capsters = capster_service.get_all_capsters()
    capster_name = "Unknown"
    for c in capsters:
        if c.telegram_id == telegram_id:
            capster_name = c.name
            break

    if capster_service.remove_capster(telegram_id):
        await query.answer(MSG_CAPSTER_REMOVED.format(name=capster_name))
        await list_capsters_handler(update, context)
    else:
        await query.answer("❌ Gagal menghapus capster.", show_alert=True)
