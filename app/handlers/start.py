"""
Start Command Handler
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.utils.decorators import require_auth, log_command, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.config.constants import MSG_WELCOME
from app.config.settings import settings
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

@handle_errors
@log_command
@require_auth
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_role = AuthService.get_user_role(user.id)
    
    # Welcome text dengan role badge
    role_badge = ""
    if AuthService.is_owner(user.id):
        role_badge = " 👑 (Owner)"
    elif AuthService.is_admin(user.id):
        role_badge = " 🔑 (Admin)"
    
    welcome_text = MSG_WELCOME.format(bot_name=settings.BOT_NAME, username=user.first_name)
    welcome_text += role_badge
    
    # Dynamic keyboard based on role
    keyboard = KeyboardBuilder.main_menu(user_id=user.id)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard
    )
    
    logger.info(f"User {user.id} [{user_role}] started bot")