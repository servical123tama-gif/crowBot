"""
Sync point_balance dengan formula: visit_count - sum(points_used loyalty claim).

Why: data customer warisan punya inkonsistensi karena:
  - visit_count di-set manual saat migrasi dari Google Sheets
  - point_balance baru mulai dari 0 di sistem baru
  - Bug "reset 0" di logic klaim lama bikin surplus poin hilang
  - Bug "visit_count double-count" (sebelum 5953b3c) bikin angka kelebihan

Setelah sync:
  point_balance = max(0, min(MAX_POINTS, visit_count - claims_used))

Idempotent — boleh dijalankan ulang kapan saja.

Cara pakai:
  python scripts/sync_loyalty_points.py            # dry-run, tampilkan diff saja
  python scripts/sync_loyalty_points.py --apply    # tulis ke DB
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import func
from app.db.database import get_db, init_db
from app.db.models import Customer, LoyaltyClaim, LoyaltyAudit


def compute_new_point(visits: int, claims_used: int, max_points: int = 10) -> int:
    return max(0, min(max_points, visits - claims_used))


def main(apply: bool = False, max_points: int = 10) -> int:
    init_db()
    with get_db() as db:
        claim_totals = dict(
            db.query(LoyaltyClaim.customer_id, func.sum(LoyaltyClaim.points_used))
            .group_by(LoyaltyClaim.customer_id)
            .all()
        )

        customers = db.query(Customer).order_by(Customer.id).all()
        total = len(customers)
        changed = []
        for c in customers:
            visits = c.visit_count or 0
            kl = int(claim_totals.get(c.id, 0) or 0)
            new_p = compute_new_point(visits, kl, max_points)
            old_p = c.point_balance or 0
            if new_p != old_p:
                changed.append((c.id, c.name, visits, kl, old_p, new_p))
                if apply:
                    c.point_balance = new_p
                    db.add(LoyaltyAudit(
                        customer_id=c.id, delta=new_p - old_p,
                        before_balance=old_p, after_balance=new_p,
                        reason='sync', actor='system',
                        note=f'sync_loyalty_points.py: visits={visits} claims_used={kl}',
                    ))
        # commit happens at context exit when no exception

    mode = 'APPLY' if apply else 'DRY-RUN'
    print(f'\n=== {mode} ===')
    print(f'Total customer: {total}')
    print(f'Sudah sinkron: {total - len(changed)}')
    print(f'{"Akan diupdate" if not apply else "Diupdate"}: {len(changed)}')

    if changed:
        print()
        print(f'{"ID":<5} {"Nama":<22} {"Visits":<7} {"Klaim":<6} {"Old":<4} {"New":<4}')
        print('-' * 55)
        for cid, name, visits, kl, old_p, new_p in changed:
            print(f'{cid:<5} {(name or "")[:21]:<22} {visits:<7} {kl:<6} {old_p:<4} {new_p:<4}')

    if not apply:
        print('\n(Dry-run. Tambah --apply untuk benar-benar update.)')
    return 0 if changed or not apply else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='Tulis perubahan ke DB. Tanpa flag ini: dry-run saja.')
    args = parser.parse_args()
    sys.exit(main(apply=args.apply))
