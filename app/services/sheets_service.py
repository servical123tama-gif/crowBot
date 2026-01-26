"""
Google Sheets Service
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

from app.config.settings import settings
from app.config.constants import *
from app.models.transaction import Transaction

logger = logging.getLogger(__name__)

class SheetsService:
    """Google Sheets operations"""
    
    def __init__(self):
        """Initialize Google Sheets client"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                settings.CREDENTIALS_FILE, scope
            )
            
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(settings.GOOGLE_SHEET_ID)
            
            logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise
    
    def add_transaction(self, transaction: Transaction) -> bool:
        """Add new transaction"""
        try:
            worksheet = self.sheet.worksheet(SHEET_TRANSACTIONS)
            
            row = [
                transaction.date.strftime(DATETIME_FORMAT),
                transaction.caster,
                transaction.service,
                transaction.price,
                transaction.payment_method,
                transaction.branch 
            ]
            
            worksheet.append_row(row)
            logger.info(f"✅ Transaction saved: {transaction}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed: {e}", exc_info=True)
            return False
    
    def get_all_transactions(self) -> List[Dict[str, Any]]:
        """Get all transactions"""
        try:
            worksheet = self.sheet.worksheet(SHEET_TRANSACTIONS)
            records = worksheet.get_all_records()
            
            return records
            
        except Exception as e:
            logger.error(f"Failed to get transactions: {e}")
            return []
    
    def get_transactions_dataframe(self) -> pd.DataFrame:
        """Get transactions as pandas DataFrame"""
        records = self.get_all_transactions()
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df['Date'] = pd.to_datetime(df['Date'])
        
        return df
    
    def get_transactions_by_date(self, date: datetime) -> pd.DataFrame:
        """Get transactions for specific date"""
        df = self.get_transactions_dataframe()
        
        if df.empty:
            return df
        
        date_str = date.strftime(DATE_FORMAT)
        return df[df['Date'].dt.strftime(DATE_FORMAT) == date_str]
    
    def get_transactions_by_range(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Get transactions within date range"""
        df = self.get_transactions_dataframe()
        
        if df.empty:
            return df
        
        return df[(df['Date'] >= start) & (df['Date'] <= end)]