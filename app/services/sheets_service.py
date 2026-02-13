"""
Google Sheets Service
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import gspread
from gspread.exceptions import WorksheetNotFound
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

from app.config.settings import settings
from app.config.constants import DATETIME_FORMAT, DATE_FORMAT, SHEET_CUSTOMERS, MONTHS_ID
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
            
            # Initialize worksheet cache
            self._worksheet_cache = {}
            self._load_worksheet_titles()
            
            logger.info("Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}")
            raise
    
    def _load_worksheet_titles(self):
        """Load all worksheet titles into cache."""
        try:
            worksheets = self.sheet.worksheets()
            self._worksheet_cache = {ws.title: ws for ws in worksheets}
            logger.info(f"Loaded {len(self._worksheet_cache)} worksheets into cache.")
        except Exception as e:
            logger.error(f"Failed to load worksheet titles into cache: {e}")

    def _get_monthly_worksheet_name(self, date: datetime) -> str:
        """Helper to get the monthly worksheet name for a given date."""
        month_name = MONTHS_ID[date.month]
        return f"{month_name} {date.year}"


    def add_transaction(self, transaction: Transaction) -> bool:
        """Add new transaction to the appropriate monthly sheet."""
        try:
            sheet_name = self._get_monthly_worksheet_name(transaction.date)
            
            # Try to get the worksheet from cache
            worksheet = self._worksheet_cache.get(sheet_name)

            if worksheet is None:
                # If not in cache, try to open it (it might have been created by another process)
                try:
                    worksheet = self.sheet.worksheet(sheet_name)
                    self._worksheet_cache[sheet_name] = worksheet # Add to cache
                except gspread.exceptions.WorksheetNotFound:
                    logger.info(f"Worksheet '{sheet_name}' not found. Creating it...")
                    worksheet = self.sheet.add_worksheet(title=sheet_name, rows="100", cols="20")
                    # Add headers to the new sheet
                    headers = ['Date', 'Capster', 'Service', 'Price', 'Payment_Method', 'Branch']
                    worksheet.append_row(headers)
                    self._worksheet_cache[sheet_name] = worksheet # Add to cache
            
            row = [
                transaction.date.strftime(DATETIME_FORMAT),
                transaction.capster,
                transaction.service,
                transaction.price,
                transaction.payment_method,
                transaction.branch 
            ]
            
            worksheet.append_row(row)
            logger.info(f"✅ Transaction saved to '{sheet_name}': {transaction}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to add transaction to monthly sheet: {e}", exc_info=True)
            return False
    
    def _records_to_dataframe(self, records: List[Dict[str, Any]], sheet_name: str = "Unknown") -> pd.DataFrame:
        """Convert list of records to a DataFrame and parse dates."""
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)

        # Convert 'Date' column to datetime, trying multiple formats
        df['Date'] = pd.to_datetime(df['Date'], format=DATETIME_FORMAT, errors='coerce')
        
        failed_rows = df['Date'].isnull()
        if failed_rows.any():
            # Try the second format on the rows that failed the first conversion
            # Note: This approach might not be ideal if the original 'Date' column was already partially converted.
            # A safer approach would be to work on a copy or use the original strings.
            # However, for this refactoring, we'll stick to the original logic's intent.
            original_dates_on_fail = pd.DataFrame(records).loc[failed_rows, 'Date']
            df.loc[failed_rows, 'Date'] = pd.to_datetime(original_dates_on_fail, format=DATE_FORMAT, errors='coerce')

        # Log and drop rows with invalid dates after trying all formats
        invalid_dates = df['Date'].isnull()
        if not invalid_dates.empty:
            logger.warning(f"Found {len(invalid_dates)} rows with unparseable date formats in sheet '{sheet_name}'. They will be skipped.")
            df = df.dropna(subset=['Date'])
        
        return df

    def get_transactions_by_month(self, year: int, month: int) -> pd.DataFrame:
        """Efficiently get all transactions for a specific month as a DataFrame."""
        month_name = MONTHS_ID[month]
        sheet_name = f"{month_name} {year}"
        
        try:
            worksheet = self._worksheet_cache.get(sheet_name)
            if worksheet is None:
                worksheet = self.sheet.worksheet(sheet_name)
                self._worksheet_cache[sheet_name] = worksheet
            
            records = worksheet.get_all_records()
            return self._records_to_dataframe(records, sheet_name)
        
        except gspread.exceptions.WorksheetNotFound:
            logger.info(f"Worksheet '{sheet_name}' not found for month {year}-{month}. Returning empty DataFrame.")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to get transactions for month {year}-{month}: {e}")
            return pd.DataFrame()

    def get_all_transactions(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get all transactions from all monthly sheets for a given year."""
        if year is None:
            year = datetime.now().year
        
        all_records = []
        
        for month_num in range(1, 13):
            month_name = MONTHS_ID[month_num]
            sheet_name = f"{month_name} {year}"
            
            try:
                # Use the more efficient method to get a DataFrame, then convert to dicts
                df = self.get_transactions_by_month(year, month_num)
                if not df.empty:
                    # To keep the original return type, we convert the DataFrame back to records.
                    # Note: This might have performance implications if the caller doesn't actually need dicts.
                    all_records.extend(df.to_dict('records'))
            except Exception as e:
                logger.error(f"Failed to get records from '{sheet_name}': {e}")
        
        return all_records
    
    def get_transactions_dataframe(self, year: Optional[int] = None) -> pd.DataFrame:
        """Get transactions as a pandas DataFrame for a given year."""
        if year is None:
            year = datetime.now().year

        all_dfs = []
        for month_num in range(1, 13):
            df = self.get_transactions_by_month(year, month_num)
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            return pd.DataFrame()
        
        return pd.concat(all_dfs, ignore_index=True)
    
    def get_transactions_by_date(self, date: datetime) -> pd.DataFrame:
        """Get transactions for a specific date from its monthly sheet."""
        df = self.get_transactions_by_month(date.year, date.month)
        
        if df.empty:
            return pd.DataFrame()
        
        date_str = date.strftime(DATE_FORMAT)
        return df[df['Date'].dt.strftime(DATE_FORMAT) == date_str]
    
    def get_transactions_by_range(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Get transactions within a date range from relevant monthly sheets."""
        
        all_dfs_in_range = []
        current_date = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        while current_date <= end:
            df = self.get_transactions_by_month(current_date.year, current_date.month)
            if not df.empty:
                all_dfs_in_range.append(df)
            
            # Move to the next month
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        if not all_dfs_in_range:
            return pd.DataFrame()
        
        combined_df = pd.concat(all_dfs_in_range, ignore_index=True)

        # Filter by exact start and end dates
        # Ensure 'Date' column is datetime type before filtering
        if not pd.api.types.is_datetime64_any_dtype(combined_df['Date']):
             combined_df['Date'] = pd.to_datetime(combined_df['Date'], errors='coerce')
             combined_df = combined_df.dropna(subset=['Date'])

        return combined_df[(combined_df['Date'] >= start) & (combined_df['Date'] <= end)]



    def add_customer(self, customer: 'Customer') -> bool:
        """Add a new customer to the Customers sheet."""
        try:
            worksheet = self.sheet.worksheet(SHEET_CUSTOMERS)
            row = [customer.name, customer.phone]
            worksheet.append_row(row)
            logger.info(f"✅ Customer added: {customer.name} ({customer.phone})")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to add customer: {e}", exc_info=True)
            return False

    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Get all customers from the Customers sheet."""
        try:
            worksheet = self.sheet.worksheet(SHEET_CUSTOMERS)
            records = worksheet.get_all_records()
            return records
        except gspread.exceptions.WorksheetNotFound:
            logger.error(f"'{SHEET_CUSTOMERS}' sheet not found.")
            return []
        except Exception as e:
            logger.error(f"Failed to get customers: {e}")
            return []
