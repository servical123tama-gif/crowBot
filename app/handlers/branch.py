"""
Branch Handlers
"""
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from app.utils.decorators import require_auth, handle_errors
from app.utils.keyboards import KeyboardBuilder
from app.services.branch_service import BranchService
from app.config.constants import BRANCHES, MSG_SELECT_BRANCH, MSG_BRANCH_CHANGED, MSG_CURRENT_BRANCH

logger = logging.getLogger(__name__)

@handle_errors
@require_auth
async def show_branch_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, is_first_time: bool = True):
    """Show branch selection menu"""
    user = update.effective_user
    
    message = MSG_SELECT_BRANCH.format(capster=user.first_name)
    keyboard = KeyboardBuilder.branch_menu()
    
    if update.message:
        await update.message.reply_text(message, reply_markup=keyboard)
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(message, reply_markup=keyboard)
    
    logger.info(f"Showed branch selection to user {user.id}")

@handle_errors
@require_auth
async def handle_branch_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, branch_id: str):
    """Handle branch selection"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    capster_name = query.from_user.first_name
    
    # Validate branch
    if branch_id not in BRANCHES:
        await query.edit_message_text("❌ Cabang tidak valid")
        return
    
    # Set branch for today
    BranchService.set_branch(user_id, branch_id)
    
    branch_data = BRANCHES[branch_id]
    branch_name = branch_data['short']
    today = datetime.now().strftime('%d %B %Y')
    
    message = MSG_BRANCH_CHANGED.format(
        branch=branch_name,
        date=today
    )
    
    keyboard = KeyboardBuilder.back_button()
    
    await query.edit_message_text(message, reply_markup=keyboard)
    logger.info(f"User {user_id} set branch to {branch_id}")

@handle_errors
@require_auth
async def handle_change_branch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle request to change branch"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    capster_name = query.from_user.first_name
    
    # Get current branch
    current_branch_id = BranchService.get_branch(user_id)
    
    if current_branch_id:
        branch_name = BRANCHES[current_branch_id]['short']
        today = datetime.now().strftime('%d %B %Y')
        
        message = MSG_CURRENT_BRANCH.format(
            branch=branch_name,
            date=today,
            capster=capster_name
        )
    else:
        message = "🏢 Anda belum memilih cabang hari ini.\n\nSilakan pilih cabang:"
    
    keyboard = KeyboardBuilder.branch_menu()
    
    await query.edit_message_text(message, reply_markup=keyboard)
    logger.info(f"User {user_id} requested to change branch")