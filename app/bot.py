"""
Main Bot Application
"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from app.config.settings import settings
from app.services.auth_service import AuthService
from app.services.sheets_service import SheetsService
from app.services.report_service import ReportService # Import ReportService
from app.handlers.start import start_handler
from app.handlers.callback import callback_router
from app.handlers.customer import add_customer_conv_handler

logger = logging.getLogger(__name__)

class BarbershopBot:
    """Main bot application"""
    
    def __init__(self):
        """Initialize bot"""
        # Validate settings
        settings.validate()
        
        # Initialize AuthService with roles
        AuthService.initialize(
            authorized_users=settings.AUTHORIZED_CAPSTERS,
            owner_ids=settings.OWNER_IDS,
            admin_ids=settings.ADMIN_IDS
        )
        
        # Create application
        self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        
        # Instantiate SheetsService once and store it in bot_data
        sheets_service_instance = SheetsService()
        self.app.bot_data['sheets_service'] = sheets_service_instance
        
        # Instantiate ReportService once, passing the SheetsService instance, and store it in bot_data
        self.app.bot_data['report_service'] = ReportService(sheets_service=sheets_service_instance)
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Bot initialized successfully")
    
    def _register_handlers(self):
        """Register all handlers"""
        self.app.add_handler(CommandHandler("start", start_handler))
        self.app.add_handler(add_customer_conv_handler)
        self.app.add_handler(CallbackQueryHandler(callback_router))
        
        logger.info("Handlers registered")
    
    def run(self):
        """Run bot"""
        logger.info("🤖 Bot is running...")
        logger.info(f"Bot name: {settings.BOT_NAME}")
        logger.info(f"Authorized users: {len(settings.AUTHORIZED_CAPSTERS)}")
        logger.info(f"Owners: {len(settings.OWNER_IDS)}")
        logger.info(f"Admins: {len(settings.ADMIN_IDS)}")
        
        self.app.run_polling(drop_pending_updates=True)
        
        '''
        rule add pyment : app/config/constants.py -> app/models/transaction.py -> 
                        app/utils/keyboards.py -> app/handlers/transaction.py -> 
                        app/handlers/callback.py -> app/services/sheets_service.py         
        '''