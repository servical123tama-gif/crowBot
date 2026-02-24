"""
Verifikasi: bandingkan data Google Sheets vs SQLite DB.
Jalankan: python scripts/verify_migration.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.services.sheets_service import SheetsService
from app.db.repository import Repository
from datetime import datetime

GREEN = '\033[92m'
RED   = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def ok(msg):   print(f"{GREEN}  ✓ {msg}{RESET}")
def fail(msg): print(f"{RED}  ✗ {msg}{RESET}")
def warn(msg): print(f"{YELLOW}  ! {msg}{RESET}")
def header(msg): print(f"\n{'='*50}\n  {msg}\n{'='*50}")


def compare_counts(label, sheets_count, db_count):
    diff = db_count - sheets_count
    if sheets_count == db_count:
        ok(f"{label}: Sheets={sheets_count}  DB={db_count}  (sama)")
    elif diff > 0:
        warn(f"{label}: Sheets={sheets_count}  DB={db_count}  (+{diff} extra di DB)")
    else:
        fail(f"{label}: Sheets={sheets_count}  DB={db_count}  ({diff} kurang di DB)")


def main():
    print("\nMemulai verifikasi Sheets vs DB...")

    sheets = SheetsService()
    db     = Repository()
    year   = datetime.now().year

    # ── 1. Capsters ───────────────────────────────────────────
    header("1. CAPSTERS")
    s_cap = sheets.get_all_capsters()
    d_cap = db.get_all_capsters()
    compare_counts("Jumlah capster", len(s_cap), len(d_cap))

    s_ids = {str(r.get('TelegramID','')) for r in s_cap}
    d_ids = {str(r.get('TelegramID','')) for r in d_cap}
    missing = s_ids - d_ids
    extra   = d_ids - s_ids
    if missing: fail(f"TelegramID ada di Sheets tapi tidak di DB: {missing}")
    if extra:   warn(f"TelegramID ada di DB tapi tidak di Sheets: {extra}")
    if not missing and not extra: ok("Semua TelegramID cocok")

    # ── 2. Services ───────────────────────────────────────────
    header("2. SERVICES")
    s_svc = sheets.get_all_services()
    d_svc = db.get_all_services()
    compare_counts("Jumlah service", len(s_svc), len(d_svc))

    s_sids = {r.get('ServiceID','') for r in s_svc}
    d_sids = {r.get('ServiceID','') for r in d_svc}
    missing = s_sids - d_sids
    extra   = d_sids - s_sids
    if missing: fail(f"ServiceID ada di Sheets tapi tidak di DB: {missing}")
    if extra:   warn(f"ServiceID ada di DB tapi tidak di Sheets: {extra}")
    if not missing and not extra: ok("Semua ServiceID cocok")

    # ── 3. Branches ───────────────────────────────────────────
    header("3. BRANCHES")
    s_br = sheets.get_all_branches_config()
    d_br = db.get_all_branches_config()
    compare_counts("Jumlah branch", len(s_br), len(d_br))

    s_bids = {r.get('BranchID','') for r in s_br}
    d_bids = {r.get('BranchID','') for r in d_br}
    missing = s_bids - d_bids
    if missing: fail(f"BranchID ada di Sheets tapi tidak di DB: {missing}")
    if not missing: ok("Semua BranchID cocok")

    # ── 4. Products ───────────────────────────────────────────
    header("4. PRODUCTS")
    s_prd = sheets.get_all_products()
    d_prd = db.get_all_products()
    compare_counts("Jumlah product", len(s_prd), len(d_prd))

    # ── 5. Customers ──────────────────────────────────────────
    header("5. CUSTOMERS")
    s_cust = sheets.get_all_customers()
    d_cust = db.get_all_customers()
    compare_counts("Jumlah customer", len(s_cust), len(d_cust))

    # ── 6. Transactions ───────────────────────────────────────
    header(f"6. TRANSACTIONS ({year})")
    s_df = sheets.get_transactions_dataframe(year=year)
    d_df = db.get_transactions_dataframe(year=year)

    s_tx = len(s_df) if not s_df.empty else 0
    d_tx = len(d_df) if not d_df.empty else 0
    compare_counts(f"Jumlah transaksi {year}", s_tx, d_tx)

    if not s_df.empty and not d_df.empty:
        # Bandingkan per bulan
        print()
        s_by_month = s_df.groupby(s_df['Date'].dt.strftime('%Y-%m')).size()
        d_by_month = d_df.groupby(d_df['Date'].dt.strftime('%Y-%m')).size()
        all_months = sorted(set(s_by_month.index) | set(d_by_month.index))
        print(f"  {'Bulan':<12} {'Sheets':>8} {'DB':>8} {'Status':>10}")
        print(f"  {'-'*40}")
        for m in all_months:
            s_n = int(s_by_month.get(m, 0))
            d_n = int(d_by_month.get(m, 0))
            status = "OK" if s_n == d_n else f"DIFF ({d_n-s_n:+d})"
            mark = GREEN+"OK"+RESET if s_n == d_n else RED+f"DIFF ({d_n-s_n:+d})"+RESET
            print(f"  {m:<12} {s_n:>8} {d_n:>8}   {mark}")

        # Bandingkan total revenue
        s_rev = int(s_df['Price'].sum())
        d_rev = int(d_df['Price'].sum())
        print()
        if s_rev == d_rev:
            ok(f"Total revenue cocok: Rp {s_rev:,}")
        else:
            fail(f"Total revenue BEDA: Sheets=Rp {s_rev:,}  DB=Rp {d_rev:,}")

    # ── 7. Ringkasan ──────────────────────────────────────────
    header("RINGKASAN")
    print("  Jika ada DIFF di transactions:")
    print("  → Jalankan ulang: python scripts/migrate_from_sheets.py")
    print("  → Script idempotent, aman dijalankan berkali-kali\n")


if __name__ == '__main__':
    main()
