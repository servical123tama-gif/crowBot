"""
Configuration Management
"""
import os
from typing import List
import logging

logger = logging.getLogger(__name__)

class Settings:
    @staticmethod
    def _parse_user_ids(raw_ids: str, var_name: str) -> List[int]:
        """Parse comma-separated user IDs from a string into a list of ints."""
        if not raw_ids:
            return []
        try:
            return [int(uid.strip()) for uid in raw_ids.split(',') if uid.strip()]
        except ValueError as e:
            logger.warning(f"Error parsing {var_name}: {e}. Contains non-integer values.")
            return []

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    BOT_NAME: str = os.getenv('BOT_NAME', 'BarbershopBot')
    BOT_USERNAME: str = os.getenv('BOT_USERNAME', '')
    
    # Google Sheets
    GOOGLE_SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', '')
    CREDENTIALS_FILE: str = 'credentials.json'
    
    # Authorization
    AUTHORIZED_CAPSTERS: List[int] = _parse_user_ids(os.getenv('AUTHORIZED_CAPSTERS', ''), 'AUTHORIZED_CAPSTERS')
    OWNER_IDS: List[int] = _parse_user_ids(os.getenv('OWNER_IDS', ''), 'OWNER_IDS')
    ADMIN_IDS: List[int] = _parse_user_ids(os.getenv('ADMIN_IDS', ''), 'ADMIN_IDS')

    # Application
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Business
    CURRENCY: str = os.getenv('CURRENCY', 'Rp')
    TIMEZONE: str = os.getenv('TIMEZONE', 'Asia/Jakarta')
    
    def validate(self) -> bool:
        """Validate required settings"""
        if not self.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required!")
        
        if not self.GOOGLE_SHEET_ID:
            raise ValueError("GOOGLE_SHEET_ID is required!")
        
        if not self.AUTHORIZED_CAPSTERS:
            raise ValueError("No authorized capsters configured!")
        
        if not os.path.exists(self.CREDENTIALS_FILE):
            raise FileNotFoundError(f"{self.CREDENTIALS_FILE} not found!")
        
        return True

# Global settings instance
settings = Settings()