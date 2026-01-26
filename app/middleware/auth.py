"""
Authentication Middleware
"""
import logging
from typing import Callable
from telegram import Update
from telegram.ext import ContextTypes
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Authentication middleware for bot"""
    
    @staticmethod
    async def check_auth(
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        next_handler: Callable
    ):
        """Check if user is authorized before processing"""
        user_id = update.effective_user.id
        
        if not AuthService.is_authorized(user_id):
            logger.warning(f"Unauthorized access blocked: {user_id}")
            
            if update.message:
                await update.message.reply_text(
                    "⛔ Anda tidak memiliki akses ke bot ini."
                )
            elif update.callback_query:
                await update.callback_query.answer(
                    "⛔ Akses ditolak!",
                    show_alert=True
                )
            return
        
        # User authorized, continue
        await next_handler(update, context)