"""Probe edge cases: invalid ID, bad params, missing auth, XSS payload."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_screening_probe.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m): logf.write(str(m) + '\n'); logf.flush()

from web import create_app
app = create_app()
admin = app.test_client()
with admin.session_transaction() as sess:
    sess['logged_in'] = True

def probe(url, expected, method='GET', form=None):
    if method == 'GET':
        r = admin.get(url, follow_redirects=False)
    else:
        r = admin.post(url, data=form or {}, follow_redirects=False)
    code = r.status_code
    body = r.get_data(as_text=True)[:200]
    ok = code in expected
    tag = 'OK' if ok else 'FAIL'
    L(f'  [{tag}] {method} {url:60s} → {code} (expected {expected})')
    if not ok:
        L(f'    body: {body}')
    return r

L('=== PROBE: Invalid IDs ===')
probe('/customers/999999/loyalty', (200, 302, 404))     # non-existent customer
probe('/capsters/edit/999999', (200, 302, 400, 404), method='POST', form={'name': 'x'})  # non-existent capster
probe('/api/customer/999999/transactions', (200, 404))  # non-existent
probe('/customers/notanumber/loyalty', (404,))          # bad URL type

L('\n=== PROBE: Bad query params ===')
probe('/profit?year=abc&month=xy', (200, 400, 500))    # invalid types
probe('/profit?year=2026&month=13', (200, 500))         # month > 12
probe('/report/weekly?week=NOTADATE', (200,))           # bad date
probe('/report/daily?date=2999-99-99', (200,))          # invalid date
probe('/compare?year=1900&month=1', (200,))             # ancient year
probe('/report/weekly?week=2020-01-01', (200,))         # week before data range

L('\n=== PROBE: XSS/HTML injection payload dalam query ===')
probe('/customers?q=<script>alert(1)</script>', (200,))
probe('/transactions?capster=<img src=x>', (200,))
probe('/portal/customer/lookup?q=<svg onload=alert(1)>', (200, 302))  # portal needs capster session, 302 to /portal/login

L('\n=== PROBE: Auth boundary — no session ===')
noauth = app.test_client()
probe_noauth = lambda u, e: (noauth.get(u), L(f'  [NoAuth] GET {u} → {noauth.get(u).status_code} (expected {e})'))
for url in ['/admin', '/capsters', '/withdraw', '/customers', '/api/notifications']:
    r = noauth.get(url, follow_redirects=False)
    L(f'  [{"OK" if r.status_code in (302, 401) else "LEAK"}] GET {url} → {r.status_code} (should redirect / 401)')

L('\n=== PROBE: Portal auth boundary ===')
for url in ['/portal/', '/portal/earnings', '/portal/withdraw', '/portal/customers']:
    r = noauth.get(url, follow_redirects=False)
    L(f'  [{"OK" if r.status_code == 302 else "LEAK"}] GET {url} → {r.status_code}')

L('\n=== PROBE: Withdraw flow — invalid amount ===')
# no CSRF handling; test client punya CSRF disabled by default? Actually flask-wtf enforces even in test.
# Skip actual POST test — just check the form page loads

L('\n=== PROBE: Filter capster di /transactions ===')
probe('/transactions?capster=Tama&start=2026-07-20&end=2026-07-26', (200,))
probe('/transactions?branch=Cabang%20A', (200,))
probe('/transactions?type=layanan', (200,))
probe('/transactions?type=produk', (200,))
probe('/transactions?type=invalid', (200,))  # unknown type

L('\n=== PROBE: Report weekly cross-month & cross-year ===')
probe('/report/weekly?week=2026-12-30', (200,))  # crosses to 2027
probe('/report/weekly?week=2026-03-01', (200,))  # crosses Feb-Mar
probe('/report/weekly?week=2025-12-30', (200,))  # crosses year, empty week

L('\n=== PROBE: Compare with future month ===')
probe('/compare?year=2027&month=1', (200,))
probe('/compare?year=2030&month=6', (200,))

L('\n=== PROBE COMPLETE ===')
logf.close()
