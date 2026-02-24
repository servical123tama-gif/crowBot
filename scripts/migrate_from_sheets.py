"""
One-time migration: Google Sheets → SQLite/PostgreSQL.
Idempotent — safe to run multiple times.

Usage:
    python scripts/migrate_from_sheets.py
"""
import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.config.settings import settings
from app.db.database import init_db, get_db
from app.db.models import Capster, Customer, Service, Branch, Product, Transaction, SalaryWithdrawal
from app.services.sheets_service import SheetsService
from app.config.constants import DATE_FORMAT, DATETIME_FORMAT

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s — %(message)s',
)
logger = logging.getLogger('migrate_from_sheets')


def migrate_capsters(sheets: SheetsService):
    logger.info("=== Migrating capsters ===")
    rows = sheets.get_all_capsters()
    added = skipped = 0
    with get_db() as db:
        for r in rows:
            tid = int(r.get('TelegramID', 0) or 0)
            if not tid:
                logger.warning(f"Skipping capster with no TelegramID: {r}")
                continue
            exists = db.query(Capster).filter(Capster.telegram_id == tid).first()
            if exists:
                skipped += 1
                continue
            try:
                cr = float(r.get('CommissionRate', 0.5) or 0.5)
            except (ValueError, TypeError):
                cr = 0.5
            db.add(Capster(
                name=r.get('Name', ''),
                telegram_id=tid,
                alias=r.get('Alias', ''),
                employment_type=r.get('EmploymentType', 'mitra') or 'mitra',
                commission_rate=cr,
            ))
            added += 1
    logger.info(f"Capsters: {added} added, {skipped} skipped")


def migrate_services(sheets: SheetsService):
    logger.info("=== Migrating services ===")
    rows = sheets.get_all_services()
    added = skipped = 0
    with get_db() as db:
        for r in rows:
            sid = r.get('ServiceID', '')
            if not sid:
                continue
            exists = db.query(Service).filter(Service.service_id == sid).first()
            if exists:
                skipped += 1
                continue
            try:
                price = int(float(r.get('Price', 0) or 0))
            except (ValueError, TypeError):
                price = 0
            db.add(Service(
                service_id=sid,
                name=r.get('Name', ''),
                category=r.get('Category', 'main') or 'main',
                price=price,
            ))
            added += 1
    logger.info(f"Services: {added} added, {skipped} skipped")


def migrate_branches(sheets: SheetsService):
    logger.info("=== Migrating branches ===")
    rows = sheets.get_all_branches_config()
    added = skipped = 0
    with get_db() as db:
        for r in rows:
            bid = r.get('BranchID', '')
            if not bid:
                continue
            exists = db.query(Branch).filter(Branch.branch_id == bid).first()
            if exists:
                skipped += 1
                continue

            def _int(key):
                try: return int(float(r.get(key, 0) or 0))
                except: return 0

            def _float(key):
                try: return float(r.get(key, 0) or 0)
                except: return 0.0

            db.add(Branch(
                branch_id=bid,
                name=r.get('Name', ''),
                location=r.get('Location', ''),
                short=r.get('Short', ''),
                employees=_int('Employees'),
                commission_rate=_float('CommissionRate'),
                cost_tempat=_int('Cost_tempat'),
                cost_listrik_air=_int('Cost_listrik_air'),
                cost_wifi=_int('Cost_wifi'),
                cost_karyawan=_int('Cost_karyawan'),
            ))
            added += 1
    logger.info(f"Branches: {added} added, {skipped} skipped")


def migrate_products(sheets: SheetsService):
    logger.info("=== Migrating products ===")
    rows = sheets.get_all_products()
    added = skipped = 0
    with get_db() as db:
        for r in rows:
            pid = r.get('ProductID', '')
            if not pid:
                continue
            exists = db.query(Product).filter(Product.product_id == pid).first()
            if exists:
                skipped += 1
                continue
            try:
                price = int(float(r.get('Price', 0) or 0))
            except (ValueError, TypeError):
                price = 0
            db.add(Product(product_id=pid, name=r.get('Name', ''), price=price))
            added += 1
    logger.info(f"Products: {added} added, {skipped} skipped")


def migrate_customers(sheets: SheetsService):
    logger.info("=== Migrating customers ===")
    rows = sheets.get_all_customers()
    added = skipped = 0
    with get_db() as db:
        existing = {(c.name, c.phone) for c in db.query(Customer).all()}
        for r in rows:
            name = r.get('Name', r.get('name', ''))
            phone = r.get('Phone', r.get('phone', ''))
            if (name, phone) in existing:
                skipped += 1
                continue
            db.add(Customer(name=name, phone=phone))
            existing.add((name, phone))
            added += 1
    logger.info(f"Customers: {added} added, {skipped} skipped")


