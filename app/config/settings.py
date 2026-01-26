"""
Configuration Management
"""
import os
from typing import List

class Settings:
    """Application settings"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    BOT_NAME: str = os.getenv('BOT_NAME', 'BarbershopBot')
    BOT_USERNAME: str = os.getenv('BOT_USERNAME', '')
    
    # Google Sheets
    GOOGLE_SHEET_ID: str = os.getenv('GOOGLE_SHEET_ID', '')
    CREDENTIALS_FILE: str = 'credentials.json'
    
    # Authorization - All users
    _authorized_casters_raw = os.getenv('AUTHORIZED_CASTERS', '')
    AUTHORIZED_CASTERS: List[int] = []
    
    if _authorized_casters_raw:
        try:
            AUTHORIZED_CASTERS = [
                int(uid.strip()) for uid in _authorized_casters_raw.split(',') 
                if uid.strip()
            ]
        except ValueError as e:
            print(f"Warning: Error parsing AUTHORIZED_CASTERS: {e}")
    
    # Owner IDs - Full access
    _owner_ids_raw = os.getenv('OWNER_IDS', '')
    OWNER_IDS: List[int] = []
    
    if _owner_ids_raw:
        try:
            OWNER_IDS = [
                int(uid.strip()) for uid in _owner_ids_raw.split(',') 
                if uid.strip()
            ]
        except ValueError as e:
            print(f"Warning: Error parsing OWNER_IDS: {e}")
    
    # Admin IDs - Can view all reports
    _admin_ids_raw = os.getenv('ADMIN_IDS', '')
    ADMIN_IDS: List[int] = []
    
    if _admin_ids_raw:
        try:
            ADMIN_IDS = [
                int(uid.strip()) for uid in _admin_ids_raw.split(',') 
                if uid.strip()
            ]
        except ValueError as e:
            print(f"Warning: Error parsing ADMIN_IDS: {e}")
    
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
        
        if not self.AUTHORIZED_CASTERS:
            raise ValueError("No authorized casters configured!")
        
        if not os.path.exists(self.CREDENTIALS_FILE):
            raise FileNotFoundError(f"{self.CREDENTIALS_FILE} not found!")
        
        return True

# Global settings instance
settings = Settings()