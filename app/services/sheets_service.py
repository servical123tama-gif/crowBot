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
from app.config.constants import (
    DATETIME_FORMAT, DATE_FORMAT, SHEET_CUSTOMERS, SHEET_CAPSTERS, MONTHS_ID,
    SHEET_SERVICES, SHEET_BRANCHES, SHEET_PRODUCTS,
    SERVICES_MAIN, SERVICES_COLORING, BRANCHES, PRODUCTS,
)
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

        # Convert 'Price' column to numeric (get_all_values returns strings)
        if 'Price' in df.columns:
            df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)

        # Convert 'Date' column to datetime, trying multiple formats
        df['Date'] = pd.to_datetime(df['Date'], format=DATETIME_FORMAT, errors='coerce')

        failed_rows = df['Date'].isnull()
        if failed_rows.any():
            original_dates_on_fail = pd.DataFrame(records).loc[failed_rows, 'Date']
            df.loc[failed_rows, 'Date'] = pd.to_datetime(original_dates_on_fail, format=DATE_FORMAT, errors='coerce')

        # Log and drop rows with invalid dates after trying all formats
        invalid_count = df['Date'].isnull().sum()
        if invalid_count > 0:
            logger.warning(f"Dropping {invalid_count} rows with unparseable dates in sheet '{sheet_name}'.")
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

            # Use get_all_values() instead of get_all_records() to avoid
            # gspread error when header row has duplicate empty cells
            # (worksheets created with cols > number of actual headers).
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return pd.DataFrame()
            headers = all_values[0]
            records = [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
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

    # --- Capster Management ---

    _CAPSTER_HEADERS = ['Name', 'TelegramID', 'Alias']

    def _ensure_capster_sheet(self):
        """Create CapsterList sheet with headers if it doesn't exist."""
        try:
            worksheet = self._worksheet_cache.get(SHEET_CAPSTERS)
            if worksheet is None:
                try:
                    worksheet = self.sheet.worksheet(SHEET_CAPSTERS)
                except WorksheetNotFound:
                    logger.info(f"Creating '{SHEET_CAPSTERS}' sheet...")
                    worksheet = self.sheet.add_worksheet(title=SHEET_CAPSTERS, rows="100", cols="5")
                    worksheet.append_row(self._CAPSTER_HEADERS)
                    self._worksheet_cache[SHEET_CAPSTERS] = worksheet
                    return worksheet

                # Sheet exists — verify/upgrade headers
                first_row = worksheet.row_values(1)
                if not first_row or first_row[0] != 'Name':
                    logger.info(f"'{SHEET_CAPSTERS}' sheet missing headers, adding them...")
                    worksheet.insert_row(self._CAPSTER_HEADERS, index=1)
                elif len(first_row) < 3 or first_row[2] != 'Alias':
                    # Upgrade: add Alias column header
                    logger.info(f"Upgrading '{SHEET_CAPSTERS}' headers with Alias column...")
                    worksheet.update_cell(1, 3, 'Alias')

                self._worksheet_cache[SHEET_CAPSTERS] = worksheet
            return worksheet
        except Exception as e:
            logger.error(f"Failed to ensure capster sheet: {e}", exc_info=True)
            raise

    def add_capster(self, capster) -> bool:
        """Add a new capster to the CapsterList sheet."""
        try:
            worksheet = self._ensure_capster_sheet()
            worksheet.append_row(capster.to_row())
            logger.info(f"Capster added: {capster.name} ({capster.telegram_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to add capster: {e}", exc_info=True)
            return False

    def get_all_capsters(self) -> List[Dict[str, Any]]:
        """Get all capsters from the CapsterList sheet."""
        try:
            worksheet = self._ensure_capster_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                # Only header or empty
                return []
            headers = all_values[0]
            return [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
        except Exception as e:
            logger.error(f"Failed to get capsters: {e}")
            return []

    def remove_capster(self, telegram_id: int) -> bool:
        """Remove a capster by telegram_id from the CapsterList sheet."""
        try:
            worksheet = self._ensure_capster_sheet()
            records = worksheet.get_all_records()

            for i, rec in enumerate(records):
                if int(rec.get('TelegramID', 0)) == telegram_id:
                    # Row index: +2 because row 1 is header, records are 0-indexed
                    worksheet.delete_rows(i + 2)
                    logger.info(f"Capster with TelegramID {telegram_id} removed from sheet.")
                    return True

            logger.warning(f"Capster with TelegramID {telegram_id} not found in sheet.")
            return False
        except Exception as e:
            logger.error(f"Failed to remove capster: {e}", exc_info=True)
            return False

    def update_capster(self, telegram_id: int, name: str = None, alias: str = None) -> bool:
        """Update capster data by telegram_id."""
        try:
            worksheet = self._ensure_capster_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False

            for i, row in enumerate(all_values[1:], start=2):
                if len(row) >= 2 and str(row[1]).strip() == str(telegram_id):
                    if name is not None:
                        worksheet.update_cell(i, 1, name)
                    if alias is not None:
                        worksheet.update_cell(i, 3, alias)
                    logger.info(f"Capster {telegram_id} updated: name={name}, alias={alias}")
                    return True

            logger.warning(f"Capster {telegram_id} not found for update.")
            return False
        except Exception as e:
            logger.error(f"Failed to update capster: {e}", exc_info=True)
            return False

    def migrate_capster_names(self, alias_to_real: dict) -> dict:
        """Batch rename capster names in all monthly transaction sheets.
        alias_to_real: {old_name_lower: new_real_name}
        Returns: {sheet_name: count_of_updated_rows}
        """
        results = {}
        try:
            worksheets = self.sheet.worksheets()
            for ws in worksheets:
                title = ws.title
                # Skip non-transaction sheets
                if title in (SHEET_CUSTOMERS, SHEET_CAPSTERS, 'Summary'):
                    continue

                all_values = ws.get_all_values()
                if len(all_values) <= 1:
                    continue

                headers = all_values[0]
                if 'Capster' not in headers:
                    continue

                capster_col = headers.index('Capster')
                updated = 0
                for row_idx, row in enumerate(all_values[1:], start=2):
                    if capster_col < len(row):
                        old_name = row[capster_col].strip()
                        new_name = alias_to_real.get(old_name.lower())
                        if new_name and new_name != old_name:
                            ws.update_cell(row_idx, capster_col + 1, new_name)
                            updated += 1

                if updated > 0:
                    results[title] = updated
                    logger.info(f"Migrated {updated} rows in '{title}'")

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
        return results

    # --- Service Config Management ---

    _SERVICE_HEADERS = ['ServiceID', 'Name', 'Category', 'Price']

    def _ensure_service_sheet(self):
        """Create ServiceList sheet with headers if it doesn't exist. Seed from hardcoded defaults."""
        try:
            worksheet = self._worksheet_cache.get(SHEET_SERVICES)
            if worksheet is None:
                try:
                    worksheet = self.sheet.worksheet(SHEET_SERVICES)
                except WorksheetNotFound:
                    logger.info(f"Creating '{SHEET_SERVICES}' sheet with default data...")
                    worksheet = self.sheet.add_worksheet(title=SHEET_SERVICES, rows="100", cols="10")
                    worksheet.append_row(self._SERVICE_HEADERS)
                    # Seed from hardcoded constants
                    rows = []
                    for sid, data in SERVICES_MAIN.items():
                        rows.append([sid, data['name'], 'main', data['price']])
                    for sid, data in SERVICES_COLORING.items():
                        rows.append([sid, data['name'], 'coloring', data['price']])
                    if rows:
                        worksheet.append_rows(rows)
                    self._worksheet_cache[SHEET_SERVICES] = worksheet
                    logger.info(f"Seeded {len(rows)} services into '{SHEET_SERVICES}'")
                    return worksheet

                self._worksheet_cache[SHEET_SERVICES] = worksheet
            return worksheet
        except Exception as e:
            logger.error(f"Failed to ensure service sheet: {e}", exc_info=True)
            raise

    def get_all_services(self) -> List[Dict[str, Any]]:
        """Get all services from the ServiceList sheet."""
        try:
            worksheet = self._ensure_service_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return []
            headers = all_values[0]
            return [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    def add_service(self, service_id: str, name: str, category: str, price: int) -> bool:
        """Add a new service to the ServiceList sheet."""
        try:
            worksheet = self._ensure_service_sheet()
            worksheet.append_row([service_id, name, category, price])
            logger.info(f"Service added: {service_id} ({name})")
            return True
        except Exception as e:
            logger.error(f"Failed to add service: {e}", exc_info=True)
            return False

    def update_service(self, service_id: str, **fields) -> bool:
        """Update a service by ServiceID. fields can be name, category, price."""
        try:
            worksheet = self._ensure_service_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False
            headers = all_values[0]
            sid_col = headers.index('ServiceID')
            for i, row in enumerate(all_values[1:], start=2):
                if row[sid_col] == service_id:
                    for field, value in fields.items():
                        if field in headers:
                            col_idx = headers.index(field) + 1
                            worksheet.update_cell(i, col_idx, value)
                    logger.info(f"Service {service_id} updated: {fields}")
                    return True
            logger.warning(f"Service {service_id} not found for update.")
            return False
        except Exception as e:
            logger.error(f"Failed to update service: {e}", exc_info=True)
            return False

    def remove_service(self, service_id: str) -> bool:
        """Remove a service by ServiceID."""
        try:
            worksheet = self._ensure_service_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False
            headers = all_values[0]
            sid_col = headers.index('ServiceID')
            for i, row in enumerate(all_values[1:], start=2):
                if row[sid_col] == service_id:
                    worksheet.delete_rows(i)
                    logger.info(f"Service {service_id} removed.")
                    return True
            logger.warning(f"Service {service_id} not found for removal.")
            return False
        except Exception as e:
            logger.error(f"Failed to remove service: {e}", exc_info=True)
            return False

    # --- Branch Config Management ---

    _BRANCH_HEADERS = [
        'BranchID', 'Name', 'Location', 'Short', 'Employees',
        'CommissionRate', 'Cost_tempat', 'Cost_listrik_air', 'Cost_wifi', 'Cost_karyawan'
    ]

    def _ensure_branch_config_sheet(self):
        """Create BranchConfig sheet with headers if it doesn't exist. Seed from hardcoded defaults."""
        try:
            worksheet = self._worksheet_cache.get(SHEET_BRANCHES)
            if worksheet is None:
                try:
                    worksheet = self.sheet.worksheet(SHEET_BRANCHES)
                except WorksheetNotFound:
                    logger.info(f"Creating '{SHEET_BRANCHES}' sheet with default data...")
                    worksheet = self.sheet.add_worksheet(title=SHEET_BRANCHES, rows="100", cols="15")
                    worksheet.append_row(self._BRANCH_HEADERS)
                    rows = []
                    for bid, data in BRANCHES.items():
                        costs = data.get('operational_cost', {})
                        rows.append([
                            bid,
                            data['name'],
                            data.get('location', ''),
                            data.get('short', ''),
                            data.get('employees', 2),
                            data.get('commission_rate', 0),
                            costs.get('tempat', 0),
                            costs.get('listrik air', 0),
                            costs.get('wifi', 0),
                            costs.get('karyawan_fixed', 0),
                        ])
                    if rows:
                        worksheet.append_rows(rows)
                    self._worksheet_cache[SHEET_BRANCHES] = worksheet
                    logger.info(f"Seeded {len(rows)} branches into '{SHEET_BRANCHES}'")
                    return worksheet

                self._worksheet_cache[SHEET_BRANCHES] = worksheet
            return worksheet
        except Exception as e:
            logger.error(f"Failed to ensure branch config sheet: {e}", exc_info=True)
            raise

    def get_all_branches_config(self) -> List[Dict[str, Any]]:
        """Get all branch configs from the BranchConfig sheet."""
        try:
            worksheet = self._ensure_branch_config_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return []
            headers = all_values[0]
            return [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
        except Exception as e:
            logger.error(f"Failed to get branch configs: {e}")
            return []

    def update_branch_config(self, branch_id: str, **fields) -> bool:
        """Update a branch config by BranchID. fields can be any column name."""
        try:
            worksheet = self._ensure_branch_config_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False
            headers = all_values[0]
            bid_col = headers.index('BranchID')
            for i, row in enumerate(all_values[1:], start=2):
                if row[bid_col] == branch_id:
                    for field, value in fields.items():
                        if field in headers:
                            col_idx = headers.index(field) + 1
                            worksheet.update_cell(i, col_idx, value)
                    logger.info(f"Branch {branch_id} updated: {fields}")
                    return True
            logger.warning(f"Branch {branch_id} not found for update.")
            return False
        except Exception as e:
            logger.error(f"Failed to update branch config: {e}", exc_info=True)
            return False

    # --- Product Management ---

    _PRODUCT_HEADERS = ['ProductID', 'Name', 'Price']

    def _ensure_product_sheet(self):
        """Create ProductList sheet with headers if it doesn't exist. Seed from hardcoded defaults."""
        try:
            worksheet = self._worksheet_cache.get(SHEET_PRODUCTS)
            if worksheet is None:
                try:
                    worksheet = self.sheet.worksheet(SHEET_PRODUCTS)
                except WorksheetNotFound:
                    logger.info(f"Creating '{SHEET_PRODUCTS}' sheet with default data...")
                    worksheet = self.sheet.add_worksheet(title=SHEET_PRODUCTS, rows="100", cols="10")
                    worksheet.append_row(self._PRODUCT_HEADERS)
                    rows = []
                    for pid, data in PRODUCTS.items():
                        rows.append([pid, data['name'], data['price']])
                    if rows:
                        worksheet.append_rows(rows)
                    self._worksheet_cache[SHEET_PRODUCTS] = worksheet
                    logger.info(f"Seeded {len(rows)} products into '{SHEET_PRODUCTS}'")
                    return worksheet

                self._worksheet_cache[SHEET_PRODUCTS] = worksheet
            return worksheet
        except Exception as e:
            logger.error(f"Failed to ensure product sheet: {e}", exc_info=True)
            raise

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all products from the ProductList sheet."""
        try:
            worksheet = self._ensure_product_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return []
            headers = all_values[0]
            return [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            return []

    def add_product(self, product_id: str, name: str, price: int) -> bool:
        """Add a new product to the ProductList sheet."""
        try:
            worksheet = self._ensure_product_sheet()
            worksheet.append_row([product_id, name, price])
            logger.info(f"Product added: {product_id} ({name})")
            return True
        except Exception as e:
            logger.error(f"Failed to add product: {e}", exc_info=True)
            return False

    def update_product(self, product_id: str, **fields) -> bool:
        """Update a product by ProductID."""
        try:
            worksheet = self._ensure_product_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False
            headers = all_values[0]
            pid_col = headers.index('ProductID')
            for i, row in enumerate(all_values[1:], start=2):
                if row[pid_col] == product_id:
                    for field, value in fields.items():
                        if field in headers:
                            col_idx = headers.index(field) + 1
                            worksheet.update_cell(i, col_idx, value)
                    logger.info(f"Product {product_id} updated: {fields}")
                    return True
            logger.warning(f"Product {product_id} not found for update.")
            return False
        except Exception as e:
            logger.error(f"Failed to update product: {e}", exc_info=True)
            return False

    def remove_product(self, product_id: str) -> bool:
        """Remove a product by ProductID."""
        try:
            worksheet = self._ensure_product_sheet()
            all_values = worksheet.get_all_values()
            if len(all_values) <= 1:
                return False
            headers = all_values[0]
            pid_col = headers.index('ProductID')
            for i, row in enumerate(all_values[1:], start=2):
                if row[pid_col] == product_id:
                    worksheet.delete_rows(i)
                    logger.info(f"Product {product_id} removed.")
                    return True
            logger.warning(f"Product {product_id} not found for removal.")
            return False
        except Exception as e:
            logger.error(f"Failed to remove product: {e}", exc_info=True)
            return False
