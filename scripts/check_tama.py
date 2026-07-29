from app.db.repository import Repository
import pandas as pd
from datetime import datetime

db = Repository()

# Cari data Tama
capsters = db.get_all_capsters()
tama = next((c for c in capsters if 'tama' in c.get('Name','').lower() or 'tama' in c.get('Alias','').lower()), None)
print('=== DATA CAPSTER TAMA ===')
print(tama)
print()

if tama:
    name   = tama.get('Name','')
    alias  = tama.get('Alias','')
    etype  = (tama.get('EmploymentType') or 'mitra').lower()
    rate   = tama.get('CommissionRate', 0.5)
    salary = tama.get('MonthlySalary', 0)
    tid    = tama.get('TelegramID', 0)
    print(f'Status saat ini : {etype}')
    print(f'Commission rate : {rate}')
    print(f'Gaji tetap (lama): Rp {salary:,}')
    print()

    # All-time transactions
    all_dfs = []
    for y in range(2024, datetime.now().year + 1):
        df_y = db.get_transactions_dataframe(year=y)
        if not df_y.empty:
            all_dfs.append(df_y)
    all_time_df = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

    names_lower = {name.lower()}
    if alias:
        names_lower.add(alias.lower())

    if not all_time_df.empty and 'Capster' in all_time_df.columns:
        cap_df = all_time_df[all_time_df['Capster'].str.lower().isin(names_lower)]
    else:
        cap_df = pd.DataFrame()

    print('=== TRANSAKSI ALL-TIME ===')
    total_rev = 0
    if not cap_df.empty:
        total_rev = int(cap_df['Price'].sum())
        print(f'Total transaksi : {len(cap_df)} baris')
        print(f'Total revenue   : Rp {total_rev:,}')
        if 'Date' in cap_df.columns:
            monthly = cap_df.copy()
            monthly['YM'] = monthly['Date'].dt.strftime('%Y-%m')
            print('\nPer bulan:')
            for ym, grp in monthly.groupby('YM'):
                rev = int(grp['Price'].sum())
                kom = int(rev * rate)
                print(f'  {ym}: {len(grp)} tx | revenue Rp {rev:,} | komisi Rp {kom:,}')
            distinct_months = monthly['YM'].nunique()
            gaji_tetap_total = distinct_months * salary
            print(f'\nTotal distinct bulan    : {distinct_months}')
            print(f'Earned JIKA tetap       : {distinct_months} x Rp {salary:,} = Rp {gaji_tetap_total:,}')
    else:
        print('Tidak ada transaksi')
    print()

    # Withdrawals
    withdrawals = db.get_withdrawals(tid)
    print('=== WITHDRAWAL ALL-TIME ===')
    total_wd = 0
    for w in withdrawals:
        amt  = w.get('Amount', 0)
        date = w.get('Date', '')
        note = w.get('Note', '')
        total_wd += amt
        print(f'  {date} | Rp {amt:,} | {note}')
    print(f'\n  TOTAL withdrawn: Rp {total_wd:,}')
    print()

    # Product commission
    prod_comm = db.get_product_sales_commission_total(name)
    print(f'=== KOMISI PRODUK: Rp {prod_comm:,} ===')
    print()

    # Saldo sebagai MITRA (cara sistem saat ini)
    earned_mitra = int(total_rev * rate)
    saldo_mitra  = earned_mitra + prod_comm - total_wd
    print('=== SALDO DIHITUNG SEBAGAI MITRA (sistem saat ini) ===')
    print(f'  earned komisi all-time : Rp {earned_mitra:,}')
    print(f'  + komisi produk        : Rp {prod_comm:,}')
    print(f'  - withdrawn all-time   : Rp {total_wd:,}')
    print(f'  = SALDO                : Rp {saldo_mitra:,}')
