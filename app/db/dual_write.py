"""
DualWrite Adapter — Phase 1 migration.
Write → DB (primary) + Sheets (backup, failures ignored).
Read  → DB always.
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


class DualWriteService:
    """Writes to both DB and Sheets; reads from DB only."""

    def __init__(self, db_service, sheets_service):
        self._db = db_service
        self._sheets = sheets_service

    def _sheets_write(self, method: str, *args, **kwargs):
        """Call a write method on Sheets; swallow all exceptions."""
        try:
            getattr(self._sheets, method)(*args, **kwargs)
        except Exception as e:
            logger.warning(f"DualWrite: Sheets backup failed for '{method}': {e}")

    # ------------------------------------------------------------------ #
    # Transactions                                                         #
    # ------------------------------------------------------------------ #

    def add_transaction(self, transaction) -> bool:
        result = self._db.add_transaction(transaction)
        self._sheets_write('add_transaction', transaction)
        return result

    def get_transactions_by_month(self, year: int, month: int) -> pd.DataFrame:
        return self._db.get_transactions_by_month(year, month)

    def get_transactions_by_date(self, dt: datetime) -> pd.DataFrame:
        return self._db.get_transactions_by_date(dt)

    def get_transactions_by_range(self, start: datetime, end: datetime) -> pd.DataFrame:
        return self._db.get_transactions_by_range(start, end)

    def get_all_transactions(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        return self._db.get_all_transactions(year)

    def get_transactions_dataframe(self, year: Optional[int] = None) -> pd.DataFrame:
        return self._db.get_transactions_dataframe(year)

    # ------------------------------------------------------------------ #
    # Customers                                                            #
    # ------------------------------------------------------------------ #

    def add_customer(self, customer) -> bool:
        result = self._db.add_customer(customer)
        self._sheets_write('add_customer', customer)
        return result

    def get_all_customers(self) -> List[Dict[str, Any]]:
        return self._db.get_all_customers()

    # ------------------------------------------------------------------ #
    # Capsters                                                             #
    # ------------------------------------------------------------------ #

    def add_capster(self, capster) -> bool:
        result = self._db.add_capster(capster)
        self._sheets_write('add_capster', capster)
        return result

    def get_all_capsters(self) -> List[Dict[str, Any]]:
        return self._db.get_all_capsters()

    def remove_capster(self, telegram_id: int) -> bool:
        result = self._db.remove_capster(telegram_id)
        self._sheets_write('remove_capster', telegram_id)
        return result

    def update_capster(self, telegram_id: int, name: str = None, alias: str = None,
                       employment_type: str = None, commission_rate: float = None) -> bool:
        result = self._db.update_capster(telegram_id, name, alias, employment_type, commission_rate)
        self._sheets_write('update_capster', telegram_id, name, alias, employment_type, commission_rate)
        return result

    def migrate_capster_names(self, alias_to_real: dict) -> dict:
        result = self._db.migrate_capster_names(alias_to_real)
        self._sheets_write('migrate_capster_names', alias_to_real)
        return result

    # ------------------------------------------------------------------ #
    # Services                                                             #
    # ------------------------------------------------------------------ #

    def get_all_services(self) -> List[Dict[str, Any]]:
        return self._db.get_all_services()

    def add_service(self, service_id: str, name: str, category: str, price: int) -> bool:
        result = self._db.add_service(service_id, name, category, price)
        self._sheets_write('add_service', service_id, name, category, price)
        return result

    def update_service(self, service_id: str, **fields) -> bool:
        result = self._db.update_service(service_id, **fields)
        self._sheets_write('update_service', service_id, **fields)
        return result

    def remove_service(self, service_id: str) -> bool:
        result = self._db.remove_service(service_id)
        self._sheets_write('remove_service', service_id)
        return result

    # ------------------------------------------------------------------ #
    # Branches                                                             #
    # ------------------------------------------------------------------ #

    def get_all_branches_config(self) -> List[Dict[str, Any]]:
        return self._db.get_all_branches_config()

    def update_branch_config(self, branch_id: str, **fields) -> bool:
        result = self._db.update_branch_config(branch_id, **fields)
        self._sheets_write('update_branch_config', branch_id, **fields)
        return result

    # ------------------------------------------------------------------ #
    # Products                                                             #
    # ------------------------------------------------------------------ #

    def get_all_products(self) -> List[Dict[str, Any]]:
        return self._db.get_all_products()

    def add_product(self, product_id: str, name: str, price: int) -> bool:
        result = self._db.add_product(product_id, name, price)
        self._sheets_write('add_product', product_id, name, price)
        return result

    def update_product(self, product_id: str, **fields) -> bool:
        result = self._db.update_product(product_id, **fields)
        self._sheets_write('update_product', product_id, **fields)
        return result

    def remove_product(self, product_id: str) -> bool:
        result = self._db.remove_product(product_id)
        self._sheets_write('remove_product', product_id)
        return result

    # ------------------------------------------------------------------ #
    # Salary Withdrawals                                                   #
    # ------------------------------------------------------------------ #

    def add_withdrawal(self, capster_name: str, telegram_id: int, amount: int,
                       period_start: str, period_end: str, note: str = '') -> bool:
        result = self._db.add_withdrawal(capster_name, telegram_id, amount, period_start, period_end, note)
        self._sheets_write('add_withdrawal', capster_name, telegram_id, amount, period_start, period_end, note)
        return result

    def get_withdrawals(self, telegram_id: int, start_date: str = None,
                        end_date: str = None) -> List[Dict[str, Any]]:
        return self._db.get_withdrawals(telegram_id, start_date, end_date)

    def get_total_withdrawn(self, telegram_id: int, start_date: str, end_date: str) -> int:
        return self._db.get_total_withdrawn(telegram_id, start_date, end_date)
