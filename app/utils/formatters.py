"""
Text Formatting Utilities
"""
from datetime import datetime
from typing import Dict, Any
from app.config.settings import settings
from app.config.constants import *

class Formatter:
    """Text formatters"""
    
    @staticmethod
    def format_currency(amount: float) -> str:
        """Format currency"""
        return f"{settings.CURRENCY} {amount:,.0f}"
    
    @staticmethod
    def format_date(date: datetime) -> str:
        """Format date for display"""
        return date.strftime(DISPLAY_DATE_FORMAT)
    
    @staticmethod
    def format_time(time: datetime) -> str:
        """Format time for display"""
        return time.strftime(DISPLAY_TIME_FORMAT)
    
    @staticmethod
    def format_transaction_success(data: Dict[str, Any]) -> str:
        """Format transaction success message"""
        return MSG_TRANSACTION_SUCCESS.format(
            service=data['service'],
            currency=settings.CURRENCY,
            price=data['price'],
            payment_method=data['payment_method'],
            branch=data['branch'],
            capster=data['capster'],
            time=Formatter.format_time(data['time'])
        )
    
    @staticmethod
    def format_report_header(report_type: str, **kwargs) -> str:
        """Format report header"""
        if report_type == 'daily':
            return REPORT_DAILY_HEADER.format(**kwargs)
        elif report_type == 'weekly':
            return REPORT_WEEKLY_HEADER
        elif report_type == 'monthly':
            return REPORT_MONTHLY_HEADER.format(**kwargs)
        return ""