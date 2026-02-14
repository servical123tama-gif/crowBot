# app/handlers/query_handler.py
"""
Handles the conversation for Natural Language Queries.
Full RAG pipeline: PARSE (Gemini) -> RETRIEVE (ReportService) -> GENERATE (Gemini)
"""
import logging
from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    filters,
)
from telegram.constants import ParseMode

from app.services.query_parser_service import QueryParserService
from app.services.gemini_service import GeminiService
from app.utils.decorators import handle_errors, require_owner_or_admin

logger = logging.getLogger(__name__)

# Conversation states
ASKING_QUERY = 0


@handle_errors
@require_owner_or_admin
async def start_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the query conversation."""
    gemini_service: GeminiService = context.bot_data.get('gemini_service')
    mode = "AI (Gemini)" if gemini_service and gemini_service.is_available else "Keyword Matching"

    await update.message.reply_text(
        f"🧠 *Mode: {mode}*\n\n"
        "📝 Silakan ajukan pertanyaan Anda mengenai laporan keuangan.\n\n"
        "Contoh:\n"
        "• _Berapa pendapatan bulan ini?_\n"
        "• _Siapa capster terbaik minggu ini?_\n"
        "• _Bandingkan pendapatan antar cabang_\n"
        "• _Laporan profit bulan lalu_\n\n"
        "Ketik /batal untuk membatalkan.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ASKING_QUERY


@handle_errors
async def process_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's natural language query through RAG pipeline."""
    user_query = update.message.text

    # Send "thinking" message
    thinking_msg = await update.message.reply_text("🧠 Sedang memproses pertanyaan Anda...")

    # 1. PARSE — Extract intent from query
    parser_service: QueryParserService = context.bot_data['query_parser_service']
    query_result = await parser_service.parse_query(user_query)
    logger.info(f"Parsed query: {query_result}")

    if not query_result.is_valid():
        await thinking_msg.edit_text(
            "🤔 Maaf, saya tidak mengerti pertanyaan Anda.\n\n"
            "Coba tanyakan tentang:\n"
            "• Pendapatan/omzet\n"
            "• Ranking capster\n"
            "• Perbandingan cabang\n"
            "• Layanan terpopuler\n"
            "• Laporan profit"
        )
        return ConversationHandler.END

    # 2. RETRIEVE — Get data from ReportService
    try:
        report_service = context.bot_data['report_service']
        data_context = report_service.generate_report_from_query(query_result)
    except Exception as e:
        logger.error(f"Failed to retrieve data: {e}", exc_info=True)
        await thinking_msg.edit_text("❌ Terjadi kesalahan saat mengambil data. Silakan coba lagi.")
        return ConversationHandler.END

    if not data_context:
        timeframe = query_result.timeframe_str or 'bulan ini'
        await thinking_msg.edit_text(
            f"📭 Data tidak ditemukan untuk periode *{timeframe}*.\n\n"
            "Pastikan ada transaksi yang tercatat pada periode tersebut.",
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    # 3. GENERATE — Natural language response via Gemini
    gemini_service: GeminiService = context.bot_data.get('gemini_service')
    response = None

    if gemini_service and gemini_service.is_available:
        try:
            response = await gemini_service.generate_natural_response(
                user_query, data_context, query_result.report_type or 'general'
            )
        except Exception as e:
            logger.error(f"Gemini generate failed: {e}", exc_info=True)

    # Fallback: use raw data context if Gemini fails
    if not response:
        response = f"📊 Hasil untuk pertanyaan: \"{user_query}\"\n\n{data_context}"

    # Send response, handling Markdown errors
    try:
        await thinking_msg.edit_text(response, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        # Retry without parse_mode if Markdown fails
        try:
            await thinking_msg.edit_text(response)
        except Exception as e:
            logger.error(f"Failed to send response: {e}")
            await thinking_msg.edit_text("❌ Gagal menampilkan hasil. Silakan coba lagi.")

    return ConversationHandler.END


@handle_errors
async def cancel_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the query conversation."""
    await update.message.reply_text("👋 Percakapan dibatalkan.")
    return ConversationHandler.END


def get_query_handler() -> ConversationHandler:
    """Create and return the conversation handler for query feature."""
    return ConversationHandler(
        entry_points=[CommandHandler("tanya", start_query)],
        states={
            ASKING_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_query)],
        },
        fallbacks=[CommandHandler("batal", cancel_query)],
    )
