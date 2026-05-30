"""
Script migrasi sekali jalan — normalisasi kolom branch di tabel transactions & product_sales.

Masalah: data lama mungkin tersimpan dengan format campur:
  - 'cabang_a'       ← benar (branch_id)
  - 'Cabang A'       ← salah (short name, dari bug edit modal)
  - 'Cabang Denailla'← salah (full name)
  - '' / None        ← kosong

Solusi: semua nilai dinormalisasi ke branch_id ('cabang_a', 'cabang_b', dst.)

Cara pakai:
  python fix_branch_data.py          # dry-run (hanya tampilkan, tidak ubah)
  python fix_branch_data.py --apply  # terapkan perubahan ke DB
"""
import sys
import os

# Agar bisa import app.*
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import text
from app.db.database import engine, DATABASE_URL
from app.config.constants import BRANCHES

# ── Build reverse map: semua alias → branch_id ──────────────────────────────
# Contoh: {'Cabang A': 'cabang_a', 'Cabang Denailla': 'cabang_a', 'cabang_a': 'cabang_a', ...}
ALIAS_TO_ID: dict[str, str] = {}
for branch_id, cfg in BRANCHES.items():
    ALIAS_TO_ID[branch_id.lower()]                      = branch_id  # cabang_a
    ALIAS_TO_ID[cfg.get('short', '').lower()]           = branch_id  # cabang a
    ALIAS_TO_ID[cfg.get('name', '').lower()]            = branch_id  # cabang denailla
    ALIAS_TO_ID[cfg.get('location', '').lower()]        = branch_id  # mojosari

# Hapus key kosong jika ada
ALIAS_TO_ID.pop('', None)


def normalize(value: str | None) -> str | None:
    """Kembalikan branch_id jika bisa dipetakan, None jika tidak diketahui."""
    if not value:
        return None
    mapped = ALIAS_TO_ID.get(value.strip().lower())
    return mapped  # None jika tidak dikenal


def run(apply: bool = False):
    is_sqlite = DATABASE_URL.startswith('sqlite')

    with engine.connect() as conn:
        # ── Ambil semua nilai branch unik dari kedua tabel ───────────────
        tables = {
            'transactions':  'branch',
            'product_sales': 'branch_id',
        }

        for table, col in tables.items():
            # Cek apakah tabel & kolom ada
            if is_sqlite:
                result = conn.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ))
            else:
                result = conn.execute(text(
                    f"SELECT table_name FROM information_schema.tables "
                    f"WHERE table_name='{table}'"
                ))
            if not result.fetchone():
                print(f"  [SKIP] Tabel '{table}' tidak ditemukan.")
                continue

            rows = conn.execute(text(
                f"SELECT DISTINCT {col} FROM {table} WHERE {col} IS NOT NULL AND {col} != ''"
            )).fetchall()

            distinct_values = [r[0] for r in rows]
            print(f"\n=== {table}.{col} ===")
            print(f"  Distinct values: {distinct_values}")

            for val in distinct_values:
                mapped = normalize(val)
                if mapped is None:
                    print(f"  [UNKNOWN] '{val}' — tidak dikenali, dibiarkan.")
                elif mapped == val:
                    print(f"  [OK]      '{val}' — sudah benar.")
                else:
                    count_row = conn.execute(text(
                        f"SELECT COUNT(*) FROM {table} WHERE {col} = :v"
                    ), {'v': val}).fetchone()
                    count = count_row[0] if count_row else 0
                    print(f"  [FIX]     '{val}' -> '{mapped}' ({count} baris)")
                    if apply:
                        conn.execute(text(
                            f"UPDATE {table} SET {col} = :new WHERE {col} = :old"
                        ), {'new': mapped, 'old': val})

        if apply:
            conn.commit()
            print("\nSemua perubahan disimpan ke DB.")
        else:
            print("\nDry-run selesai. Jalankan dengan --apply untuk menerapkan perubahan.")


if __name__ == '__main__':
    apply = '--apply' in sys.argv
    print(f"Mode: {'APPLY (ubah DB)' if apply else 'DRY-RUN (hanya tampilkan)'}")
    print(f"Database: {DATABASE_URL}\n")
    run(apply=apply)
