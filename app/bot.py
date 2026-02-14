"""
Main Bot Application
"""
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from app.config.settings import settings
from app.services.auth_service import AuthService
from app.services.sheets_service import SheetsService
from app.services.report_service import ReportService
from app.services.gemini_service import GeminiService
from app.services.query_parser_service import QueryParserService
from app.services.capster_service import CapsterService
from app.services.config_service import ConfigService
from app.handlers.start import start_handler
from app.handlers.callback import callback_router
from app.handlers.customer import add_customer_conv_handler
from app.handlers.capster import add_capster_conv_handler, edit_capster_conv_handler
from app.handlers.config_handler import (
    add_service_conv_handler, edit_service_conv_handler,
    edit_branch_cost_conv_handler, edit_branch_commission_conv_handler,
    add_product_conv_handler, edit_product_conv_handler,
)
from app.handlers.query_handler import get_query_handler
from app.handlers.scheduler import setup_scheduled_jobs


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

        # Instantiate services
        sheets_service_instance = SheetsService()

        # Load config from sheets BEFORE other services that read constants
        config_service_instance = ConfigService(sheets_service=sheets_service_instance)
        config_service_instance.load_all_config()

        report_service_instance = ReportService(sheets_service=sheets_service_instance)
        gemini_service_instance = GeminiService()

        capster_service_instance = CapsterService(sheets_service=sheets_service_instance)

        self.app.bot_data['sheets_service'] = sheets_service_instance
        self.app.bot_data['config_service'] = config_service_instance
        self.app.bot_data['report_service'] = report_service_instance
        self.app.bot_data['gemini_service'] = gemini_service_instance
        self.app.bot_data['capster_service'] = capster_service_instance

        # Merge capsters from Google Sheets into AuthService (on top of .env)
        capster_service_instance.load_capsters_to_auth()

        # Build capster name list: merge transaction names + CapsterList real names + aliases
        capster_list_from_transactions = report_service_instance.get_dynamic_capster_list()
        all_capster_objects = capster_service_instance.get_all_capsters()
        capster_list_from_sheets = []
        for c in all_capster_objects:
            capster_list_from_sheets.extend(c.all_names())  # includes alias
        # Combine & deduplicate (case-insensitive), preserving original casing
        seen_lower = set()
        capster_list = []
        for name in capster_list_from_transactions + capster_list_from_sheets:
            if name and name.lower() not in seen_lower:
                seen_lower.add(name.lower())
                capster_list.append(name)

        if not capster_list:
            logger.warning("No capsters found, /tanya entity matching may be limited")
        else:
            logger.info(f"Query parser capster list: {capster_list}")

        # Build alias map for query filtering: name -> [all known names]
        capster_alias_map = capster_service_instance.get_name_alias_map()
        logger.info(f"Capster alias map: {capster_alias_map}")

        # Inject alias map into ReportService for capster report filtering
        report_service_instance._capster_alias_map = capster_alias_map

        # Initialize query parser with Gemini service
        self.app.bot_data['query_parser_service'] = QueryParserService(
            capster_list=capster_list,
            gemini_service=gemini_service_instance,
            capster_alias_map=capster_alias_map
        )

        # Log Gemini status
        if gemini_service_instance.is_available:
            logger.info("Gemini AI is available - /tanya will use AI-powered parsing and response")
        else:
            logger.warning("Gemini AI is NOT available - /tanya will use keyword fallback")

        # Register handlers
        self._register_handlers()

        # Setup scheduled jobs (daily notification etc.)
        setup_scheduled_jobs(self.app)

        logger.info("Bot initialized successfully")

    def _register_handlers(self):
        """Register all handlers"""
        self.app.add_handler(CommandHandler("start", start_handler))
        self.app.add_handler(get_query_handler())
        self.app.add_handler(add_customer_conv_handler)
        self.app.add_handler(add_capster_conv_handler)
        self.app.add_handler(edit_capster_conv_handler)
        self.app.add_handler(add_service_conv_handler)
        self.app.add_handler(edit_service_conv_handler)
        self.app.add_handler(edit_branch_cost_conv_handler)
        self.app.add_handler(edit_branch_commission_conv_handler)
        self.app.add_handler(add_product_conv_handler)
        self.app.add_handler(edit_product_conv_handler)
        self.app.add_handler(CallbackQueryHandler(callback_router))

        logger.info("Handlers registered")

    def run(self):
        """Run bot"""
        logger.info("Bot is running...")
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
