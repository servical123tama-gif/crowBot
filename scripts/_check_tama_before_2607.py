"""Cek saldo Tama sebelum 2026-07-26."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.database import get_db
from app.db.models import Capster, SalaryWithdrawal
from app.db.repository import Repository
from datetime import datetime
import pandas as pd

CUTOFF = datetime(2026, 7, 26, 0, 0, 0)   # sebelum 26 Juli = strict less-than

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_tama_check.txt')
logf = open(LOG_PATH, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

with get_db() as s:
    tama = s.query(Capster).filter(Capster.name.ilike('%tama%')).first()
    L(f'Tama: id={tama.id}, name={tama.name}, type={tama.employment_type}, rate={tama.commission_rate}, salary={tama.monthly_salary}, adjustment={tama.saldo_adjustment}')
    tid = tama.id
    trate = tama.commission_rate
    tsalary = tama.monthly_salary
    tetype = tama.employment_type
    tname = tama.name
    tadj = tama.saldo_adjustment

repo = Repository()

# Semua tx Tama sepanjang waktu
now = datetime.now()
all_dfs = []
for y in range(2024, now.year + 1):
    df = repo.get_transactions_dataframe(year=y)
    if not df.empty:
        all_dfs.append(df)
all_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
cap_df = all_df[all_df['Capster'].str.lower() == tname.lower()]

L('')
L(f'=== TRANSAKSI TAMA sampai sebelum {CUTOFF.date()} ===')
tx_before = cap_df[cap_df['Date'] < CUTOFF]
tx_after  = cap_df[cap_df['Date'] >= CUTOFF]
rev_before = int(tx_before['Price'].sum())
rev_after  = int(tx_after['Price'].sum())
L(f'  tx sebelum {CUTOFF.date()}: {len(tx_before)} tx, revenue Rp {rev_before:,}'.replace(',', '.'))
L(f'  tx 26 Juli & sesudahnya: {len(tx_after)} tx, revenue Rp {rev_after:,}'.replace(',', '.'))

L('')
L('  Per bulan:')
for m, g in cap_df.groupby(cap_df['Date'].dt.strftime('%Y-%m')):
    rev = int(g['Price'].sum())
    L(f'    {m}: {len(g)} tx, Rp {rev:,}'.replace(',', '.'))

# Earnings mitra formula
earned_all_time = int(int(cap_df['Price'].sum()) * trate)
earned_before_2607 = int(rev_before * trate)

L('')
L('=== WITHDRAWAL TAMA ===')
with get_db() as s:
    wds = s.query(SalaryWithdrawal).filter(SalaryWithdrawal.capster_id == tid).order_by(SalaryWithdrawal.date).all()
    L('  Semua withdrawal:')
    total_wd_all = 0
    total_wd_before = 0
    for w in wds:
        total_wd_all += w.amount
        marker = ''
        if w.date < CUTOFF:
            total_wd_before += w.amount
            marker = ' [SEBELUM 26 JULI]'
        L(f'    id={w.id} date={w.date}  amount=Rp {w.amount:,}  period={w.period_start}..{w.period_end}  note={w.note!r}{marker}'.replace(',', '.'))
    L(f'  Total wd all-time: Rp {total_wd_all:,}'.replace(',', '.'))
    L(f'  Total wd SEBELUM 2026-07-26: Rp {total_wd_before:,}'.replace(',', '.'))

# Product commission
prod = repo.get_product_sales_commission_total(tname)
L(f'\nProduct commission (all-time): Rp {prod:,}'.replace(',', '.'))
L(f'Saldo adjustment: Rp {tadj:,}'.replace(',', '.'))

L('')
L('=== SALDO SAAT INI (all-time, sesuai UI) ===')
saldo_now = earned_all_time + prod - total_wd_all + tadj
L(f'  = ({int(cap_df["Price"].sum()):,} × {trate}) + {prod:,} − {total_wd_all:,} + {tadj:,}'.replace(',', '.'))
L(f'  = {earned_all_time:,} + {prod:,} − {total_wd_all:,} + {tadj:,}'.replace(',', '.'))
L(f'  = Rp {saldo_now:,}'.replace(',', '.'))

L('')
L(f'=== SALDO SEBELUM 2026-07-26 ===')
L(f'  (Anggap tx & withdrawal setelah 26 Juli belum ada)')
saldo_before = earned_before_2607 + prod - total_wd_before + tadj
L(f'  = (rev_before × rate) + prod − wd_before + adj')
L(f'  = ({rev_before:,} × {trate}) + {prod:,} − {total_wd_before:,} + {tadj:,}'.replace(',', '.'))
L(f'  = {earned_before_2607:,} + {prod:,} − {total_wd_before:,} + {tadj:,}'.replace(',', '.'))
L(f'  = Rp {saldo_before:,}'.replace(',', '.'))

logf.close()
