"""Final comprehensive audit — screening + probes + regression check."""
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_final_audit.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

from web import create_app
from app.db.repository import Repository

app = create_app()
repo = Repository()

TOTAL_PASS = 0
TOTAL_FAIL = 0
FAIL_LIST = []

def check(name, condition, detail=''):
    global TOTAL_PASS, TOTAL_FAIL
    status = 'PASS' if condition else 'FAIL'
    if condition:
        TOTAL_PASS += 1
    else:
        TOTAL_FAIL += 1
        FAIL_LIST.append(f'{name}: {detail}')
    L(f'  [{status}] {name}' + (f' — {detail}' if detail else ''))
    return condition

# ============================================================
# 1. Boot + registrasi
# ============================================================
L('=== 1. Boot Flask ===')
check('Flask create_app OK', True, f'{len(app.blueprints)} blueprints')
expected_bps = {'api','branches','capster_portal','capsters','compare','customers','home',
                'products','profit','promos','public','report_daily','report_weekly',
                'services','transactions','withdraw'}
check('All 16 blueprints registered', set(app.blueprints.keys()) == expected_bps)

# ============================================================
# 2. Semua route admin dengan session
# ============================================================
L('\n=== 2. All admin routes (with session) ===')
admin = app.test_client()
with admin.session_transaction() as sess:
    sess['logged_in'] = True

admin_routes = {
    '/':                     (200,),
    '/admin':                (200,),
    '/transactions':         (200,),
    '/transactions/export':  (200,),
    '/capsters':             (200,),
    '/capsters/manage':      (200,),
    '/withdraw':             (200,),
    '/profit':               (200,),
    '/profit?year=2026&month=7': (200,),
    '/compare':              (200,),
    '/compare?year=2026&month=7': (200,),
    '/report/daily':         (200,),
    '/report/daily?date=2026-07-25': (200,),
    '/report/weekly':        (200,),
    '/report/weekly?week=2026-07-20': (200,),
    '/customers':            (200,),
    '/customers?q=tama':     (200,),
    '/services':             (200,),
    '/products':             (200,),
    '/products/stock':       (200,),
    '/promos':               (200,),
    '/branches':             (200,),
    # API
    '/api/notifications':                    (200,),
    '/api/chart/revenue-daily?days=30':      (200,),
    '/api/chart/branch-split?year=2026&month=7': (200,),
    '/api/chart/payment-split?year=2026&month=7': (200,),
    '/api/chart/top-services?year=2026&month=7':  (200,),
}
for url, expected in admin_routes.items():
    r = admin.get(url)
    ok = r.status_code in expected
    check(f'GET {url}', ok, f'status={r.status_code}')

# Customer-specific
cust = repo.get_all_customers()
if cust:
    sample = cust[0]
    r = admin.get(f'/customers/{sample["id"]}/loyalty')
    check(f'GET /customers/{sample["id"]}/loyalty', r.status_code == 200, f'status={r.status_code}')

# ============================================================
# 3. Portal routes
# ============================================================
L('\n=== 3. Portal routes (with capster session) ===')
caps = repo.get_all_capsters()
if caps:
    target = next((c for c in caps if c.get('Username')), caps[0])
    portal = app.test_client()
    with portal.session_transaction() as sess:
        sess['capster_logged_in']   = True
        sess['capster_id']          = target['id']
        sess['capster_name']        = target['Name']
        sess['capster_telegram_id'] = target.get('TelegramID')
        sess['capster_alias']       = target.get('Alias', '')
        sess['capster_type']        = target.get('EmploymentType', 'mitra')
        sess['capster_rate']        = target.get('CommissionRate', 0.5)
        sess['capster_salary']      = target.get('MonthlySalary', 0)
        sess['capster_branch_id']   = target.get('BranchID', '')

    portal_routes = ['/portal/', '/portal/transactions', '/portal/earnings',
                     '/portal/withdraw', '/portal/profile', '/portal/add-transaction',
                     '/portal/customers']
    for url in portal_routes:
        r = portal.get(url)
        check(f'GET {url} (capster session)', r.status_code == 200, f'status={r.status_code}')

# ============================================================
# 4. Auth boundary (no session)
# ============================================================
L('\n=== 4. Auth boundary (no session) ===')
noauth = app.test_client()
for url in ['/admin', '/capsters', '/withdraw', '/customers', '/services',
            '/profit', '/compare', '/branches', '/products']:
    r = noauth.get(url, follow_redirects=False)
    check(f'{url} redirect w/o auth', r.status_code == 302, f'status={r.status_code}')
