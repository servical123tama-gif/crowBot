"""One-off migration: tambah salary_withdrawals.capster_id + backfill + capsters.telegram_id nullable.

Run: venv\\Scripts\\python.exe scripts\\_migrate_capster_id.py
Idempotent (aman di-run 2x).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.db.database import get_db
from sqlalchemy import text, inspect

LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups', '_migration_log.txt')


def main():
    logf = open(LOG_PATH, 'w', encoding='utf-8')

    def log(msg):
        logf.write(str(msg) + '\n')
        logf.flush()

    try:
        with get_db() as s:
            insp = inspect(s.bind)
            log('=== BEFORE ===')
            for c in insp.get_columns('capsters'):
                if c['name'] == 'telegram_id':
                    log(f"  capsters.telegram_id: nullable={c['nullable']}")
            wd_cols = [c['name'] for c in insp.get_columns('salary_withdrawals')]
            log(f"  salary_withdrawals cols: {wd_cols}")

            s.execute(text('ALTER TABLE salary_withdrawals ADD COLUMN IF NOT EXISTS capster_id INTEGER'))

            res = s.execute(text("""
                UPDATE salary_withdrawals w
                SET capster_id = c.id
                FROM capsters c
                WHERE w.telegram_id = c.telegram_id
                  AND w.capster_id IS NULL
            """))
            log(f'  Backfill: {res.rowcount} withdrawal rows updated')

            orphans = s.execute(text('SELECT COUNT(*) FROM salary_withdrawals WHERE capster_id IS NULL')).scalar()
            log(f'  Orphan withdrawals (capster_id NULL): {orphans}')
            if orphans > 0:
                rows = s.execute(text('SELECT id, capster_name, telegram_id, amount FROM salary_withdrawals WHERE capster_id IS NULL')).fetchall()
                for r in rows:
                    log(f'    orphan id={r[0]} name={r[1]!r} telegram_id={r[2]} amount={r[3]}')

            s.execute(text('ALTER TABLE capsters ALTER COLUMN telegram_id DROP NOT NULL'))

        log('=== AFTER ===')
        with get_db() as s:
            insp = inspect(s.bind)
            for c in insp.get_columns('capsters'):
                if c['name'] == 'telegram_id':
                    log(f"  capsters.telegram_id: nullable={c['nullable']}")
            wd_cols = [c['name'] for c in insp.get_columns('salary_withdrawals')]
            log(f"  salary_withdrawals cols: {wd_cols}")

        log('Migration OK.')
    except Exception as e:
        log(f'ERROR: {e}')
        import traceback
        log(traceback.format_exc())
        raise
    finally:
        logf.close()


if __name__ == '__main__':
    main()
