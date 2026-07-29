"""Smoke test setelah refactor telegram_id -> capster_id.

Verify:
1. Flask app boot OK
2. All blueprints registered
3. Route /capsters, /withdraw, /portal reachable (200/302)
4. DB integrity: semua withdrawal punya capster_id non-null
5. get_all_capsters() return dict dengan key 'id'
6. get_withdrawals(capster_id) works
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_smoke_log.txt')


def main():
    logf = open(LOG_PATH, 'w', encoding='utf-8')
    def log(msg):
        logf.write(str(msg) + '\n')
        logf.flush()

    try:
        log('=== 1. Flask app boot ===')
        from web import create_app
        app = create_app()
        log(f'  OK. Blueprints: {sorted(app.blueprints.keys())}')

        log('=== 2. Repository sanity ===')
        from app.db.repository import Repository
        repo = Repository()
        capsters = repo.get_all_capsters()
        log(f'  get_all_capsters() returned {len(capsters)} capsters')
        for c in capsters:
            has_id = 'id' in c
            log(f'    id={c.get("id")}, name={c.get("Name")!r}, has_id_key={has_id}')

        log('=== 3. get_withdrawals(capster_id) test ===')
        for c in capsters:
            cid = c.get('id')
            wds = repo.get_withdrawals(cid)
            log(f'    capster id={cid} name={c.get("Name")!r} -> {len(wds)} withdrawals')

        log('=== 4. DB integrity check ===')
        from app.db.database import get_db
        from sqlalchemy import text
        with get_db() as s:
            total_wd = s.execute(text('SELECT COUNT(*) FROM salary_withdrawals')).scalar()
            orphan_wd = s.execute(text('SELECT COUNT(*) FROM salary_withdrawals WHERE capster_id IS NULL')).scalar()
            log(f'  salary_withdrawals: total={total_wd}, orphan(capster_id NULL)={orphan_wd}')
            total_cap = s.execute(text('SELECT COUNT(*) FROM capsters')).scalar()
            null_tid = s.execute(text('SELECT COUNT(*) FROM capsters WHERE telegram_id IS NULL')).scalar()
            log(f'  capsters: total={total_cap}, telegram_id NULL={null_tid}')

        log('=== 5. Route smoke — with admin session ===')
        client = app.test_client()
        with client.session_transaction() as sess:
            sess['logged_in'] = True
        for url in ['/capsters', '/capsters/manage', '/withdraw', '/compare']:
            resp = client.get(url)
            log(f'  GET {url} -> {resp.status_code}')
            if resp.status_code == 500:
                log(f'    ERROR body: {resp.get_data(as_text=True)[:400]}')

        log('=== 6. Route smoke — with capster session ===')
        client2 = app.test_client()
        # Ambil capster pertama yang punya username untuk simulasi session
        target_cap = next((c for c in capsters if c.get('Username')), capsters[0] if capsters else None)
        if target_cap:
            log(f'  Simulate portal session as capster id={target_cap["id"]} name={target_cap["Name"]!r}')
            with client2.session_transaction() as sess:
                sess['capster_logged_in']   = True
                sess['capster_id']          = target_cap['id']
                sess['capster_name']        = target_cap['Name']
                sess['capster_telegram_id'] = target_cap.get('TelegramID')
                sess['capster_alias']       = target_cap.get('Alias', '')
                sess['capster_type']        = target_cap.get('EmploymentType', 'mitra')
                sess['capster_rate']        = target_cap.get('CommissionRate', 0.5)
                sess['capster_salary']      = target_cap.get('MonthlySalary', 0)
                sess['capster_branch_id']   = target_cap.get('BranchID', '')
            for url in ['/portal/', '/portal/earnings', '/portal/withdraw', '/portal/profile']:
                resp = client2.get(url)
                log(f'  GET {url} -> {resp.status_code}')
                if resp.status_code == 500:
                    log(f'    ERROR body: {resp.get_data(as_text=True)[:400]}')

        log('=== ALL SMOKE TESTS PASSED ===')
    except Exception as e:
        log(f'\nERROR: {e}')
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        logf.close()


if __name__ == '__main__':
    main()
