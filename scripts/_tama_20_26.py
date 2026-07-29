"""Detail Tama untuk periode 20-26 Juli 2026."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from app.db.repository import Repository
from datetime import datetime
import pandas as pd

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_tama_periode.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

repo = Repository()
df = repo.get_transactions_dataframe(year=2026)
tama_df = df[df['Capster'].str.lower() == 'tama'] if not df.empty else pd.DataFrame()

start = datetime(2026, 7, 20)
end   = datetime(2026, 7, 26, 23, 59, 59)

window = tama_df[(tama_df['Date'] >= start) & (tama_df['Date'] <= end)]
L(f'=== TRANSAKSI TAMA 20-26 JULI 2026 ===')
L(f'  Jumlah tx: {len(window)}')
rev = int(window["Price"].sum()) if not window.empty else 0
L(f'  Revenue: Rp {rev:,}'.replace(',', '.'))
earned = int(rev * 0.5)
L(f'  Earnings (mitra 50%): Rp {earned:,}'.replace(',', '.'))
L('')
L('  Per hari (20-26 Juli):')
for d in range(20, 27):
    day = datetime(2026, 7, d)
    day_end = datetime(2026, 7, d, 23, 59, 59)
    dtx = tama_df[(tama_df['Date'] >= day) & (tama_df['Date'] <= day_end)]
    if not dtx.empty:
        drev = int(dtx['Price'].sum())
        L(f'    {day.strftime("%d Jul")}: {len(dtx)} tx, Rp {drev:,} (komisi Rp {int(drev*0.5):,})'.replace(',', '.'))
    else:
        L(f'    {day.strftime("%d Jul")}: 0 tx')

logf.close()