r = noauth.get('/api/notifications', follow_redirects=False)
check('/api/notifications requires auth', r.status_code == 401, f'status={r.status_code}')
for url in ['/portal/', '/portal/earnings', '/portal/withdraw']:
    r = noauth.get(url, follow_redirects=False)
    check(f'{url} redirect w/o capster session', r.status_code == 302, f'status={r.status_code}')

# ============================================================
# 5. Edge cases (bad params)
# ============================================================
L('\n=== 5. Edge case handling (bad input) ===')
edge_tests = [
    ('/profit?year=abc&month=xy', 200, 'profit non-int params'),
    ('/profit?year=2026&month=13', 200, 'profit month out of range'),
    ('/profit?year=2026&month=0', 200, 'profit month zero'),
    ('/report/daily?date=2999-99-99', 200, 'daily bad date'),
    ('/report/weekly?week=NOTADATE', 200, 'weekly bad param'),
    ('/compare?year=2030&month=6', 200, 'compare future'),
    ('/transactions?type=invalid', 200, 'transactions bad type'),
    ('/customers/999999/loyalty', 302, 'non-existent customer'),
    ('/customers/notanumber/loyalty', 404, 'non-numeric URL'),
]
for url, expected, label in edge_tests:
    r = admin.get(url)
    check(f'{label} ({url})', r.status_code == expected, f'status={r.status_code}')

# ============================================================
# 6. XSS defense (K-14)
# ============================================================
L('\n=== 6. XSS defense — customer phone validation ===')
from web.routes.customers import _is_valid_phone
xss_tests = [
    ('', True, 'empty'),
    ('081234567890', True, 'normal'),
    ('+62 812-3456', True, 'with symbols'),
    ("'; alert(1); //", False, 'JS injection payload'),
    ('<script>alert(1)</script>', False, 'HTML tag'),
    ('javascript:alert(1)', False, 'js URL scheme'),
    ('a' * 40, False, 'too long'),
    ("' onerror=alert(1) '", False, 'event handler'),
]
for phone, expected, label in xss_tests:
    got = _is_valid_phone(phone)
    check(f'phone regex — {label}: {phone[:25]!r}', got == expected, f'got={got}')

# ============================================================
# 7. XSS render (tojson|forceescape)
# ============================================================
L('\n=== 7. Template render — no HTML injection via onclick ===')
r = admin.get('/customers')
body = r.get_data(as_text=True)
# Should not have raw quotes inside onclick attributes
broken_pattern = re.findall(r'onclick="[^"]*"[a-zA-Z]', body)
check('No broken onclick in /customers', len(broken_pattern) == 0,
      f'found {len(broken_pattern)} broken')
# Should have &#34; (encoded quotes) in onclick
encoded_pattern = re.findall(r'onclick="[^"]*&#34;[^"]*"', body)
check('Onclick uses encoded quotes', len(encoded_pattern) > 0,
      f'found {len(encoded_pattern)} encoded onclick')

# ============================================================
# 8. Stock guard (K-9)
# ============================================================
L('\n=== 8. Stock guard on add_product_sale ===')
products = repo.get_all_products()
branches = repo.get_all_branches_config()
if products and branches:
    p = products[0]
    b = branches[0]
    stocks = repo.get_product_stocks(branch_id=b['BranchID'])
    stock_row = next((s for s in stocks if s['ProductID'] == p['ProductID']), None)
    current = stock_row['Quantity'] if stock_row else 0

    ok, err = repo.add_product_sale(
        capster_name='__audit_test__',
        product_id=p['ProductID'],
        product_name=p['Name'],
        price_each=p['Price'],
        quantity=current + 100,
        commission_rate=p.get('CommissionRate', 0),
        branch_id=b['BranchID'],
    )
    check('Over-stock sale rejected', not ok, f'err={err!r}')

    # Verify stock unchanged
    stocks2 = repo.get_product_stocks(branch_id=b['BranchID'])
    stock2 = next((s for s in stocks2 if s['ProductID'] == p['ProductID']), None)
    current_after = stock2['Quantity'] if stock2 else 0
    check('Stock not decremented after reject', current == current_after,
          f'{current} → {current_after}')

# ============================================================
# 9. Profit uses DB (K-4)
# ============================================================
L('\n=== 9. calc_profit uses DB (not constants) ===')
from app.services.reports import calc_profit
import inspect
src = inspect.getsource(calc_profit)
check('calc_profit does NOT import constants.BRANCHES',
      'BRANCHES.items()' not in src,
      'still uses constants.BRANCHES.items()')
check('calc_profit uses repo.get_all_branches_config()',
      'get_all_branches_config' in src)