def migrate_transactions(sheets: SheetsService, years=None):
    import pandas as pd
    if years is None:
        from datetime import datetime
        years = [datetime.now().year]
    logger.info(f"=== Migrating transactions for years: {years} ===")
    total_added = total_skipped = 0

    for year in years:
        df = sheets.get_transactions_dataframe(year=year)
        if df.empty:
            logger.info(f"No transactions found for {year}")
            continue

        logger.info(f"Found {len(df)} transactions for {year}")

        with get_db() as db:
            # Load existing keys for dedup — pakai DATETIME penuh agar
            # transaksi berbeda waktu pada hari yg sama tidak di-dedup
            existing_keys = set()
            for row in db.query(
                Transaction.date,
                Transaction.capster_name,
                Transaction.service_name,
                Transaction.price,
            ).all():
                d = row.date.strftime(DATETIME_FORMAT) if row.date else ''
                existing_keys.add((d, row.capster_name, row.service_name, row.price))

            added = skipped = 0
            for _, row in df.iterrows():
                try:
                    dt = row['Date']
                    if pd.isna(dt):
                        skipped += 1
                        continue
                    if hasattr(dt, 'to_pydatetime'):
                        dt = dt.to_pydatetime()
                    # Gunakan DATETIME_FORMAT agar tiap jam/menit unik
                    datetime_str = dt.strftime(DATETIME_FORMAT)
                    capster = str(row.get('Capster', '') or '')
                    service = str(row.get('Service', '') or '')
                    try:
                        price = int(float(row.get('Price', 0) or 0))
                    except (ValueError, TypeError):
                        price = 0

                    key = (datetime_str, capster, service, price)
                    if key in existing_keys:
                        skipped += 1
                        continue

                    db.add(Transaction(
                        date=dt,
                        capster_name=capster,
                        service_name=service,
                        price=price,
                        payment_method=str(row.get('Payment_Method', 'Cash') or 'Cash'),
                        branch=str(row.get('Branch', '') or ''),
                    ))
                    existing_keys.add((datetime_str, capster, service, price))
                    added += 1
                except Exception as e:
                    logger.warning(f"Skipping transaction row due to error: {e}")
                    skipped += 1

        logger.info(f"  Year {year}: {added} added, {skipped} skipped")
        total_added += added
        total_skipped += skipped

    logger.info(f"Transactions total: {total_added} added, {total_skipped} skipped")


def migrate_salary_withdrawals(sheets: SheetsService):
    from datetime import datetime
    logger.info("=== Migrating salary withdrawals ===")
    # get_withdrawals requires telegram_id; read the raw sheet directly
    try:
        from app.config.constants import SHEET_SALARY
        ws = sheets.sheet.worksheet(SHEET_SALARY)
        all_values = ws.get_all_values()
        if len(all_values) <= 1:
            logger.info("No salary withdrawals found.")
            return
        headers = all_values[0]
        records = [dict(zip(headers, row)) for row in all_values[1:] if any(row)]
    except Exception as e:
        logger.warning(f"Could not read salary sheet directly: {e}. Skipping withdrawal migration.")
        return

    added = skipped = 0
    with get_db() as db:
        existing_keys = set()
        for row in db.query(
            SalaryWithdrawal.telegram_id,
            SalaryWithdrawal.date,
            SalaryWithdrawal.amount,
            SalaryWithdrawal.period_start,
        ).all():
            d = row.date.strftime(DATE_FORMAT) if row.date else ''
            ps = row.period_start.strftime(DATE_FORMAT) if row.period_start else ''
            existing_keys.add((str(row.telegram_id), d, str(row.amount), ps))

        for r in records:
            try:
                tid = str(r.get('TelegramID', '') or '').strip()
                if not tid:
                    skipped += 1
                    continue

                date_str = str(r.get('Date', '') or '').strip()
                try:
                    dt = datetime.strptime(date_str, DATETIME_FORMAT)
                except ValueError:
                    try:
                        dt = datetime.strptime(date_str, DATE_FORMAT)
                    except ValueError:
                        skipped += 1
                        continue

                try:
                    amount = int(float(r.get('Amount', 0) or 0))
                except (ValueError, TypeError):
                    amount = 0

                ps_str = str(r.get('PeriodStart', '') or '').strip()
                pe_str = str(r.get('PeriodEnd', '') or '').strip()

                key = (tid, dt.strftime(DATE_FORMAT), str(amount), ps_str)
                if key in existing_keys:
                    skipped += 1
                    continue

                ps = datetime.strptime(ps_str, DATE_FORMAT).date() if ps_str else None
                pe = datetime.strptime(pe_str, DATE_FORMAT).date() if pe_str else None

                db.add(SalaryWithdrawal(
                    date=dt,
                    capster_name=str(r.get('CapsterName', '') or ''),
                    telegram_id=int(tid),
                    amount=amount,
                    period_start=ps,
                    period_end=pe,
                    note=str(r.get('Note', '') or ''),
                ))
                existing_keys.add(key)
                added += 1
            except Exception as e:
                logger.warning(f"Skipping withdrawal row due to error: {e}")
                skipped += 1

    logger.info(f"Salary withdrawals: {added} added, {skipped} skipped")


def main():
    from datetime import datetime
    logger.info("Starting migration from Google Sheets → DB")

    # Initialize DB schema
    init_db()

    logger.info("Connecting to Google Sheets...")
    sheets = SheetsService()

    migrate_capsters(sheets)
    migrate_services(sheets)
    migrate_branches(sheets)
    migrate_products(sheets)
    migrate_customers(sheets)
    migrate_transactions(sheets, years=[2025, datetime.now().year])
    migrate_salary_withdrawals(sheets)

    logger.info("Migration complete!")


if __name__ == '__main__':
    main()
