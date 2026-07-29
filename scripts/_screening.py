"""Comprehensive screening — hit setiap halaman admin + portal, cari 500/template error."""
import os, sys, re, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_screening_log.txt')
logf = open(LOG, 'w', encoding='utf-8')
def L(m):
    logf.write(str(m) + '\n')
    logf.flush()

try:
    from web import create_app
    from app.db.repository import Repository
    app = create_app()
    L('=== Flask app booted ===')
    L(f'Blueprints: {sorted(app.blueprints.keys())}')

    # Get some sample IDs for URL testing
    repo = Repository()
    caps = repo.get_all_capsters()
    cust_list = repo.get_all_customers()
    sample_capster = caps[0] if caps else None
    sample_cust    = cust_list[0] if cust_list else None
    L(f'Sample capster: id={sample_capster["id"] if sample_capster else None}, name={sample_capster["Name"] if sample_capster else None}')
    L(f'Sample customer: id={sample_cust["id"] if sample_cust else None}, name={sample_cust["Name"] if sample_cust else None}')

    def check_route(client, url, method='GET', form=None, expected=(200, 302), label=''):
        try:
            if method == 'GET':
                resp = client.get(url, follow_redirects=False)
            else:
                resp = client.post(url, data=form or {}, follow_redirects=False)
            code = resp.status_code
            body = resp.get_data(as_text=True)
            issues = []
            if code == 500:
                issues.append('500 ERROR')
            elif code not in expected:
                issues.append(f'unexpected {code}')

            # Detect Jinja/Python error strings in body
            error_markers = [
                ('Traceback', 'python traceback rendered'),
                ('UndefinedError', 'jinja undefined var'),
                ('TemplateSyntaxError', 'jinja syntax'),
                ('OperationalError', 'sqlalchemy op error'),
                ('AttributeError', 'attribute error'),
                ('TypeError:', 'type error'),
                ('KeyError:', 'key error'),
            ]
            for marker, desc in error_markers:
                if marker in body:
                    issues.append(f'body contains {marker} ({desc})')

            status = 'FAIL' if issues else 'OK'
            L(f'  [{status}] {method} {url:60s} → {code}   {"| " + ", ".join(issues) if issues else ""}')
            if issues and 'python traceback' in ','.join(issues).lower():
                # Extract first 400 chars of traceback
                tb_start = body.find('Traceback')
                L(f'         Body[traceback]: {body[tb_start:tb_start+500]}')
            return code, issues
        except Exception as e:
            L(f'  [EXCEPT] {method} {url} → {type(e).__name__}: {e}')
            return -1, [f'exception: {e}']

    # ========================================================
    # ADMIN routes
    # ========================================================
    L('\n=== ADMIN routes (with admin session) ===')
    admin = app.test_client()
    with admin.session_transaction() as sess:
        sess['logged_in'] = True

    admin_routes = [
        '/', '/admin',
        '/transactions', '/transactions/export',
        '/capsters', '/capsters/manage',
        '/withdraw',
        '/profit', '/profit?year=2026&month=7',
        '/compare', '/compare?year=2026&month=7',
        '/report/daily', '/report/daily?date=2026-07-25',
        '/report/weekly', '/report/weekly?week=2026-07-20',
        '/customers', '/customers?q=tama',
        '/services',
        '/products', '/products/stock',
        '/promos',
        '/branches',
    ]
    for url in admin_routes:
        check_route(admin, url)

    # Customer detail
    if sample_cust:
        check_route(admin, f'/customers/{sample_cust["id"]}/loyalty')
        check_route(admin, f'/customers/{sample_cust["id"]}/qr.png', expected=(200,))

    # API endpoints
    L('\n=== API routes ===')
    api_routes = [
        '/api/notifications',
        '/api/chart/revenue-daily?days=30',
        '/api/chart/branch-split?year=2026&month=7',
        '/api/chart/payment-split?year=2026&month=7',
        '/api/chart/top-services?year=2026&month=7',
    ]
    for url in api_routes:
        check_route(admin, url)
    if sample_cust:
        check_route(admin, f'/api/customer/{sample_cust["id"]}/transactions')

    # ========================================================
    # PORTAL routes (with capster session)
    # ========================================================
    L('\n=== PORTAL routes (with capster session) ===')
    portal = app.test_client()
    target = next((c for c in caps if c.get('Username')), caps[0] if caps else None)
    if target:
        L(f'Simulate portal session as capster id={target["id"]}, name={target["Name"]}, type={target["EmploymentType"]}')
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

        portal_routes = [
            '/portal/', '/portal/login',
            '/portal/dashboard',   # jika ada route ini
            '/portal/transactions',
            '/portal/earnings',
            '/portal/withdraw',
            '/portal/profile',
            '/portal/add-transaction',
            '/portal/customers',
            '/portal/customer/lookup?q=' + (sample_cust['Name'] if sample_cust else 'test'),
            '/portal/customer/check-phone?phone=' + (sample_cust.get('Phone', '') if sample_cust else '081'),
        ]
        for url in portal_routes:
            check_route(portal, url)

    # ========================================================
    # SPECIFIC saldo screening — cek Tama & semua capster
    # ========================================================
    L('\n=== SALDO CHECK — semua capster ===')
    # Simulasi request /capsters (list) untuk verify saldo tampil
    resp = admin.get('/capsters')
    body = resp.get_data(as_text=True)
    for c in caps:
        name = c['Name']
        # Extract saldo dari body
        # Cari pattern: nama capster followed by saldo cards
        idx = body.find(f'>{name}<')
        L(f'  {name} (id={c["id"]}): displayed in /capsters = {idx > -1}')

    # Cek edit capster via POST
    L('\n=== EDIT CAPSTER via POST /capsters/edit/<id> ===')
    if target:
        # Simulate edit — same values, should be no-op success
        from flask_wtf.csrf import generate_csrf
        with admin.session_transaction() as sess:
            sess['logged_in'] = True
        # Fetch page first to get CSRF cookie
        admin.get('/capsters/manage')
        # POST edit
        edit_data = {
            'name': target['Name'],
            'alias': target.get('Alias', ''),
            'employment_type': target['EmploymentType'],
            'monthly_salary': str(target['MonthlySalary']),
            'branch_id': target['BranchID'],
            'saldo_adjustment': '',   # kosong = jangan overwrite
        }
        # CSRF handled via session; test client auto-manages
        resp = admin.post(f'/capsters/edit/{target["id"]}', data=edit_data)
        L(f'  POST /capsters/edit/{target["id"]} → {resp.status_code}')
        if resp.status_code == 500:
            L(f'    ERROR: {resp.get_data(as_text=True)[:500]}')
        elif resp.status_code == 400:
            L(f'    400 (CSRF?): {resp.get_data(as_text=True)[:300]}')

    L('\n=== SCREENING COMPLETE ===')
except Exception as e:
    L(f'\n!!! SCREENING SCRIPT ERROR !!!')
    L(traceback.format_exc())
finally:
    logf.close()