check('calc_profit reads Cost_tempat from DB',
      'Cost_tempat' in src)
# Actual test
data = calc_profit(repo, 2026, 7)
check('calc_profit returns non-empty for 2026-07', bool(data.get('branches')))

# ============================================================
# 10. Withdraw guard exists (K-1)
# ============================================================
L('\n=== 10. Withdraw guard code exists ===')
from web.routes.withdraw import _build_capster_balances, withdraw_add
withdraw_src = inspect.getsource(withdraw_add)
check('withdraw_add checks amount > available',
      'amount > available' in withdraw_src,
      'guard code not found in withdraw_add')
check('withdraw_add validates period start <= end',
      'parsed_start > parsed_end' in withdraw_src)
balances = _build_capster_balances(repo)
check('_build_capster_balances returns id field',
      all('id' in b for b in balances) if balances else True)

# ============================================================
# 11. capster_id refactor consistency
# ============================================================
L('\n=== 11. capster_id refactor — telegram_id references ===')
# Grep files for lingering telegram_id as identifier
import glob
files_to_check = glob.glob('web/routes/*.py')
issues = []
for fpath in files_to_check:
    with open(fpath, encoding='utf-8') as f:
        content = f.read()
    # Cari pattern: telegram_id sebagai argument function repo.xxx(telegram_id)
    bad_calls = re.findall(r'repo\.(get_withdrawals|update_capster|remove_capster|update_capster_password|set_capster_credentials)\((?![^)]*capster_id)', content)
    if bad_calls:
        issues.append(f'{fpath}: {bad_calls}')
check('No repo calls with telegram_id as identifier',
      len(issues) == 0, f'issues: {issues}')

# ============================================================
# 12. DB integrity
# ============================================================
L('\n=== 12. DB integrity ===')
from app.db.database import get_db
from sqlalchemy import text
with get_db() as s:
    orphan = s.execute(text('SELECT COUNT(*) FROM salary_withdrawals WHERE capster_id IS NULL')).scalar()
    check('No orphan withdrawals (capster_id NULL)', orphan == 0, f'{orphan} orphans')
    total_wd = s.execute(text('SELECT COUNT(*) FROM salary_withdrawals')).scalar()
    L(f'  Total withdrawals: {total_wd}')
    tama = s.execute(text("SELECT id, telegram_id, saldo_adjustment FROM capsters WHERE name ILIKE '%tama%'")).fetchone()
    if tama:
        L(f'  Tama: id={tama[0]}, telegram_id={tama[1]}, adjustment=Rp {tama[2]:,}'.replace(',', '.'))

# ============================================================
# 13. .env.example correctness
# ============================================================
L('\n=== 13. .env.example content ===')
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env.example')
with open(env_path) as f:
    envx = f.read()
check('DEBUG=False default', 'DEBUG=False' in envx and 'DEBUG=True' not in envx)
check('Uses PORT (not DASHBOARD_PORT)',
      'PORT=' in envx and 'DASHBOARD_PORT=' not in envx)
check('SECRET_KEY required for QR HMAC', 'SECRET_KEY=' in envx)

# ============================================================
# 14. Bot removal — no leftover
# ============================================================
L('\n=== 14. Bot Telegram removal completeness ===')
check('bot/ folder gone', not os.path.exists('bot'))
check('run_bot.py gone', not os.path.exists('run_bot.py'))
check('requirements.txt no python-telegram-bot',
      'python-telegram-bot' not in open('requirements.txt').read())
# Grep for lingering "from bot" or "import telegram"
py_files = glob.glob('web/**/*.py', recursive=True) + glob.glob('app/**/*.py', recursive=True) + glob.glob('*.py')
bot_imports = []
for f in py_files:
    with open(f, encoding='utf-8') as fh:
        c = fh.read()
    if re.search(r'^from bot|^import bot\b|^from telegram|^import telegram', c, re.M):
        bot_imports.append(f)
check('No bot/telegram imports in code', len(bot_imports) == 0, f'files: {bot_imports}')

# ============================================================
# SUMMARY
# ============================================================
L('\n' + '=' * 60)
L(f'FINAL AUDIT SUMMARY')
L('=' * 60)
L(f'  Total checks: {TOTAL_PASS + TOTAL_FAIL}')
L(f'  PASSED: {TOTAL_PASS}')
L(f'  FAILED: {TOTAL_FAIL}')
if FAIL_LIST:
    L('\nFAILURES:')
    for f in FAIL_LIST:
        L(f'  - {f}')
else:
    L('\n*** ALL CHECKS PASSED ***')
logf.close()
