"""
Salary / Withdrawal Handler
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
    CB_SALARY_MENU, CB_SALARY_CAPSTER, CB_SALARY_WITHDRAW,
    CB_SALARY_HISTORY, CB_SALARY_PERIOD_WEEK, CB_SALARY_PERIOD_MONTH,
    MSG_SALARY_MENU, MONTHS_ID,
)

logger = logging.getLogger(__name__)

# Conversation states for withdrawal
GET_WITHDRAW_AMOUNT = 50
GET_WITHDRAW_NOTE = 51


@handle_errors
@log_command
@require_owner
async def salary_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show salary menu with capster list."""
    query = update.callback_query
    await query.answer()

    capster_service = context.bot_data.get('capster_service')
    capsters = capster_service.get_all_capsters()

    if not capsters:
        await query.edit_message_text("📭 Belum ada capster terdaftar.")
        return

    keyboard = KeyboardBuilder.salary_menu(capsters)
    await query.edit_message_text(text=MSG_SALARY_MENU, reply_markup=keyboard)


@handle_errors
@log_command
@require_owner
async def salary_capster_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str = None):
    """Show salary summary for a specific capster."""
    query = update.callback_query
    await query.answer()

    if data:
        tid_str = data.replace(f"{CB_SALARY_CAPSTER}_", "")
    else:
        tid_str = query.data.replace(f"{CB_SALARY_CAPSTER}_", "")

    try:
        telegram_id = int(tid_str)
    except ValueError:
        await query.edit_message_text("Data tidak valid.")
        return

    # Check if period is specified
    period = context.user_data.get('salary_period', 'week')

    capster_service = context.bot_data.get('capster_service')
    summary = capster_service.get_salary_summary(telegram_id, period=period)

    if not summary:
        await query.edit_message_text("Capster tidak ditemukan.")
        return

    capster = summary['capster']
    ps = summary['period_start']
    pe = summary['period_end']

    period_label = "Minggu ini" if period == 'week' else "Bulan ini"
    type_label = f"Mitra (Komisi {int(capster.commission_rate * 100)}%)" if capster.employment_type == 'mitra' else "Tetap"

    text = (
        f"💰 Gaji Capster: {capster.name}\n"
        f"Tipe: {type_label}\n\n"
        f"📅 Periode: {ps.strftime('%d %b')} - {pe.strftime('%d %b %Y')} ({period_label})\n"
        f"Transaksi: {summary['transaction_count']}\n"
        f"Total Omzet: Rp {summary['total_revenue']:,}\n"
    )

    if capster.employment_type == 'mitra':
        text += f"Komisi {int(capster.commission_rate * 100)}%: Rp {summary['commission_earned']:,}\n"
        period_withdrawn = summary.get('period_withdrawn', 0)
        if period_withdrawn > 0:
            text += f"Diambil periode ini: Rp {period_withdrawn:,}\n"

        text += (
            f"\n── Saldo Keseluruhan ──\n"
            f"Total Komisi ({ps.year}): Rp {summary['cumulative_commission']:,}\n"
            f"💵 Total Diambil: Rp {summary['total_withdrawn']:,}\n"
            f"💰 Saldo: Rp {summary['balance']:,}\n"
        )
    else:
        text += "\nℹ️ Capster tetap - gaji bulanan fixed.\n"

    if summary['last_withdrawal_date']:
        text += f"📋 Terakhir Ambil: {summary['last_withdrawal_date'].strftime('%d %b %Y')}\n"

    keyboard = KeyboardBuilder.salary_capster_detail(telegram_id, capster.employment_type, period)
    await query.edit_message_text(text=text, reply_markup=keyboard)


