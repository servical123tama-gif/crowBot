"""
Repository — SQLAlchemy drop-in replacement for SheetsService.
All public methods return identical types as SheetsService.
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import pandas as pd
from sqlalchemy import func, and_, or_, extract

from app.db.database import get_db
from app.db.models import (
    Transaction, Capster, Customer, Service, Branch, Product, SalaryWithdrawal
)
from app.config.constants import (
    DATETIME_FORMAT, DATE_FORMAT,
    SERVICES_MAIN, SERVICES_COLORING, BRANCHES, PRODUCTS,
)
from app.models.transaction import Transaction as TxModel

logger = logging.getLogger(__name__)


class Repository:
    """SQLAlchemy-backed data service. Drop-in replacement for SheetsService."""

    # ------------------------------------------------------------------ #
    # Transactions                                                         #
    # ------------------------------------------------------------------ #

    def add_transaction(self, transaction: TxModel) -> bool:
        try:
            with get_db() as db:
                row = Transaction(
                    date=transaction.date,
                    capster_name=transaction.capster,
                    service_name=transaction.service,
                    price=int(transaction.price),
                    payment_method=transaction.payment_method or 'Cash',
                    branch=transaction.branch,
                )
                db.add(row)
            logger.info(f"Transaction saved to DB: {transaction}")
            return True
        except Exception as e:
            logger.error(f"Failed to add transaction: {e}", exc_info=True)
            return False

    def get_transactions_by_month(self, year: int, month: int) -> pd.DataFrame:
        try:
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    extract('year', Transaction.date) == year,
                    extract('month', Transaction.date) == month,
                ).all()
            return self._rows_to_df(rows)
        except Exception as e:
            logger.error(f"Failed to get transactions for {year}-{month}: {e}")
            return pd.DataFrame()

    def get_transactions_by_date(self, dt: datetime) -> pd.DataFrame:
        try:
            from datetime import timedelta
            start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
            end   = start + timedelta(days=1)
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    Transaction.date >= start,
                    Transaction.date <  end,
                ).all()
            return self._rows_to_df(rows)
        except Exception as e:
            logger.error(f"Failed to get transactions for date {date_str}: {e}")
            return pd.DataFrame()

    def get_transactions_by_range(self, start: datetime, end: datetime) -> pd.DataFrame:
        try:
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    Transaction.date >= start,
                    Transaction.date <= end,
                ).all()
            return self._rows_to_df(rows)
        except Exception as e:
            logger.error(f"Failed to get transactions for range {start}–{end}: {e}")
            return pd.DataFrame()

    def get_all_transactions(self, year: Optional[int] = None) -> List[Dict[str, Any]]:
        if year is None:
            year = datetime.now().year
        try:
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    extract('year', Transaction.date) == year
                ).all()
            df = self._rows_to_df(rows)
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            logger.error(f"Failed to get all transactions for {year}: {e}")
            return []

    def get_transactions_dataframe(self, year: Optional[int] = None) -> pd.DataFrame:
        if year is None:
            year = datetime.now().year
        try:
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    extract('year', Transaction.date) == year
                ).all()
            return self._rows_to_df(rows)
        except Exception as e:
            logger.error(f"Failed to get transactions dataframe for {year}: {e}")
            return pd.DataFrame()

    @staticmethod
    def _rows_to_df(rows: list) -> pd.DataFrame:
        """Convert ORM Transaction rows → DataFrame matching SheetsService format."""
        if not rows:
            return pd.DataFrame()
        records = [
            {
                'id': r.id,
                'Date': r.date,
                'Capster': r.capster_name,
                'Service': r.service_name,
                'Price': r.price,
                'Payment_Method': r.payment_method,
                'Branch': r.branch or '',
            }
            for r in rows
        ]
        df = pd.DataFrame(records)
        df['Date'] = pd.to_datetime(df['Date'])
        df['Price'] = pd.to_numeric(df['Price'], errors='coerce').fillna(0).astype(int)
        return df

    def get_transaction_by_id(self, tx_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                row = db.query(Transaction).filter(Transaction.id == tx_id).first()
            if not row:
                return None
            return {
                'id': row.id,
                'date': row.date.strftime('%Y-%m-%dT%H:%M'),
                'capster': row.capster_name,
                'service': row.service_name,
                'price': row.price,
                'payment': row.payment_method,
                'branch': row.branch or '',
            }
        except Exception as e:
            logger.error(f"Failed to get transaction {tx_id}: {e}")
            return None

    def update_transaction(self, tx_id: int, date: datetime, capster: str,
                           service: str, price: int, payment: str, branch: str) -> bool:
        try:
            with get_db() as db:
                row = db.query(Transaction).filter(Transaction.id == tx_id).first()
                if not row:
                    return False
                row.date = date
                row.capster_name = capster
                row.service_name = service
                row.price = price
                row.payment_method = payment
                row.branch = branch
            logger.info(f"Transaction {tx_id} updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update transaction {tx_id}: {e}", exc_info=True)
            return False

    def delete_transaction(self, tx_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(Transaction).filter(Transaction.id == tx_id).first()
                if not row:
                    return False
                db.delete(row)
            logger.info(f"Transaction {tx_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete transaction {tx_id}: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------ #
    # Customers                                                            #
    # ------------------------------------------------------------------ #

    def add_customer(self, customer) -> bool:
        try:
            with get_db() as db:
                db.add(Customer(name=customer.name, phone=customer.phone))
            logger.info(f"Customer added: {customer.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add customer: {e}", exc_info=True)
            return False

    def get_all_customers(self) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                rows = db.query(Customer).all()
            return [{'Name': r.name, 'Phone': r.phone} for r in rows]
        except Exception as e:
            logger.error(f"Failed to get customers: {e}")
            return []

    # ------------------------------------------------------------------ #
    # Capsters                                                             #
    # ------------------------------------------------------------------ #

    def add_capster(self, capster) -> bool:
        try:
            with get_db() as db:
                db.add(Capster(
                    name=capster.name,
                    telegram_id=capster.telegram_id,
                    alias=capster.alias or '',
                    employment_type=capster.employment_type or 'mitra',
                    commission_rate=float(capster.commission_rate or 0.5),
                    monthly_salary=int(getattr(capster, 'monthly_salary', 0) or 0),
                    branch_id=getattr(capster, 'branch_id', '') or '',
                ))
            logger.info(f"Capster added: {capster.name} ({capster.telegram_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to add capster: {e}", exc_info=True)
            return False

    def get_all_capsters(self) -> List[Dict[str, Any]]:
        """Return list of dicts with keys matching SheetsService: Name, TelegramID, Alias, EmploymentType, CommissionRate, MonthlySalary, BranchID."""
        try:
            with get_db() as db:
                rows = db.query(Capster).all()
            return [
                {
                    'Name': r.name,
                    'TelegramID': str(r.telegram_id),
                    'Alias': r.alias or '',
                    'EmploymentType': r.employment_type,
                    'CommissionRate': str(r.commission_rate),
                    'MonthlySalary': str(r.monthly_salary or 0),
                    'BranchID': r.branch_id or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get capsters: {e}")
            return []

    def remove_capster(self, telegram_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(Capster).filter(Capster.telegram_id == telegram_id).first()
                if row is None:
                    logger.warning(f"Capster {telegram_id} not found for removal.")
                    return False
                db.delete(row)
            logger.info(f"Capster {telegram_id} removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove capster: {e}", exc_info=True)
            return False

    def update_capster(self, telegram_id: int, name: str = None, alias: str = None,
                       employment_type: str = None, commission_rate: float = None,
                       monthly_salary: int = None, branch_id: str = None) -> bool:
        try:
            with get_db() as db:
                row = db.query(Capster).filter(Capster.telegram_id == telegram_id).first()
                if row is None:
                    logger.warning(f"Capster {telegram_id} not found for update.")
                    return False
                if name is not None:
                    row.name = name
                if alias is not None:
                    row.alias = alias
                if employment_type is not None:
                    row.employment_type = employment_type
                if commission_rate is not None:
                    row.commission_rate = float(commission_rate)
                if monthly_salary is not None:
                    row.monthly_salary = int(monthly_salary)
                if branch_id is not None:
                    row.branch_id = branch_id
            logger.info(f"Capster {telegram_id} updated.")
            return True
        except Exception as e:
            logger.error(f"Failed to update capster: {e}", exc_info=True)
            return False

    def migrate_capster_names(self, alias_to_real: dict) -> dict:
        """Batch rename capster_name in transactions for alias migration.
        alias_to_real: {old_name_lower: new_real_name}
        Returns: {new_name: count_updated}
        """
        results = {}
        try:
            with get_db() as db:
                for old_lower, new_name in alias_to_real.items():
                    updated = db.query(Transaction).filter(
                        func.lower(Transaction.capster_name) == old_lower
                    ).update({'capster_name': new_name}, synchronize_session='fetch')
                    if updated > 0:
                        results[new_name] = updated
                        logger.info(f"Migrated {updated} transactions: '{old_lower}' → '{new_name}'")
        except Exception as e:
            logger.error(f"migrate_capster_names failed: {e}", exc_info=True)
        return results

    # ------------------------------------------------------------------ #
    # Services                                                             #
    # ------------------------------------------------------------------ #

    def _seed_services_if_empty(self, db):
        count = db.query(func.count(Service.service_id)).scalar()
        if count == 0:
            rows = []
            for sid, data in SERVICES_MAIN.items():
                rows.append(Service(service_id=sid, name=data['name'], category='main', price=data['price']))
            for sid, data in SERVICES_COLORING.items():
                rows.append(Service(service_id=sid, name=data['name'], category='coloring', price=data['price']))
            db.add_all(rows)
            logger.info(f"Seeded {len(rows)} services into DB")

    def get_all_services(self) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                self._seed_services_if_empty(db)
                rows = db.query(Service).all()
            return [
                {'ServiceID': r.service_id, 'Name': r.name, 'Category': r.category, 'Price': str(r.price)}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    def add_service(self, service_id: str, name: str, category: str, price: int) -> bool:
        try:
            with get_db() as db:
                db.add(Service(service_id=service_id, name=name, category=category, price=int(price)))
            logger.info(f"Service added: {service_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add service: {e}", exc_info=True)
            return False

    def update_service(self, service_id: str, **fields) -> bool:
        try:
            with get_db() as db:
                row = db.query(Service).filter(Service.service_id == service_id).first()
                if row is None:
                    logger.warning(f"Service {service_id} not found for update.")
                    return False
                for field, value in fields.items():
                    col = field.lower()
                    if col == 'name':
                        row.name = value
                    elif col == 'category':
                        row.category = value
                    elif col == 'price':
                        row.price = int(value)
            logger.info(f"Service {service_id} updated: {fields}")
            return True
        except Exception as e:
            logger.error(f"Failed to update service: {e}", exc_info=True)
            return False

    def remove_service(self, service_id: str) -> bool:
        try:
            with get_db() as db:
                row = db.query(Service).filter(Service.service_id == service_id).first()
                if row is None:
                    logger.warning(f"Service {service_id} not found for removal.")
                    return False
                db.delete(row)
            logger.info(f"Service {service_id} removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove service: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------ #
    # Branches                                                             #
    # ------------------------------------------------------------------ #

    def _seed_branches_if_empty(self, db):
        count = db.query(func.count(Branch.branch_id)).scalar()
        if count == 0:
            rows = []
            for bid, data in BRANCHES.items():
                costs = data.get('operational_cost', {})
                rows.append(Branch(
                    branch_id=bid,
                    name=data['name'],
                    location=data.get('location', ''),
                    short=data.get('short', ''),
                    employees=data.get('employees', 2),
                    commission_rate=data.get('commission_rate', 0),
                    cost_tempat=costs.get('tempat', 0),
                    cost_listrik_air=costs.get('listrik air', 0),
                    cost_wifi=costs.get('wifi', 0),
                    cost_karyawan=costs.get('karyawan_fixed', 0),
                ))
            db.add_all(rows)
            logger.info(f"Seeded {len(rows)} branches into DB")

    def get_all_branches_config(self) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                self._seed_branches_if_empty(db)
                rows = db.query(Branch).all()
            return [
                {
                    'BranchID': r.branch_id,
                    'Name': r.name,
                    'Location': r.location or '',
                    'Short': r.short or '',
                    'Employees': str(r.employees),
                    'CommissionRate': str(r.commission_rate),
                    'Cost_tempat': str(r.cost_tempat),
                    'Cost_listrik_air': str(r.cost_listrik_air),
                    'Cost_wifi': str(r.cost_wifi),
                    'Cost_karyawan': str(r.cost_karyawan),
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get branch configs: {e}")
            return []

    def update_branch_config(self, branch_id: str, **fields) -> bool:
        _col_map = {
            'name': 'name', 'location': 'location', 'short': 'short',
            'employees': 'employees', 'commissionrate': 'commission_rate',
            'cost_tempat': 'cost_tempat', 'cost_listrik_air': 'cost_listrik_air',
            'cost_wifi': 'cost_wifi', 'cost_karyawan': 'cost_karyawan',
        }
        try:
            with get_db() as db:
                row = db.query(Branch).filter(Branch.branch_id == branch_id).first()
                if row is None:
                    logger.warning(f"Branch {branch_id} not found for update.")
                    return False
                for field, value in fields.items():
                    attr = _col_map.get(field.lower().replace(' ', '_'))
                    if attr:
                        if attr in ('employees', 'cost_tempat', 'cost_listrik_air', 'cost_wifi', 'cost_karyawan'):
                            setattr(row, attr, int(value))
                        elif attr == 'commission_rate':
                            setattr(row, attr, float(value))
                        else:
                            setattr(row, attr, value)
            logger.info(f"Branch {branch_id} updated: {fields}")
            return True
        except Exception as e:
            logger.error(f"Failed to update branch config: {e}", exc_info=True)
            return False

    def add_branch(self, branch_id: str, name: str, location: str = '',
                   short: str = '', employees: int = 2, commission_rate: float = 0.0,
                   cost_tempat: int = 0, cost_listrik_air: int = 0,
                   cost_wifi: int = 0, cost_karyawan: int = 0) -> bool:
        try:
            with get_db() as db:
                db.add(Branch(
                    branch_id=branch_id,
                    name=name,
                    location=location or '',
                    short=short or '',
                    employees=int(employees or 2),
                    commission_rate=float(commission_rate or 0),
                    cost_tempat=int(cost_tempat or 0),
                    cost_listrik_air=int(cost_listrik_air or 0),
                    cost_wifi=int(cost_wifi or 0),
                    cost_karyawan=int(cost_karyawan or 0),
                ))
            logger.info(f"Branch added: {branch_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add branch: {e}", exc_info=True)
            return False

    def remove_branch(self, branch_id: str) -> bool:
        try:
            with get_db() as db:
                row = db.query(Branch).filter(Branch.branch_id == branch_id).first()
                if row is None:
                    logger.warning(f"Branch {branch_id} not found for removal.")
                    return False
                db.delete(row)
            logger.info(f"Branch {branch_id} removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove branch: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------ #
    # Products                                                             #
    # ------------------------------------------------------------------ #

    def _seed_products_if_empty(self, db):
        count = db.query(func.count(Product.product_id)).scalar()
        if count == 0:
            rows = [
                Product(product_id=pid, name=data['name'], price=data['price'])
                for pid, data in PRODUCTS.items()
            ]
            db.add_all(rows)
            logger.info(f"Seeded {len(rows)} products into DB")

    def get_all_products(self) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                self._seed_products_if_empty(db)
                rows = db.query(Product).all()
            return [{'ProductID': r.product_id, 'Name': r.name, 'Price': str(r.price)} for r in rows]
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            return []

    def add_product(self, product_id: str, name: str, price: int) -> bool:
        try:
            with get_db() as db:
                db.add(Product(product_id=product_id, name=name, price=int(price)))
            logger.info(f"Product added: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add product: {e}", exc_info=True)
            return False

    def update_product(self, product_id: str, **fields) -> bool:
        try:
            with get_db() as db:
                row = db.query(Product).filter(Product.product_id == product_id).first()
                if row is None:
                    logger.warning(f"Product {product_id} not found for update.")
                    return False
                for field, value in fields.items():
                    col = field.lower()
                    if col == 'name':
                        row.name = value
                    elif col == 'price':
                        row.price = int(value)
            logger.info(f"Product {product_id} updated: {fields}")
            return True
        except Exception as e:
            logger.error(f"Failed to update product: {e}", exc_info=True)
            return False

    def remove_product(self, product_id: str) -> bool:
        try:
            with get_db() as db:
                row = db.query(Product).filter(Product.product_id == product_id).first()
                if row is None:
                    logger.warning(f"Product {product_id} not found for removal.")
                    return False
                db.delete(row)
            logger.info(f"Product {product_id} removed.")
            return True
        except Exception as e:
            logger.error(f"Failed to remove product: {e}", exc_info=True)
            return False

    # ------------------------------------------------------------------ #
    # Salary Withdrawals                                                   #
    # ------------------------------------------------------------------ #

    def add_withdrawal(self, capster_name: str, telegram_id: int, amount: int,
                       period_start: str, period_end: str, note: str = '') -> bool:
        try:
            ps = datetime.strptime(period_start, DATE_FORMAT).date() if period_start else None
            pe = datetime.strptime(period_end, DATE_FORMAT).date() if period_end else None
            with get_db() as db:
                db.add(SalaryWithdrawal(
                    date=datetime.now(),
                    capster_name=capster_name,
                    telegram_id=telegram_id,
                    amount=int(amount),
                    period_start=ps,
                    period_end=pe,
                    note=note or '',
                ))
            logger.info(f"Withdrawal recorded: {capster_name} Rp {amount:,}")
            return True
        except Exception as e:
            logger.error(f"Failed to add withdrawal: {e}", exc_info=True)
            return False

    def get_withdrawals(self, telegram_id: int, start_date: str = None,
                        end_date: str = None) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                q = db.query(SalaryWithdrawal).filter(
                    SalaryWithdrawal.telegram_id == telegram_id
                )
                if start_date and end_date:
                    # period overlap: withdrawal.period_start <= end_date AND withdrawal.period_end >= start_date
                    ps = datetime.strptime(start_date, DATE_FORMAT).date()
                    pe = datetime.strptime(end_date, DATE_FORMAT).date()
                    q = q.filter(
                        SalaryWithdrawal.period_start <= pe,
                        SalaryWithdrawal.period_end >= ps,
                    )
                rows = q.all()
            return [
                {
                    'Date': r.date.strftime(DATETIME_FORMAT) if r.date else '',
                    'CapsterName': r.capster_name,
                    'TelegramID': str(r.telegram_id),
                    'Amount': str(r.amount),
                    'PeriodStart': r.period_start.strftime(DATE_FORMAT) if r.period_start else '',
                    'PeriodEnd': r.period_end.strftime(DATE_FORMAT) if r.period_end else '',
                    'Note': r.note or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get withdrawals: {e}")
            return []

    def get_all_withdrawals(self) -> List[Dict[str, Any]]:
        """Semua withdrawal dari semua capster, diurutkan terbaru dulu."""
        try:
            with get_db() as db:
                rows = db.query(SalaryWithdrawal).order_by(SalaryWithdrawal.date.desc()).all()
            return [
                {
                    'Date': r.date.strftime(DATETIME_FORMAT) if r.date else '',
                    'CapsterName': r.capster_name,
                    'TelegramID': str(r.telegram_id),
                    'Amount': str(r.amount),
                    'PeriodStart': r.period_start.strftime(DATE_FORMAT) if r.period_start else '',
                    'PeriodEnd': r.period_end.strftime(DATE_FORMAT) if r.period_end else '',
                    'Note': r.note or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get all withdrawals: {e}")
            return []

    def get_total_withdrawn(self, telegram_id: int, start_date: str, end_date: str) -> int:
        records = self.get_withdrawals(telegram_id, start_date, end_date)
        total = 0
        for r in records:
            try:
                total += int(float(r.get('Amount', 0)))
            except (ValueError, TypeError):
                pass
        return total
