"""
Barbershop Bot - Entry Point
Jalankan dengan: python run.py
"""
import logging
import os
import sys

# Tambahkan path root ke sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create logs directory if not exists
os.makedirs('logs', exist_ok=True)

# Setup logging SEBELUM import app
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,  # ← Ubah ke DEBUG untuk detail
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def validate_environment():
    """Validate environment before starting"""
    logger.info("=" * 60)
    logger.info("🔍 Validating environment...")
    logger.info("=" * 60)
    
    # Check .env file
    if not os.path.exists('.env'):
        logger.error("❌ .env file not found!")
        logger.info("💡 Copy .env.example to .env and configure it")
        return False
    logger.info("✅ .env file found")
    
    # Check credentials.json
    if not os.path.exists('credentials.json'):
        logger.error("❌ credentials.json not found!")
        logger.info("💡 Download from Google Cloud Console")
        return False
    logger.info("✅ credentials.json found")
    
    # Load and check .env values
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    sheet_id = os.getenv('GOOGLE_SHEET_ID', '')
    authorized = os.getenv('AUTHORIZED_CAPSTERS', '')
    
    logger.info(f"📋 Configuration:")
    logger.info(f"   BOT_TOKEN: {'✅ Set' if bot_token else '❌ Empty'}")
    logger.info(f"   SHEET_ID: {'✅ Set' if sheet_id else '❌ Empty'}")
    logger.info(f"   AUTHORIZED_CAPSTERS: {'✅ Set' if authorized else '❌ Empty'}")
    
    if not bot_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN is empty in .env")
        return False
    
    if not sheet_id:
        logger.error("❌ GOOGLE_SHEET_ID is empty in .env")
        return False
    
    if not authorized:
        logger.error("❌ AUTHORIZED_CAPSTERS is empty in .env")
        return False
    
    logger.info("✅ All environment variables configured")
    return True

def main():
    """Main entry point"""
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Barbershop Bot...")
        logger.info("=" * 60)
        
        # Validate environment first
        if not validate_environment():
            logger.error("❌ Environment validation failed!")
            logger.info("\n💡 Please check the errors above and fix them")
            input("\nPress Enter to exit...")
            return
        
        logger.info("\n" + "=" * 60)
        logger.info("📦 Importing bot modules...")
        logger.info("=" * 60)
        
        # Import after validation
        from app.bot import BarbershopBot
        from app.config.settings import settings
        
        logger.info("✅ Modules imported successfully")
        
        # Validate settings
        logger.info("\n" + "=" * 60)
        logger.info("⚙️  Validating settings...")
        logger.info("=" * 60)
        
        settings.validate()
        logger.info("✅ Settings validated")
        
        # Create and run bot
        logger.info("\n" + "=" * 60)
        logger.info("🤖 Initializing bot...")
        logger.info("=" * 60)
        
        bot = BarbershopBot()
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ Bot initialized successfully!")
        logger.info(f"📝 Bot Name: {settings.BOT_NAME}")
        logger.info(f"👥 Authorized Users: {len(settings.AUTHORIZED_CAPSTERS)}")
        logger.info("🔄 Starting polling...")
        logger.info("=" * 60)
        logger.info("\n💡 Bot is now running! Press Ctrl+C to stop.\n")
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("👋 Bot stopped by user (Ctrl+C)")
        logger.info("=" * 60)
        
    except ValueError as e:
        logger.error("=" * 60)
        logger.error(f"❌ Configuration error: {e}")
        logger.error("=" * 60)
        logger.info("\n💡 Please check your .env file configuration")
        input("\nPress Enter to exit...")
        
    except FileNotFoundError as e:
        logger.error("=" * 60)
        logger.error(f"❌ File not found: {e}")
        logger.error("=" * 60)
        input("\nPress Enter to exit...")
        
    except ImportError as e:
        logger.error("=" * 60)
        logger.error(f"❌ Import error: {e}")
        logger.error("=" * 60)
        logger.info("\n💡 Make sure all dependencies are installed:")
        logger.info("   pip install -r requirements.txt")
        input("\nPress Enter to exit...")
        
    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ Fatal error: {e}")
        logger.error("=" * 60)
        logger.exception("Full traceback:")
        input("\nPress Enter to exit...")
        raise

if __name__ == '__main__':
    main()