@handle_errors
@log_command
@require_owner
async def salary_period_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Switch period (week/month) and refresh detail."""
    query = update.callback_query

    if data.startswith(CB_SALARY_PERIOD_WEEK):
        context.user_data['salary_period'] = 'week'
        tid_str = data.replace(f"{CB_SALARY_PERIOD_WEEK}_", "")
    elif data.startswith(CB_SALARY_PERIOD_MONTH):
        context.user_data['salary_period'] = 'month'
        tid_str = data.replace(f"{CB_SALARY_PERIOD_MONTH}_", "")
    else:
        await query.answer("Unknown period")
        return

    # Re-render detail with new period
    fake_data = f"{CB_SALARY_CAPSTER}_{tid_str}"
    await salary_capster_detail(update, context, data=fake_data)


@handle_errors
@log_command
@require_owner
async def salary_history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    """Show withdrawal history for a capster."""
    query = update.callback_query
    await query.answer()

    tid_str = data.replace(f"{CB_SALARY_HISTORY}_", "")
    try:
        telegram_id = int(tid_str)
    except ValueError:
        await query.edit_message_text("Data tidak valid.")
        return

    capster_service = context.bot_data.get('capster_service')
    capster = capster_service._get_capster_by_tid(telegram_id)
    history = capster_service.get_withdrawal_history(telegram_id, limit=10)

    capster_name = capster.name if capster else "Unknown"

    if not history:
        text = f"📋 Riwayat Pengambilan: {capster_name}\n\nBelum ada riwayat pengambilan gaji."
    else:
        text = f"📋 Riwayat Pengambilan: {capster_name}\n\n"
        for i, rec in enumerate(history, 1):
            amount = int(float(rec.get('Amount', 0)))
            date_str = rec.get('Date', '')[:10]
            note = rec.get('Note', '')
            period_s = rec.get('PeriodStart', '')
            period_e = rec.get('PeriodEnd', '')
            text += f"{i}. {date_str} - Rp {amount:,}"
            if note:
                text += f" ({note})"
            text += f"\n   Periode: {period_s} s/d {period_e}\n"

    from app.config.constants import CB_BACK_MAIN
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Kembali", callback_data=f"{CB_SALARY_CAPSTER}_{telegram_id}")],
        [InlineKeyboardButton("🏠 Menu Utama", callback_data=CB_BACK_MAIN)],
    ])
    await query.edit_message_text(text=text, reply_markup=keyboard)


# --- Withdrawal ConversationHandler ---

@handle_errors
@require_owner
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start withdrawal conversation."""
    query = update.callback_query
    await query.answer()

    data = query.data
    tid_str = data.replace(f"{CB_SALARY_WITHDRAW}_", "")
    try:
        telegram_id = int(tid_str)
    except ValueError:
        await query.message.reply_text("Data tidak valid.")
        return ConversationHandler.END

    capster_service = context.bot_data.get('capster_service')
    summary = capster_service.get_salary_summary(telegram_id,
                                                  period=context.user_data.get('salary_period', 'week'))
    if not summary:
        await query.message.reply_text("Capster tidak ditemukan.")
        return ConversationHandler.END

    context.user_data['withdraw_tid'] = telegram_id
    context.user_data['withdraw_period_start'] = summary['period_start']
    context.user_data['withdraw_period_end'] = summary['period_end']
    context.user_data['withdraw_balance'] = summary['balance']

    await query.message.reply_text(
        f"💵 Catat Pengambilan Gaji: {summary['capster'].name}\n"
        f"Saldo saat ini: Rp {summary['balance']:,}\n\n"
        f"Masukkan jumlah pengambilan (angka saja):\n\n"
        f"💡 Ketik /cancel untuk membatalkan."
    )
    return GET_WITHDRAW_AMOUNT


@handle_errors
async def get_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get withdrawal amount."""
    text = update.message.text.strip().replace('.', '').replace(',', '')

    try:
        amount = int(text)
    except ValueError:
        await update.message.reply_text("❌ Masukkan angka yang valid.\nCoba lagi:")
        return GET_WITHDRAW_AMOUNT

    if amount <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0.\nCoba lagi:")
        return GET_WITHDRAW_AMOUNT

    context.user_data['withdraw_amount'] = amount
    await update.message.reply_text(
        "📝 Keterangan (opsional).\n"
        "Ketik /skip untuk lewati:"
    )
    return GET_WITHDRAW_NOTE


@handle_errors
async def get_withdraw_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get optional note and save withdrawal."""
    text = update.message.text.strip()
    note = '' if text.startswith('/skip') else text
    return await _save_withdrawal(update, context, note)


async def skip_withdraw_note(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip note."""
    return await _save_withdrawal(update, context, '')


async def _save_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, note: str) -> int:
    """Save the withdrawal record."""
    telegram_id = context.user_data.get('withdraw_tid')
    amount = context.user_data.get('withdraw_amount')
    period_start = context.user_data.get('withdraw_period_start')
    period_end = context.user_data.get('withdraw_period_end')
    old_balance = context.user_data.get('withdraw_balance', 0)

    capster_service = context.bot_data.get('capster_service')
    capster = capster_service._get_capster_by_tid(telegram_id)
    capster_name = capster.name if capster else "Unknown"

    success = capster_service.record_withdrawal(
        telegram_id, amount, period_start, period_end, note
    )

    if success:
        new_balance = old_balance - amount
        text = (
            f"✅ Pengambilan gaji berhasil dicatat!\n\n"
            f"Capster: {capster_name}\n"
            f"Jumlah: Rp {amount:,}\n"
        )
        if note:
            text += f"Keterangan: {note}\n"
        text += f"Sisa Saldo: Rp {new_balance:,}"
    else:
        text = "❌ Gagal mencatat pengambilan. Silakan coba lagi."

    await update.message.reply_text(text)

    # Cleanup
    for key in ['withdraw_tid', 'withdraw_amount', 'withdraw_period_start',
                'withdraw_period_end', 'withdraw_balance']:
        context.user_data.pop(key, None)

    return ConversationHandler.END


async def cancel_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel withdrawal conversation."""
    await update.message.reply_text("Pengambilan gaji dibatalkan.")
    for key in ['withdraw_tid', 'withdraw_amount', 'withdraw_period_start',
                'withdraw_period_end', 'withdraw_balance']:
        context.user_data.pop(key, None)
    return ConversationHandler.END


salary_withdraw_conv_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(withdraw_start, pattern=f"^{CB_SALARY_WITHDRAW}_")],
    states={
        GET_WITHDRAW_AMOUNT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_amount),
        ],
        GET_WITHDRAW_NOTE: [
            CommandHandler('skip', skip_withdraw_note),
            MessageHandler(filters.TEXT & ~filters.COMMAND, get_withdraw_note),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_withdraw)],
)
