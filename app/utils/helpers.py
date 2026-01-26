"""
Helper Functions
"""
import logging
from telegram import Update
from telegram.error import BadRequest

logger = logging.getLogger(__name__)

async def safe_edit_message(query, text: str, reply_markup=None, parse_mode=None):
    """
    Safely edit message, handling "message not modified" error
    
    Args:
        query: CallbackQuery object
        text: New message text
        reply_markup: Keyboard markup
        parse_mode: Parse mode (e.g., 'Markdown', 'HTML')
    
    Returns:
        bool: True if edited successfully, False if skipped
    """
    try:
        await query.edit_message_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
        
    except BadRequest as e:
        error_msg = str(e).lower()
        
        if "message is not modified" in error_msg:
            # Message sama, skip edit
            logger.debug("Message content unchanged, skipping edit")
            return False
            
        elif "message to edit not found" in error_msg:
            logger.warning("Message to edit not found")
            return False
            
        else:
            # Error lain, raise
            logger.error(f"Error editing message: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Unexpected error editing message: {e}")
        raise
    
    
def get_kapster_info(username):
    """
    Ambil info kapster dari username Telegram
    
    Args:
        username: Username Telegram (bisa dengan atau tanpa @)
        
    Returns:
        dict: Info kapster atau None jika tidak ditemukan
    """
    # Debug & validasi input
    if not username:
        print("DEBUG get_kapster_info: username is falsy:", username)
        return None

    if not isinstance(username, str):
        print("DEBUG get_kapster_info: username is not str, converting:", type(username))
        try:
            username = str(username)
        except Exception:
            return None

    # Normalisasi: hapus leading @, trim spasi, ubah ke lowercase
    username_clean = username.strip().lstrip("@").lower()

    print("DEBUG get_kapster_info: normalized username =", username_clean)

    return username_clean