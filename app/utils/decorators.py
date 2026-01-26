"""
Custom Decorators
"""
import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.services.auth_service import AuthService
from app.config.constants import MSG_UNAUTHORIZED_FEATURE

logger = logging.getLogger(__name__)

def require_auth(func):
    """Decorator to check user authorization"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not AuthService.is_authorized(user_id):
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            
            if update.message:
                await update.message.reply_text(
                    f"⛔ Maaf, Anda tidak memiliki akses.\nUser ID: {user_id}"
                )
            elif update.callback_query:
                await update.callback_query.answer("⛔ Akses ditolak!", show_alert=True)
            
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def require_owner_or_admin(func):
    """Decorator to check if user is owner or admin"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        user_role = AuthService.get_user_role(user_id)
        
        if not AuthService.is_owner_or_admin(user_id):
            logger.warning(f"Unauthorized feature access by user {user_id} (role: {user_role})")
            
            if update.message:
                await update.message.reply_text(MSG_UNAUTHORIZED_FEATURE)
            elif update.callback_query:
                await update.callback_query.answer(
                    "⛔ Fitur ini hanya untuk Owner/Admin!",
                    show_alert=True
                )
            
            return
        
        logger.info(f"User {user_id} ({user_role}) accessing admin feature")
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def require_owner(func):
    """Decorator to check if user is owner (strictest)"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if not AuthService.is_owner(user_id):
            logger.warning(f"Owner-only feature access attempt by user {user_id}")
            
            if update.message:
                await update.message.reply_text("⛔ Fitur ini hanya untuk Owner!")
            elif update.callback_query:
                await update.callback_query.answer(
                    "⛔ Fitur ini hanya untuk Owner!",
                    show_alert=True
                )
            
            return
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def log_command(func):
    """Decorator to log command usage"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        command = update.message.text if update.message else 'callback'
        role = AuthService.get_user_role(user.id)
        
        logger.info(f"User {user.id} ({user.username}) [{role}] executed: {command}")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

def handle_errors(func):
    """Decorator to handle errors gracefully"""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            error_msg = "❌ Terjadi kesalahan. Silakan coba lagi atau hubungi admin."
            
            if update.message:
                await update.message.reply_text(error_msg)
            elif update.callback_query:
                await update.callback_query.answer(error_msg, show_alert=True)
    
    return wrapper