"""
Input Validators
"""
import re
from typing import Optional

class Validator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_price(price: str) -> Optional[float]:
        """Validate price input"""
        try:
            price_float = float(price.replace(',', '').replace('.', ''))
            if price_float <= 0:
                return None
            return price_float
        except ValueError:
            return None
    
    @staticmethod
    def validate_user_id(user_id: str) -> Optional[int]:
        """Validate Telegram user ID"""
        try:
            uid = int(user_id)
            if uid > 0:
                return uid
            return None
        except ValueError:
            return None
    
    @staticmethod
    def validate_service_name(name: str) -> bool:
        """Validate service name"""
        if not name or len(name) < 2:
            return False
        # Only allow alphanumeric and spaces
        return bool(re.match(r'^[a-zA-Z0-9\s]+$', name))
    
    @staticmethod
    def validate_date_format(date_str: str, format: str = '%Y-%m-%d') -> bool:
        """Validate date format"""
        try:
            from datetime import datetime
            datetime.strptime(date_str, format)
            return True
        except ValueError:
            return False