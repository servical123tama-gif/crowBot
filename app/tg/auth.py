"""Admin-only access control for Telegram bot."""
import os
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def _parse_ids(raw: str) -> set[int]:
    out = set()
    for token in (raw or '').split(','):
        token = token.strip()
        if token.isdigit():
            out.add(int(token))
    return out


def allowed_ids() -> set[int]:
    """Union of OWNER_IDS and ADMIN_IDS from env."""
    return _parse_ids(os.getenv('OWNER_IDS', '')) | _parse_ids(os.getenv('ADMIN_IDS', ''))


def owner_ids() -> set[int]:
    return _parse_ids(os.getenv('OWNER_IDS', ''))


def admin_only(handler):
    """Decorator — reject non-admin users with a polite message."""
    @wraps(handler)
    async def wrapper(update, context):
        user = update.effective_user
        uid = user.id if user else None
        if uid not in allowed_ids():
            logger.warning("Unauthorized access attempt: user_id=%s username=%s",
                           uid, user.username if user else None)
            if update.message:
                await update.message.reply_text(
                    "Akses ditolak. Bot ini khusus admin/owner."
                )
            elif update.callback_query:
                await update.callback_query.answer("Akses ditolak.", show_alert=True)
            return
        return await handler(update, context)
    return wrapper
