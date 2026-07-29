import sys
sys.path.insert(0, 'D:/Document/barber/bot_barber_2')

from app.db.repository import Repository
import pandas as pd
from datetime import datetime

db = Repository()

# Semua withdrawal
print('=== SEMUA WITHDRAWAL ===')
wds = db.get_all_withdrawals()
for w in wds:
    print(w)
print(f'Total records: {len(wds)}')
print()

# Semua transaksi bulan Juli 2026
print('=== TRANSAKSI JULI 2026 ===')
df = db.get_transactions_dataframe(year=2026)
if not df.empty:
    if 'Date' in df.columns:
        df['YM'] = df['Date'].dt.strftime('%Y-%m')
        july = df[df['YM'] == '2026-07']
        print(f'Total transaksi Juli: {len(july)}')
        if not july.empty:
            for name, grp in july.groupby('Capster'):
                rev = int(grp['Price'].sum())
                print(f'  {name}: {len(grp)} tx | Rp {rev:,}')
print()

# Saldo semua capster
print('=== SALDO SEMUA CAPSTER ===')
capsters = db.get_all_capsters()
all_dfs = []
for y in range(2024, datetime.now().year + 1):
    df_y = db.get_transactions_dataframe(year=y)
    if not df_y.empty:
        all_dfs.append(df_y)
all_time_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

for c in capsters:
    name   = c.get('Name','')
    alias  = c.get('Alias','')
    etype  = (c.get('EmploymentType') or 'mitra').lower()
    rate   = c.get('CommissionRate', 0.5)
    salary = c.get('MonthlySalary', 0)
    tid    = c.get('TelegramID', 0)

    names_lower = {name.lower()}
    if alias:
        names_lower.add(alias.lower())

    if not all_time_df.empty and 'Capster' in all_time_df.columns:
        cap_df = all_time_df[all_time_df['Capster'].str.lower().isin(names_lower)]
    else:
        cap_df = pd.DataFrame()

    if etype == 'mitra':
        rev_all    = int(cap_df['Price'].sum()) if not cap_df.empty else 0
        earned_all = int(rev_all * rate)
    else:
        distinct_months = cap_df['Date'].dt.strftime('%Y-%m').nunique() if (not cap_df.empty and 'Date' in cap_df.columns) else 0
        earned_all = distinct_months * salary

    prod_comm   = db.get_product_sales_commission_total(name)
    withdrawals = db.get_withdrawals(tid)
    withdrawn_all = sum(w.get('Amount', 0) for w in withdrawals)
    balance = earned_all + prod_comm - withdrawn_all

    print(f'  {name} [{etype}] earned={earned_all:,} prod={prod_comm:,} wd={withdrawn_all:,} => SALDO={balance:,}')
