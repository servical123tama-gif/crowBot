"""
Migrasi data dari SQLite ke PostgreSQL.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Pastikan .env sudah diupdate dengan DATABASE_URL PostgreSQL
dan SQLite barbershop.db masih ada di root project.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Koneksi SQLite (sumber) ───────────────────────────────────────────────────
SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'barbershop.db')

# ── Koneksi PostgreSQL (tujuan) ───────────────────────────────────────────────
PG_URL = os.getenv('DATABASE_URL', '')
if not PG_URL or PG_URL.startswith('sqlite'):
    print("ERROR: DATABASE_URL di .env harus PostgreSQL, bukan SQLite.")
    print("       Contoh: postgresql://postgres:password@localhost:5432/barbershop_db")
    sys.exit(1)

PG_URL = PG_URL.replace('postgres://', 'postgresql://', 1)

print(f"SQLite  : {SQLITE_PATH}")
print(f"Postgres: {PG_URL[:PG_URL.index('@')+1]}***")
print()

# ── Setup PostgreSQL engine + buat tabel ─────────────────────────────────────
from app.db.models import Base
from app.db.database import init_db

pg_engine = create_engine(PG_URL, pool_pre_ping=True)
PgSession = sessionmaker(bind=pg_engine)

print("Membuat tabel di PostgreSQL...")
Base.metadata.create_all(bind=pg_engine)
print("Tabel berhasil dibuat.\n")

# ── Baca semua data dari SQLite ───────────────────────────────────────────────
if not os.path.exists(SQLITE_PATH):
    print(f"ERROR: File SQLite tidak ditemukan: {SQLITE_PATH}")
    sys.exit(1)

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row
cur = sqlite_conn.cursor()


def migrate_table(table_name, insert_sql, fetch_sql, transform_fn=None):
    cur.execute(fetch_sql)
    rows = cur.fetchall()
    if not rows:
        print(f"  {table_name}: tidak ada data, skip.")
        return 0

    with pg_engine.begin() as conn:
        # Truncate dulu (hindari duplikat kalau script dijalankan ulang)
        conn.execute(text(f'TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE'))
        count = 0
        for row in rows:
            data = dict(row)
            if transform_fn:
                data = transform_fn(data)
            if data:
                conn.execute(text(insert_sql), data)
                count += 1

    print(f"  {table_name}: {count} baris dimigrasikan.")
    return count


# ── 1. transactions ───────────────────────────────────────────────────────────
print("Migrasi transactions...")
migrate_table(
    'transactions',
    """INSERT INTO transactions
       (id, date, capster_name, service_name, price, payment_method, branch, created_at)
       VALUES (:id, :date, :capster_name, :service_name, :price, :payment_method, :branch, :created_at)""",
    "SELECT id, date, capster_name, service_name, price, payment_method, branch, created_at FROM transactions"
)

# ── 2. capsters ───────────────────────────────────────────────────────────────
print("Migrasi capsters...")
migrate_table(
    'capsters',
    """INSERT INTO capsters
       (id, name, telegram_id, alias, employment_type, commission_rate, monthly_salary, branch_id)
       VALUES (:id, :name, :telegram_id, :alias, :employment_type, :commission_rate, :monthly_salary, :branch_id)""",
    "SELECT id, name, telegram_id, alias, employment_type, commission_rate, monthly_salary, branch_id FROM capsters"
)

# ── 3. services ───────────────────────────────────────────────────────────────
print("Migrasi services...")
migrate_table(
    'services',
    """INSERT INTO services (service_id, name, category, price)
       VALUES (:service_id, :name, :category, :price)""",
    "SELECT service_id, name, category, price FROM services"
)

# ── 4. branches ───────────────────────────────────────────────────────────────
print("Migrasi branches...")
migrate_table(
    'branches',
    """INSERT INTO branches
       (branch_id, name, location, short, employees, commission_rate,
        cost_tempat, cost_listrik_air, cost_wifi, cost_karyawan)
       VALUES (:branch_id, :name, :location, :short, :employees, :commission_rate,
               :cost_tempat, :cost_listrik_air, :cost_wifi, :cost_karyawan)""",
    "SELECT branch_id, name, location, short, employees, commission_rate, cost_tempat, cost_listrik_air, cost_wifi, cost_karyawan FROM branches"
)

# ── 5. products ───────────────────────────────────────────────────────────────
print("Migrasi products...")
migrate_table(
    'products',
    "INSERT INTO products (product_id, name, price) VALUES (:product_id, :name, :price)",
    "SELECT product_id, name, price FROM products"
)

# ── 6. salary_withdrawals ─────────────────────────────────────────────────────
print("Migrasi salary_withdrawals...")
migrate_table(
    'salary_withdrawals',
    """INSERT INTO salary_withdrawals
       (id, date, capster_name, telegram_id, amount, period_start, period_end, note)
       VALUES (:id, :date, :capster_name, :telegram_id, :amount, :period_start, :period_end, :note)""",
    "SELECT id, date, capster_name, telegram_id, amount, period_start, period_end, note FROM salary_withdrawals"
)

# ── 7. customers ──────────────────────────────────────────────────────────────
print("Migrasi customers...")
migrate_table(
    'customers',
    "INSERT INTO customers (id, name, phone) VALUES (:id, :name, :phone)",
    "SELECT id, name, phone FROM customers"
)

sqlite_conn.close()

# ── Reset auto-increment sequences di PostgreSQL ─────────────────────────────
print("\nReset sequences PostgreSQL...")
with pg_engine.begin() as conn:
    for tbl, col in [
        ('transactions', 'id'),
        ('capsters', 'id'),
        ('customers', 'id'),
        ('salary_withdrawals', 'id'),
    ]:
        conn.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{tbl}', '{col}'), "
            f"COALESCE((SELECT MAX({col}) FROM {tbl}), 0) + 1, false)"
        ))
        print(f"  Sequence {tbl}.{col} direset.")

print("\n✅ Migrasi selesai! Semua data sudah di PostgreSQL.")
print("   Jalankan: python run_dashboard.py")
