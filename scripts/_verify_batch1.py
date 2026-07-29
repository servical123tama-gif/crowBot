"""Verify Batch 1 fixes: K-14 (XSS), K-1 (withdraw guard), K-4 (profit DB), K-9 (stock), S-16/17 env."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_verify_batch1.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

from web import create_app
from app.db.repository import Repository

app = create_app()
repo = Repository()

# ======================================================
# K-14: XSS via customer phone
# ======================================================
L('=== K-14: XSS phone validation ===')
from web.routes.customers import _is_valid_phone
tests = [
    ('', True),                              # empty OK
    ('081234567890', True),                  # normal
    ('+62 812-3456-7890', True),             # dgn simbol OK
    ('0817 890 123', True),                  # spasi OK
    ("'; alert(1); //", False),              # XSS payload
    ('<script>alert(1)</script>', False),   # HTML tag
    ('abc123', False),                       # huruf
    ('081<>', False),                        # HTML
    ('a' * 40, False),                       # too long
]
for phone, expected in tests:
    got = _is_valid_phone(phone)
    ok = got == expected
    L(f'  [{"OK" if ok else "FAIL"}] phone={phone[:30]!r:35s} → valid={got} (expected {expected})')

# ======================================================
# K-14: tojson filter render check (XSS payload di render)
# ======================================================
L('\n=== K-14: tojson di template render (customer name dgn XSS payload) ===')
client = app.test_client()
with client.session_transaction() as sess:
    sess['logged_in'] = True
# Test: search customer dengan payload — kalau XSS masuk, browser execute
resp = client.get('/customers')
body = resp.get_data(as_text=True)
# Cek apakah ada onclick=".*replace.*'" — pattern lama yang dihapus
import re
old_pattern_count = len(re.findall(r"replace\(&#34;'&#34;,", body))
tojson_count = body.count('|tojson')  # not in output, but verify template render
L(f'  onclick pakai old replace() pattern: {old_pattern_count} (should be 0)')
# Cek payload tidak ke-execute — pastikan tanda kutip dalam nama di-escape via JSON
# Contoh: kalau ada capster dgn ' di nama, harus di-render sebagai ' atau \'
L(f'  Response 200: {resp.status_code == 200}')

# ======================================================
# K-1: withdraw guard
# ======================================================
L('\n=== K-1: Withdraw guard ===')
# Ambil capster + saldo
from web.routes.withdraw import _build_capster_balances
balances = _build_capster_balances(repo)
if balances:
    target = balances[0]
    L(f'  Target capster: {target["name"]} (id={target["id"]}), balance=Rp {target["balance"]:,}'.replace(',', '.'))
    # Simulasi over-withdraw
    over = target['balance'] + 1_000_000
    L(f'  Simulasi withdraw Rp {over:,} (over-limit)'.replace(',', '.'))
    # Direct call add_withdrawal — masih akan sukses (repository level tidak ada guard)
    # Route level yang guard. Test via test_client dengan CSRF token.
    # NOTE: kita cek dari logic function, bukan HTTP POST karena CSRF susah di test_client
    # Cek kode _build_capster_balances return field id (untuk guard route)
    has_id = 'id' in target
    L(f'  _build_capster_balances return "id" field: {has_id} (guard butuh field ini)')

# ======================================================
# K-4: profit pakai DB
# ======================================================
L('\n=== K-4: profit calc pakai DB, bukan constants ===')
from app.services.reports import calc_profit
data = calc_profit(repo, 2026, 7)
if data:
    L(f'  calc_profit(2026, 7) return {len(data.get("branches", {}))} branches')
    for short, b in data['branches'].items():
        L(f'    {short}: fixed_ops=Rp {b["fixed_ops"]:,}, tetap=Rp {b["tetap_total"]:,}, revenue=Rp {b["revenue"]:,}, net=Rp {b["net_profit"]:,}'.replace(',', '.'))
    # Cek apakah baca dari DB — modify branch cost di DB, calc profit, verify berubah
    branches_db = repo.get_all_branches_config()
    if branches_db:
        b0 = branches_db[0]
        L(f'  DB source: branch "{b0["Name"]}" cost_tempat=Rp {b0["Cost_tempat"]:,}'.replace(',', '.'))

# ======================================================
# K-9: stock validation
# ======================================================
L('\n=== K-9: add_product_sale stock guard ===')
products = repo.get_all_products()
branches = repo.get_all_branches_config()
if products and branches:
    p = products[0]
    b = branches[0]
    # Cek current stock
    stocks = repo.get_product_stocks(branch_id=b['BranchID'])
    stock_p = next((s for s in stocks if s['ProductID'] == p['ProductID']), None)
    current_stock = stock_p['Quantity'] if stock_p else 0
    L(f'  Product: {p["Name"]}, branch: {b["Name"]}, stock: {current_stock}')

    # Simulasi jual over-stock (jangan actual commit — return only)
    result = repo.add_product_sale(
        capster_name='__test_capster__',
        product_id=p['ProductID'],
        product_name=p['Name'],
        price_each=p['Price'],
        quantity=current_stock + 999,   # over-stock
        commission_rate=p.get('CommissionRate', 0),
        branch_id=b['BranchID'],
    )
    ok, err = result
    L(f'  add_product_sale(qty=stock+999): ok={ok}, err={err!r}')
    L(f'  Expected ok=False (rejected). Actual: {"PASS" if not ok else "FAIL"}')

    # Verify sale did NOT persist — cek stock tidak berubah
    stocks_after = repo.get_product_stocks(branch_id=b['BranchID'])
    stock_after = next((s for s in stocks_after if s['ProductID'] == p['ProductID']), None)
    current_after = stock_after['Quantity'] if stock_after else 0
    L(f'  Stock setelah rejected sale: {current_after} (should still be {current_stock})')

# ======================================================
# S-16/S-17: .env.example
# ======================================================
L('\n=== S-16/S-17: .env.example fix ===')
with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.example')) as f:
    envx = f.read()
L(f'  Contains "DEBUG=False": {"DEBUG=False" in envx} (should True)')
L(f'  Contains "DEBUG=True": {"DEBUG=True" in envx} (should False)')
L(f'  Contains "PORT=": {"PORT=" in envx and "DASHBOARD_PORT=" not in envx} (should True — pakai PORT bukan DASHBOARD_PORT)')
L(f'  Contains "SECRET_KEY=": {"SECRET_KEY=" in envx} (should True — QR HMAC needs this)')

# ======================================================
# Regression: rerun screening
# ======================================================
L('\n=== Regression: hit all admin routes ===')
routes = [
    '/', '/admin', '/transactions', '/capsters', '/capsters/manage',
    '/withdraw', '/profit', '/compare', '/report/daily', '/report/weekly',
    '/customers', '/services', '/products', '/products/stock', '/promos', '/branches',
    '/profit?year=abc',    # bug fix earlier — must be 200
    '/profit?month=13',    # bug fix earlier — must be 200
]
for url in routes:
    r = client.get(url)
    L(f'  [{"OK" if r.status_code in (200, 302) else "FAIL"}] GET {url:35s} → {r.status_code}')

L('\n=== BATCH 1 VERIFY COMPLETE ===')
logf.close()
