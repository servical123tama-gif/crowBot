"""
Configuration Management
"""
import os

class Settings:
    # Application
    DEBUG: bool    = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # Business
    CURRENCY: str = os.getenv('CURRENCY', 'Rp')
    TIMEZONE: str = os.getenv('TIMEZONE', 'Asia/Jakarta')

    # Database
    DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite:///./barbershop.db')

    # Web dashboard secret key
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'dev-secret-change-in-prod')

    # WA (Fonnte)
    FONNTE_TOKEN: str = os.getenv('FONNTE_TOKEN', '')

    # QR base URL (untuk link member QR)
    BASE_URL: str = os.getenv('BASE_URL', 'http://localhost:5000')

# Global settings instance
settings = Settings()
