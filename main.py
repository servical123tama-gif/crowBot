"""
Barbershop Bot - Main Entry Point
"""
import logging
import os
import sys
import argparse

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def setup_logging(level: str):
    """Configures the logging for the application."""
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=level.upper(),
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def validate_environment():
    """Validates the local development environment before starting."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("🔍 Validating development environment...")
    logger.info("=" * 60)
    
    if not os.path.exists('.env'):
        logger.error("❌ .env file not found! Copy .env.example to .env and configure it.")
        return False
    logger.info("✅ .env file found")
    
    if not os.path.exists('credentials.json'):
        logger.error("❌ credentials.json not found! Download it from your Google Cloud Console.")
        return False
    logger.info("✅ credentials.json found")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'GOOGLE_SHEET_ID', 'AUTHORIZED_CAPSTERS', 'OWNER_IDS']
    optional_vars = ['GEMINI_API_KEY']
    all_vars_valid = True

    logger.info("📋 Checking required .env variables:")
    for var in required_vars:
        value = os.getenv(var, '')
        if value:
            logger.info(f"   - {var}: ✅ Set")
        else:
            logger.error(f"   - {var}: ❌ Empty or not set!")
            all_vars_valid = False

    logger.info("📋 Checking optional .env variables:")
    for var in optional_vars:
        value = os.getenv(var, '')
        if value:
            logger.info(f"   - {var}: ✅ Set")
        else:
            logger.warning(f"   - {var}: ⚠️ Not set (feature /tanya will use fallback mode)")

    if not all_vars_valid:
        logger.error("❌ One or more required environment variables are missing.")
        return False
    
    logger.info("✅ All required environment variables are configured.")
    return True

def main(dev_mode: bool = False):
    """
    Main entry point for the Barbershop Bot.
    
    :param dev_mode: If True, runs in development mode with detailed validation.
                     If False, runs in production mode (e.g., for Render.com).
    """
    log_level = 'DEBUG' if dev_mode else 'INFO'
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    mode_message = "LOCAL DEVELOPMENT" if dev_mode else "PRODUCTION"
    logger.info("=" * 60)
    logger.info(f"🚀 Starting Barbershop Bot in {mode_message} mode...")
    logger.info("=" * 60)

    try:
        if dev_mode:
            # For local runs, perform detailed validation first.
            if not validate_environment():
                logger.error("❌ Environment validation failed! Please fix the errors above.")
                input("\nPress Enter to exit...")
                return
        else:
            # In production (e.g., Render), start the health check server.
            logger.info("Starting health check web server for production...")
            from app.web_server import keep_alive
            keep_alive()
            logger.info("✅ Health check server is running.")

        logger.info("📦 Importing bot modules...")
        from app.bot import BarbershopBot
        from app.config.settings import settings
        logger.info("✅ Modules imported.")

        logger.info("⚙️ Validating application settings...")
        settings.validate()
        logger.info("✅ Settings validated.")

        logger.info("🤖 Initializing bot...")
        bot = BarbershopBot()
        logger.info("✅ Bot initialized successfully!")
        logger.info(f"   - Bot Name: {settings.BOT_NAME}")
        logger.info(f"   - Authorized Users: {len(settings.AUTHORIZED_CAPSTERS)}")
        logger.info(f"   - Admins: {len(settings.ADMIN_IDS)}")
        logger.info(f"   - Owners: {len(settings.OWNER_IDS)}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🔄 Bot is now running! Press Ctrl+C to stop.")
        logger.info("=" * 60)
        
        bot.run()

    except (ValueError, FileNotFoundError) as e:
        logger.error("=" * 60)
        logger.error(f"❌ Configuration Error: {e}")
        logger.error("=" * 60)
        logger.info("\n💡 Please check your .env and credentials.json files.")
        if dev_mode:
            input("\nPress Enter to exit...")
            
    except ImportError as e:
        logger.error("=" * 60)
        logger.error(f"❌ Import Error: {e}")
        logger.error("=" * 60)
        logger.info("\n💡 Have you installed the dependencies? Run: pip install -r requirements.txt")
        if dev_mode:
            input("\nPress Enter to exit...")
            
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("👋 Bot stopped by user (Ctrl+C).")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ An unexpected fatal error occurred: {e}")
        logger.error("=" * 60)
        logger.exception("Full traceback:")
        if dev_mode:
            input("\nPress Enter to exit...")
        raise

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the Barbershop Bot.")
    parser.add_argument(
        '--dev',
        action='store_true',
        help="Run in local development mode with detailed validation."
    )
    args = parser.parse_args()
    
    main(dev_mode=args.dev)
