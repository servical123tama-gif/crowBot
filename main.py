import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config.settings import settings

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=settings.LOG_LEVEL.upper(),
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("🚀 Starting Barbershop Bot on Render.com...")
    logger.info("=" * 60)
    
    try:
        # Start health check web server (untuk Render.com)
        logger.info("Starting health check server...")
        from app.web_server import keep_alive
        keep_alive()
        logger.info("✅ Health check server started")
        
        # Start Telegram bot
        logger.info("Initializing Telegram bot...")
        from app.bot import BarbershopBot
        bot = BarbershopBot()
        
        logger.info("✅ Bot initialized successfully")
        logger.info("🤖 Bot is now running and listening for messages...")
        
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    main()