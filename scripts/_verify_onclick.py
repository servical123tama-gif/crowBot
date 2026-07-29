"""Verify onclick handlers render dengan HTML+JS valid setelah tojson|forceescape."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_onclick_verify.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

from web import create_app
app = create_app()
client = app.test_client()
with client.session_transaction() as sess:
    sess['logged_in'] = True

L('=== /customers ===')
r = client.get('/customers')
body = r.get_data(as_text=True)
# Extract onclick attributes
patterns = ['sendQR', 'openQR', 'openEdit', 'openDelete', 'openProfile']
for p in patterns:
    matches = re.findall(rf'onclick="{re.escape(p)}\([^"]*"', body)
    if matches:
        L(f'  {p} x {len(matches)} sample: {matches[0][:200]}')

# Cek apakah ada broken onclick: attribute yang berakhir di tengah JS
# Broken kalau: onclick="foo("bar")" - HTML parser lihat 2 attribute
broken = re.findall(r'onclick="[^"]*"[a-zA-Z]', body)
L(f'  Broken onclick pattern (raw quote leak): {len(broken)}')
if broken:
    L(f'  First broken: {broken[0][:300]}')

L('\n=== /capsters/manage ===')
r = client.get('/capsters/manage')
body = r.get_data(as_text=True)
for p in [r'openSetPwd\(', r'onsubmit="return confirm']:
    matches = re.findall(rf'{p}[^"]*"', body[:20000])
    for m in matches[:2]:
        L(f'  sample: {m[:200]}')

L('\n=== /services ===')
r = client.get('/services')
body = r.get_data(as_text=True)
matches = re.findall(r'onsubmit="return confirm[^"]*"', body)
for m in matches[:2]:
    L(f'  sample: {m[:200]}')

L('\n=== /branches ===')
r = client.get('/branches')
body = r.get_data(as_text=True)
matches = re.findall(r'onsubmit="return confirm[^"]*"', body)
for m in matches[:2]:
    L(f'  sample: {m[:200]}')

L('\n=== /products/stock ===')
r = client.get('/products/stock')
body = r.get_data(as_text=True)
matches = re.findall(r'onclick="openStockModal[^"]*"', body)
for m in matches[:2]:
    L(f'  sample: {m[:200]}')

L('\nCEK MANUAL: attribute onclick harus terminate dengan " tanpa " di tengah.')
logf.close()
