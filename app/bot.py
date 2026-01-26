"""
Main Bot Application
"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from app.config.settings import settings
from app.services.auth_service import AuthService
from app.handlers.start import start_handler
from app.handlers.callback import callback_router

logger = logging.getLogger(__name__)

class BarbershopBot:
    """Main bot application"""
    
    def __init__(self):
        """Initialize bot"""
        # Validate settings
        settings.validate()
        
        # Initialize AuthService with roles
        AuthService.initialize(
            authorized_users=settings.AUTHORIZED_CASTERS,
            owner_ids=settings.OWNER_IDS,
            admin_ids=settings.ADMIN_IDS
        )
        
        # Create application
        self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Bot initialized successfully")
    
    def _register_handlers(self):
        """Register all handlers"""
        self.app.add_handler(CommandHandler("start", start_handler))
        self.app.add_handler(CallbackQueryHandler(callback_router))
        
        logger.info("Handlers registered")
    
    def run(self):
        """Run bot"""
        logger.info("🤖 Bot is running...")
        logger.info(f"Bot name: {settings.BOT_NAME}")
        logger.info(f"Authorized users: {len(settings.AUTHORIZED_CASTERS)}")
        logger.info(f"Owners: {len(settings.OWNER_IDS)}")
        logger.info(f"Admins: {len(settings.ADMIN_IDS)}")
        
        self.app.run_polling(drop_pending_updates=True)
        
        '''
        rule add pyment : app/config/constants.py -> app/models/transaction.py -> 
                        app/utils/keyboards.py -> app/handlers/transaction.py -> 
                        app/handlers/callback.py -> app/services/sheets_service.py         
        '''