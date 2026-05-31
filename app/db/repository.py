"""
Repository — SQLAlchemy drop-in replacement for SheetsService.
All public methods return identical types as SheetsService.
"""
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional

import pandas as pd
from sqlalchemy import func, and_, or_, extract
from werkzeug.security import generate_password_hash, check_password_hash

from app.db.database import get_db
from app.db.models import (
    Transaction, Capster, Customer, Service, Branch, Product, SalaryWithdrawal,
    ProductStock, ProductSale, Promo, Setting, LoyaltyClaim,
)
from app.config.constants import (
    DATETIME_FORMAT, DATE_FORMAT,
    SERVICES_MAIN, SERVICES_COLORING, BRANCHES, PRODUCTS,
)

logger = logging.getLogger(__name__)


class Repository:
    """SQLAlchemy-backed data service. Drop-in replacement for SheetsService."""

    # ------------------------------------------------------------------ #
    # Transactions                                                         #
    # ------------------------------------------------------------------ #

    def _add_transaction_legacy(self) -> bool:
        # removed — hanya dipakai bot Telegram (sudah dihapus)
        raise NotImplementedError
        try:
            pass
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
            logger.error(f"Failed to get transactions for date {dt}: {e}")
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
                'PromoName': r.promo_name or '',
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

    def get_recent_customers(self, limit: int = 20) -> List[Dict]:
        """Return N most recently added customers, newest first."""
        try:
            with get_db() as db:
                rows = db.query(Customer).order_by(
                    Customer.created_at.desc().nullslast(),
                    Customer.id.desc()
                ).limit(limit).all()
            return [
                {
                    'id':        r.id,
                    'Name':      r.name,
                    'Phone':     r.phone or '',
                    'AddedBy':   getattr(r, 'added_by', '') or '',
                    'CreatedAt': r.created_at,
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get recent customers: {e}")
            return []

    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Return existing customer dict if phone already registered, else None."""
        if not phone or not phone.strip():
            return None
        try:
            with get_db() as db:
                row = db.query(Customer).filter(
                    Customer.phone == phone.strip()
                ).first()
            if row:
                return {'id': row.id, 'Name': row.name, 'Phone': row.phone or '',
                        'VisitCount': getattr(row, 'visit_count', 0) or 0,
                        'AddedBy': getattr(row, 'added_by', '') or ''}
            return None
        except Exception as e:
            logger.error(f"Failed to get customer by phone: {e}")
            return None

    def add_customer(self, customer, added_by: str = '') -> Optional[int]:
        """Insert customer. Return new ID kalau sukses, None kalau gagal.

        Note: caller lama yang pakai `if ok:` tetap jalan karena None falsy & int truthy.
        """
        try:
            with get_db() as db:
                new_row = Customer(
                    name=customer.name,
                    phone=customer.phone,
                    added_by=added_by,
                    visit_count=1,
                )
                db.add(new_row)
                db.flush()              # populate new_row.id sebelum commit
                new_id = new_row.id
            logger.info(f"Customer added id={new_id}: {customer.name} by {added_by or 'unknown'}")
            return new_id
        except Exception as e:
            logger.error(f"Failed to add customer: {e}", exc_info=True)
            return None

    def get_all_customers(self) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                rows = db.query(Customer).order_by(Customer.name).all()
            return [
                {'id': r.id, 'Name': r.name, 'Phone': r.phone or '',
                 'VisitCount': getattr(r, 'visit_count', 0) or 0,
                 'PointBalance': getattr(r, 'point_balance', 0) or 0,
                 'AddedBy': getattr(r, 'added_by', '') or '',
                 'CreatedAt': getattr(r, 'created_at', None)}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get customers: {e}")
            return []

    def get_transactions_by_customer(self, customer_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    Transaction.customer_id == customer_id
                ).order_by(Transaction.date.desc()).limit(limit).all()
            return [
                {
                    'date':    r.date,
                    'service': r.service_name,
                    'price':   r.price,
                    'capster': r.capster_name,
                    'payment': r.payment_method,
                    'promo':   r.promo_name or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get transactions by customer: {e}")
            return []

    def get_customers_by_capster(self, capster_name: str) -> List[Dict[str, Any]]:
        """Get all customers added by a specific capster."""
        try:
            with get_db() as db:
                rows = db.query(Customer).filter(
                    Customer.added_by == capster_name
                ).order_by(Customer.name).all()
            return [
                {'id': r.id, 'Name': r.name, 'Phone': r.phone or '',
                 'VisitCount': getattr(r, 'visit_count', 0) or 0,
                 'AddedBy': getattr(r, 'added_by', '') or ''}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get customers by capster: {e}")
            return []

    def search_customers(self, query: str) -> List[Dict[str, Any]]:
        """Search customers by name or phone (case-insensitive)."""
        try:
            q = query.strip().lower()
            with get_db() as db:
                rows = db.query(Customer).filter(
                    or_(
                        func.lower(Customer.name).contains(q),
                        Customer.phone.contains(q),
                    )
                ).order_by(Customer.name).limit(10).all()
            return [
                {'id': r.id, 'Name': r.name, 'Phone': r.phone or '',
                 'VisitCount': getattr(r, 'visit_count', 0) or 0,
                 'PointBalance': getattr(r, 'point_balance', 0) or 0,
                 'AddedBy': getattr(r, 'added_by', '') or ''}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to search customers: {e}")
            return []

    def increment_visit_count(self, customer_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
                if not row:
                    return False
                current = getattr(row, 'visit_count', 0) or 0
                row.visit_count = current + 1
            return True
        except Exception as e:
            logger.error(f"Failed to increment visit count for customer {customer_id}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Loyalty / Points                                                    #
    # ------------------------------------------------------------------ #

    LOYALTY_THRESHOLDS = {
        '50pct': {'points': 5,  'label': 'Diskon 50%'},
        'free':  {'points': 10, 'label': 'Potong Gratis'},
    }
    LOYALTY_MAX_POINTS = 10

    def get_loyalty_status(self, customer_id: int, include_next: bool = False) -> Dict:
        """Return point_balance and available claim types for a customer.

        include_next=True → cek reward setelah +1 poin (kunjungan ini).
        Panel muncul saat point_balance >= 4 (→ jadi 5) atau >= 9 (→ jadi 10).
        """
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
            if not row:
                return {'point_balance': 0, 'available': []}
            bal = getattr(row, 'point_balance', 0) or 0
            check_bal = min(bal + 1, self.LOYALTY_MAX_POINTS) if include_next else bal
            # Tampilkan hanya reward terbaik yang bisa diclaim (prioritas: gratis > 50%)
            available = []
            if check_bal >= self.LOYALTY_THRESHOLDS['free']['points']:
                t = self.LOYALTY_THRESHOLDS['free']
                available.append({'type': 'free', 'label': t['label'], 'points': t['points']})
            elif check_bal >= self.LOYALTY_THRESHOLDS['50pct']['points']:
                t = self.LOYALTY_THRESHOLDS['50pct']
                available.append({'type': '50pct', 'label': t['label'], 'points': t['points']})
            return {'point_balance': bal, 'available': available}
        except Exception as e:
            logger.error(f"Failed to get loyalty status: {e}")
            return {'point_balance': 0, 'available': []}

    def add_customer_points(self, customer_id: int, points: int = 1) -> int:
        """Add loyalty points to customer. Returns new balance."""
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
                if not row:
                    return 0
                bal = min((getattr(row, 'point_balance', 0) or 0) + points, self.LOYALTY_MAX_POINTS)
                row.point_balance = bal
            return bal
        except Exception as e:
            logger.error(f"Failed to add points to customer {customer_id}: {e}")
            return 0

    def use_loyalty_claim(self, customer_id: int, claim_type: str,
                          transaction_id: Optional[int] = None) -> bool:
        """Tambah +1 poin kunjungan ini, validasi threshold, reset ke 0, catat klaim."""
        cfg = self.LOYALTY_THRESHOLDS.get(claim_type)
        if not cfg:
            return False
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
                if not row:
                    return False
                bal = min((getattr(row, 'point_balance', 0) or 0) + 1, self.LOYALTY_MAX_POINTS)
                if bal < cfg['points']:
                    return False
                row.point_balance = 0
                db.add(LoyaltyClaim(
                    customer_id=customer_id,
                    claim_type=claim_type,
                    points_used=cfg['points'],
                    claimed_at=datetime.utcnow(),
                    transaction_id=transaction_id,
                ))
            return True
        except Exception as e:
            logger.error(f"Failed to use loyalty claim: {e}")
            return False

    def get_loyalty_history(self, customer_id: Optional[int] = None,
                            limit: int = 50) -> List[Dict]:
        """Return loyalty claim history, optionally filtered by customer."""
        try:
            with get_db() as db:
                q = db.query(LoyaltyClaim, Customer.name).join(
                    Customer, LoyaltyClaim.customer_id == Customer.id, isouter=True
                )
                if customer_id:
                    q = q.filter(LoyaltyClaim.customer_id == customer_id)
                rows = q.order_by(LoyaltyClaim.claimed_at.desc()).limit(limit).all()
            result = []
            for claim, cname in rows:
                label = self.LOYALTY_THRESHOLDS.get(claim.claim_type, {}).get('label', claim.claim_type)
                result.append({
                    'id':             claim.id,
                    'customer_id':    claim.customer_id,
                    'customer_name':  cname or '-',
                    'claim_type':     claim.claim_type,
                    'label':          label,
                    'points_used':    claim.points_used,
                    'claimed_at':     claim.claimed_at,
                    'transaction_id': claim.transaction_id,
                })
            return result
        except Exception as e:
            logger.error(f"Failed to get loyalty history: {e}")
            return []

    def add_transaction_full(self, date: 'datetime', capster_name: str, service_name: str,
                             price: int, payment_method: str, branch: str,
                             customer_id: Optional[int] = None,
                             promo_name: Optional[str] = None) -> bool:
        """Add transaction and optionally increment customer visit count."""
        try:
            with get_db() as db:
                row = Transaction(
                    date=date,
                    capster_name=capster_name,
                    service_name=service_name,
                    price=int(price),
                    payment_method=payment_method or 'Cash',
                    branch=branch,
                    customer_id=customer_id,
                    promo_name=promo_name or '',
                )
                db.add(row)
            if customer_id:
                self.increment_visit_count(customer_id)
            logger.info(f"Transaction added: {capster_name} - {service_name} - customer={customer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to add transaction_full: {e}", exc_info=True)
            return False

    def generate_customer_qr_png(self, customer_id: int) -> bytes:
        """Generate QR code PNG bytes for a customer. Content: BARBER:<id>"""
        import qrcode
        import io
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=3,
        )
        qr.add_data(f'BARBER:{customer_id}')
        qr.make(fit=True)
        img = qr.make_image(fill_color='#0f3460', back_color='white')
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    def get_customer_by_id(self, customer_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
            if not row:
                return None
            return {
                'id': row.id, 'Name': row.name, 'Phone': row.phone or '',
                'VisitCount': getattr(row, 'visit_count', 0) or 0,
                'AddedBy': getattr(row, 'added_by', '') or '',
                'CreatedAt': getattr(row, 'created_at', None),
            }
        except Exception as e:
            logger.error(f"Failed to get customer {customer_id}: {e}")
            return None

    def update_customer(self, customer_id: int, name: str, phone: str,
                        added_by: str = None, visit_count: int = None) -> bool:
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
                if not row:
                    return False
                row.name = name
                row.phone = phone or ''
                if added_by is not None:
                    row.added_by = added_by
                if visit_count is not None:
                    row.visit_count = visit_count
            logger.info(f"Customer {customer_id} updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update customer {customer_id}: {e}", exc_info=True)
            return False

    def delete_customer(self, customer_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(Customer).filter(Customer.id == customer_id).first()
                if not row:
                    return False
                db.delete(row)
            logger.info(f"Customer {customer_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete customer {customer_id}: {e}", exc_info=True)
            return False

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
                    'TelegramID': r.telegram_id,
                    'Alias': r.alias or '',
                    'EmploymentType': r.employment_type,
                    'CommissionRate': float(r.commission_rate or 0.5),
                    'MonthlySalary': int(r.monthly_salary or 0),
                    'BranchID': r.branch_id or '',
                    'Username': r.username or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get capsters: {e}")
            return []

    # ── Capster Auth ────────────────────────────────────────────────────── #

    def get_capster_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                row = db.query(Capster).filter(Capster.username == username).first()
            if not row:
                return None
            return {
                'id': row.id,
                'Name': row.name,
                'TelegramID': row.telegram_id,
                'Alias': row.alias or '',
                'EmploymentType': row.employment_type,
                'CommissionRate': float(row.commission_rate or 0.5),
                'MonthlySalary': int(row.monthly_salary or 0),
                'BranchID': row.branch_id or '',
                'Username': row.username or '',
                'password_hash': row.password_hash or '',
            }
        except Exception as e:
            logger.error(f"Failed to get capster by username: {e}")
            return None

    def set_capster_credentials(self, telegram_id: int, username: str, password: str) -> tuple:
        """Set username + password for a capster. Returns (ok, error_message)."""
        try:
            with get_db() as db:
                conflict = db.query(Capster).filter(
                    Capster.username == username,
                    Capster.telegram_id != telegram_id,
                ).first()
                if conflict:
                    return False, f'Username "{username}" sudah dipakai capster lain.'
                row = db.query(Capster).filter(Capster.telegram_id == telegram_id).first()
                if not row:
                    return False, 'Capster tidak ditemukan.'
                row.username = username
                row.password_hash = generate_password_hash(password)
            logger.info(f"Credentials set for capster {telegram_id} → username={username}")
            return True, ''
        except Exception as e:
            logger.error(f"Failed to set capster credentials: {e}", exc_info=True)
            return False, 'Terjadi kesalahan server.'

    def verify_capster_login(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Return capster dict if username+password valid, else None."""
        capster = self.get_capster_by_username(username)
        if not capster or not capster.get('password_hash'):
            return None
        if check_password_hash(capster['password_hash'], password):
            return capster
        return None

    def update_capster_password(self, telegram_id: int, new_password: str) -> bool:
        try:
            with get_db() as db:
                row = db.query(Capster).filter(Capster.telegram_id == telegram_id).first()
                if not row:
                    return False
                row.password_hash = generate_password_hash(new_password)
            logger.info(f"Password updated for capster {telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update capster password: {e}", exc_info=True)
            return False

    def get_transactions_by_capster_month(self, capster_name: str, alias: str,
                                          year: int, month: int) -> List[Dict[str, Any]]:
        """Transactions for a capster (by name OR alias) in a given month."""
        try:
            names_lower = [capster_name.lower()]
            if alias:
                names_lower.append(alias.lower())
            with get_db() as db:
                rows = db.query(Transaction).filter(
                    func.lower(Transaction.capster_name).in_(names_lower),
                    extract('year',  Transaction.date) == year,
                    extract('month', Transaction.date) == month,
                ).order_by(Transaction.date.desc()).all()
            return [
                {
                    'id':      r.id,
                    'date':    r.date,
                    'service': r.service_name,
                    'price':   r.price,
                    'payment': r.payment_method,
                    'branch':  r.branch or '',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get capster transactions: {e}")
            return []

    def get_product_sales_by_capster_month(self, capster_name: str, alias: str,
                                           year: int, month: int) -> List[Dict[str, Any]]:
        """Product sales for a capster in a given month."""
        try:
            names_lower = [capster_name.lower()]
            if alias:
                names_lower.append(alias.lower())
            with get_db() as db:
                rows = db.query(ProductSale).filter(
                    func.lower(ProductSale.capster_name).in_(names_lower),
                    extract('year',  ProductSale.date) == year,
                    extract('month', ProductSale.date) == month,
                ).order_by(ProductSale.date.desc()).all()
            return [
                {
                    'id':         r.id,
                    'date':       r.date,
                    'service':    f"{r.product_name} (x{r.quantity})",
                    'price':      r.price_each * r.quantity,   # harga jual (omset)
                    'commission': r.commission_earned,          # komisi capster
                    'payment':    '-',
                    'branch':     r.branch_id or '',
                    'type':       'produk',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get capster product sales: {e}")
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
                {'ServiceID': r.service_id, 'Name': r.name, 'Category': r.category,
                 'Price': int(r.price),
                 'CommissionRate': float(getattr(r, 'commission_rate', 0.5) or 0.5)}
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get services: {e}")
            return []

    def add_service(self, service_id: str, name: str, category: str, price: int, commission_rate: float = 0.5) -> bool:
        try:
            with get_db() as db:
                db.add(Service(service_id=service_id, name=name, category=category,
                               price=int(price), commission_rate=commission_rate))
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
                    elif col == 'commission_rate':
                        row.commission_rate = float(value)
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

    def get_service_popularity(self) -> dict:
        """Return {service_name_lower: transaction_count} for all time."""
        try:
            with get_db() as db:
                rows = db.query(
                    Transaction.service_name,
                    func.count(Transaction.id).label('cnt'),
                ).group_by(Transaction.service_name).all()
            return {r.service_name.lower(): r.cnt for r in rows}
        except Exception as e:
            logger.error(f"Failed to get service popularity: {e}")
            return {}

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
                    'Employees': int(r.employees or 0),
                    'CommissionRate': float(r.commission_rate or 0),
                    'Cost_tempat': int(r.cost_tempat or 0),
                    'Cost_listrik_air': int(r.cost_listrik_air or 0),
                    'Cost_wifi': int(r.cost_wifi or 0),
                    'Cost_karyawan': int(r.cost_karyawan or 0),
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
            return [{
                'ProductID':      r.product_id,
                'Name':           r.name,
                'Price':          int(r.price),
                'CommissionRate': float(r.commission_rate or 0),
            } for r in rows]
        except Exception as e:
            logger.error(f"Failed to get products: {e}")
            return []

    def add_product(self, product_id: str, name: str, price: int,
                    commission_rate: float = 0.0) -> bool:
        try:
            with get_db() as db:
                db.add(Product(
                    product_id=product_id, name=name,
                    price=int(price), commission_rate=float(commission_rate),
                ))
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
                    elif col == 'commission_rate':
                        row.commission_rate = float(value)
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
    # Product Stock                                                        #
    # ------------------------------------------------------------------ #

    def get_product_stocks(self, branch_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return list of stocks optionally filtered by branch_id.
        Each item: {ProductID, Name, Price, CommissionRate, BranchID, Quantity}
        """
        try:
            with get_db() as db:
                self._seed_products_if_empty(db)
                products = db.query(Product).all()
                product_map = {p.product_id: p for p in products}

                query = db.query(ProductStock)
                if branch_id:
                    query = query.filter(ProductStock.branch_id == branch_id)
                stock_rows = query.all()
                stock_map = {(s.product_id, s.branch_id): s.quantity for s in stock_rows}

            results = []
            if branch_id:
                # Return one row per product (stock for this branch)
                for p in sorted(products, key=lambda x: x.name):
                    results.append({
                        'ProductID':      p.product_id,
                        'Name':           p.name,
                        'Price':          p.price,
                        'CommissionRate': p.commission_rate,
                        'BranchID':       branch_id,
                        'Quantity':       stock_map.get((p.product_id, branch_id), 0),
                    })
            else:
                for (pid, bid), qty in stock_map.items():
                    p = product_map.get(pid)
                    if p:
                        results.append({
                            'ProductID':      pid,
                            'Name':           p.name,
                            'Price':          p.price,
                            'CommissionRate': p.commission_rate,
                            'BranchID':       bid,
                            'Quantity':       qty,
                        })
            return results
        except Exception as e:
            logger.error(f"Failed to get product stocks: {e}", exc_info=True)
            return []

    def set_stock(self, product_id: str, branch_id: str, quantity: int) -> bool:
        """Upsert stock quantity for a product-branch pair."""
        try:
            qty = max(0, int(quantity))
            with get_db() as db:
                row = db.query(ProductStock).filter_by(
                    product_id=product_id, branch_id=branch_id
                ).first()
                if row:
                    row.quantity = qty
                else:
                    db.add(ProductStock(product_id=product_id, branch_id=branch_id, quantity=qty))
            logger.info(f"Stock set: {product_id}@{branch_id}={qty}")
            return True
        except Exception as e:
            logger.error(f"Failed to set stock: {e}", exc_info=True)
            return False

    def adjust_stock(self, product_id: str, branch_id: str, delta: int) -> int:
        """Add delta to stock (negative to subtract). Returns new quantity (floor 0)."""
        try:
            with get_db() as db:
                row = db.query(ProductStock).filter_by(
                    product_id=product_id, branch_id=branch_id
                ).first()
                if row:
                    new_qty = max(0, row.quantity + delta)
                    row.quantity = new_qty
                else:
                    new_qty = max(0, delta)
                    db.add(ProductStock(product_id=product_id, branch_id=branch_id, quantity=new_qty))
            return new_qty
        except Exception as e:
            logger.error(f"Failed to adjust stock: {e}", exc_info=True)
            return 0

    # ------------------------------------------------------------------ #
    # Product Sales                                                        #
    # ------------------------------------------------------------------ #

    def add_product_sale(self, capster_name: str, product_id: str, product_name: str,
                         price_each: int, quantity: int,
                         commission_rate: float, branch_id: str) -> bool:
        """Record a product sale and reduce stock."""
        try:
            commission_earned = int(price_each * quantity * commission_rate)
            with get_db() as db:
                db.add(ProductSale(
                    date=datetime.now(),
                    capster_name=capster_name,
                    product_id=product_id,
                    product_name=product_name,
                    price_each=int(price_each),
                    quantity=int(quantity),
                    commission_rate=float(commission_rate),
                    commission_earned=commission_earned,
                    branch_id=branch_id,
                ))
            # Reduce stock
            self.adjust_stock(product_id, branch_id, -quantity)
            logger.info(f"ProductSale: {capster_name} sold {quantity}x{product_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to record product sale: {e}", exc_info=True)
            return False

    def get_product_sales_commission_total(self, capster_name: str) -> int:
        """Total commission earned from product sales (all-time) for a capster."""
        try:
            with get_db() as db:
                result = db.query(func.sum(ProductSale.commission_earned)).filter(
                    func.lower(ProductSale.capster_name) == capster_name.lower()
                ).scalar()
            return int(result or 0)
        except Exception as e:
            logger.error(f"Failed to get product sales commission: {e}", exc_info=True)
            return 0

    def get_product_sales(self, capster_name: Optional[str] = None,
                          year: Optional[int] = None,
                          month_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """List product sales, optionally filtered."""
        try:
            with get_db() as db:
                query = db.query(ProductSale).order_by(ProductSale.date.desc())
                if capster_name:
                    query = query.filter(
                        func.lower(ProductSale.capster_name) == capster_name.lower()
                    )
                if year:
                    query = query.filter(extract('year', ProductSale.date) == year)
                rows = query.all()
            results = []
            for r in rows:
                date_str = r.date.strftime('%Y-%m-%d %H:%M') if r.date else ''
                if month_str and date_str[:7] != month_str:
                    continue
                results.append({
                    'ID':               r.id,
                    'Date':             date_str,
                    'CapsterName':      r.capster_name,
                    'ProductID':        r.product_id,
                    'ProductName':      r.product_name,
                    'PriceEach':        r.price_each,
                    'Quantity':         r.quantity,
                    'CommissionRate':   r.commission_rate,
                    'CommissionEarned': r.commission_earned,
                    'BranchID':         r.branch_id,
                    'Total':            r.price_each * r.quantity,
                })
            return results
        except Exception as e:
            logger.error(f"Failed to get product sales: {e}", exc_info=True)
            return []

    def get_product_sales_by_range(self, start: datetime, end: datetime,
                                   capster_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Product sales in a date range, optionally filtered by capster."""
        try:
            with get_db() as db:
                query = db.query(ProductSale).filter(
                    ProductSale.date >= start,
                    ProductSale.date <= end,
                )
                if capster_name:
                    query = query.filter(
                        func.lower(ProductSale.capster_name) == capster_name.lower()
                    )
                rows = query.order_by(ProductSale.date.desc()).all()
            return [{
                'ID':               r.id,
                'Date':             r.date.strftime('%Y-%m-%d %H:%M') if r.date else '',
                'DateObj':          r.date,
                'CapsterName':      r.capster_name,
                'ProductID':        r.product_id,
                'ProductName':      r.product_name,
                'PriceEach':        r.price_each,
                'Quantity':         r.quantity,
                'CommissionRate':   r.commission_rate,
                'CommissionEarned': r.commission_earned,
                'BranchID':         r.branch_id,
                'Total':            r.price_each * r.quantity,
            } for r in rows]
        except Exception as e:
            logger.error(f"Failed to get product sales by range: {e}", exc_info=True)
            return []

    def update_product_sale(self, sale_id: int, date: 'datetime', capster_name: str,
                             product_id: str, product_name: str, price_each: int,
                             quantity: int, commission_rate: float, branch_id: str) -> bool:
        """Update a product sale and adjust stock accordingly."""
        try:
            with get_db() as db:
                row = db.query(ProductSale).filter(ProductSale.id == sale_id).first()
                if row is None:
                    return False
                old_product_id = row.product_id
                old_branch_id  = row.branch_id
                old_qty        = row.quantity

                row.date             = date
                row.capster_name     = capster_name
                row.product_id       = product_id
                row.product_name     = product_name
                row.price_each       = int(price_each)
                row.quantity         = int(quantity)
                row.commission_rate  = float(commission_rate)
                row.commission_earned= int(price_each * quantity * commission_rate)
                row.branch_id        = branch_id

            # Adjust stock: restore old, reduce new
            if old_product_id != product_id or old_branch_id != branch_id:
                self.adjust_stock(old_product_id, old_branch_id, old_qty)
                self.adjust_stock(product_id, branch_id, -int(quantity))
            elif old_qty != int(quantity):
                self.adjust_stock(product_id, branch_id, old_qty - int(quantity))

            logger.info(f"ProductSale {sale_id} updated")
            return True
        except Exception as e:
            logger.error(f"Failed to update product sale {sale_id}: {e}", exc_info=True)
            return False

    def delete_product_sale(self, sale_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(ProductSale).filter(ProductSale.id == sale_id).first()
                if row is None:
                    return False
                # Kembalikan stok
                self.adjust_stock(row.product_id, row.branch_id, row.quantity)
                db.delete(row)
            return True
        except Exception as e:
            logger.error(f"Failed to delete product sale {sale_id}: {e}", exc_info=True)
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
                    'TelegramID': r.telegram_id,
                    'Amount': int(r.amount),
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
                    'TelegramID': r.telegram_id,
                    'Amount': int(r.amount),
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
            total += r.get('Amount', 0)
        return total

    # ------------------------------------------------------------------ #
    # Promos                                                               #
    # ------------------------------------------------------------------ #

    def get_all_promos(self) -> List[Dict]:
        try:
            with get_db() as db:
                rows = db.query(Promo).order_by(Promo.id.desc()).all()
            return [
                {
                    'id':           r.id,
                    'name':         r.name,
                    'discount_pct': r.discount_pct,
                    'start_date':   r.start_date.strftime('%Y-%m-%d') if r.start_date else '',
                    'end_date':     r.end_date.strftime('%Y-%m-%d') if r.end_date else '',
                    'is_active':    bool(r.is_active),
                    'service_ids':  [s.strip() for s in r.service_ids.split(',') if s.strip()],
                    'branch_ids':   r.branch_ids or 'ALL',
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get all promos: {e}")
            return []

    def get_active_promos_for_branch(self, branch_id: str, today=None) -> List[Dict]:
        """Return promos active today for the given branch_id."""
        if today is None:
            today = date.today()
        try:
            with get_db() as db:
                rows = db.query(Promo).filter(
                    Promo.is_active == True,
                    Promo.start_date <= today,
                    Promo.end_date >= today,
                ).all()
            result = []
            for r in rows:
                b_ids = r.branch_ids or 'ALL'
                if b_ids.strip().upper() == 'ALL' or branch_id in [x.strip() for x in b_ids.split(',')]:
                    result.append({
                        'id':           r.id,
                        'name':         r.name,
                        'discount_pct': r.discount_pct,
                        'service_ids':  [s.strip() for s in r.service_ids.split(',') if s.strip()],
                    })
            return result
        except Exception as e:
            logger.error(f"Failed to get active promos for branch {branch_id}: {e}")
            return []

    def add_promo(self, name: str, discount_pct: float, start_date, end_date,
                  service_ids: list, branch_ids: list) -> bool:
        try:
            with get_db() as db:
                row = Promo(
                    name=name,
                    discount_pct=discount_pct,
                    start_date=start_date,
                    end_date=end_date,
                    is_active=True,
                    service_ids=','.join(service_ids),
                    branch_ids=','.join(branch_ids) if branch_ids else 'ALL',
                )
                db.add(row)
            return True
        except Exception as e:
            logger.error(f"Failed to add promo: {e}")
            return False

    def update_promo(self, promo_id: int, **fields) -> bool:
        try:
            with get_db() as db:
                row = db.query(Promo).filter(Promo.id == promo_id).first()
                if not row:
                    return False
                if 'name' in fields:
                    row.name = fields['name']
                if 'discount_pct' in fields:
                    row.discount_pct = fields['discount_pct']
                if 'start_date' in fields:
                    row.start_date = fields['start_date']
                if 'end_date' in fields:
                    row.end_date = fields['end_date']
                if 'is_active' in fields:
                    row.is_active = bool(fields['is_active'])
                if 'service_ids' in fields:
                    ids = fields['service_ids']
                    row.service_ids = ','.join(ids) if isinstance(ids, list) else ids
                if 'branch_ids' in fields:
                    ids = fields['branch_ids']
                    row.branch_ids = ','.join(ids) if isinstance(ids, list) else ids
            return True
        except Exception as e:
            logger.error(f"Failed to update promo {promo_id}: {e}")
            return False

    def delete_promo(self, promo_id: int) -> bool:
        try:
            with get_db() as db:
                row = db.query(Promo).filter(Promo.id == promo_id).first()
                if not row:
                    return False
                db.delete(row)
            return True
        except Exception as e:
            logger.error(f"Failed to delete promo {promo_id}: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Settings (key-value store)                                           #
    # ------------------------------------------------------------------ #

    def get_setting(self, key: str, default: str = '') -> str:
        try:
            with get_db() as db:
                row = db.query(Setting).filter(Setting.key == key).first()
            return row.value if row else default
        except Exception as e:
            logger.error(f"Failed to get setting {key}: {e}")
            return default

    def set_setting(self, key: str, value: str) -> None:
        try:
            with get_db() as db:
                row = db.query(Setting).filter(Setting.key == key).first()
                if row:
                    row.value = value
                else:
                    db.add(Setting(key=key, value=value))
        except Exception as e:
            logger.error(f"Failed to set setting {key}: {e}")
